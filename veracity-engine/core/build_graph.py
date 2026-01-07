import os
import ast
import logging
import sys
import time
import hashlib
import json
import argparse
from typing import List, Dict, Any, Set
from neo4j import GraphDatabase

from core.embeddings import get_document_embedding
from core.validation import validate_project_name, validate_path, validate_target_dirs
from core.config import ConfigLoader, get_config
from core.multitenancy import get_schema_constraints, validate_relationship_projects, TenantViolationType
from core.provenance import create_node_provenance_fields, get_extractor_version

# Setup Logging - will be configured by ConfigLoader
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def get_file_hash(path: str) -> str:
    """Calculate SHA1 hash of a file for change detection (fast)."""
    hasher = hashlib.sha1()
    with open(path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, builder, file_path, parent_id):
        self.builder = builder
        self.file_path = file_path
        self.parent_stack = [parent_id]

    def visit_Import(self, node):
        for alias in node.names:
            self.builder.relationships.append({
                "start_id": self.parent_stack[0],
                "end_target": alias.name,
                "type": "DEPENDS_ON"
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            target = f"{module}.{alias.name}" if module else alias.name
            self.builder.relationships.append({
                "start_id": self.parent_stack[0],
                "end_target": target,
                "type": "DEPENDS_ON"
            })
        self.generic_visit(node)

    def visit_Call(self, node):
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
            
        if call_name:
            self.builder.relationships.append({
                "start_id": self.parent_stack[-1],
                "end_target": call_name,
                "type": "CALLS"
            })
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        parent_id = self.parent_stack[-1]
        qualified_name = f"{parent_id}.{node.name}"
        docstring = ast.get_docstring(node) or ""
        
        node_data = {
            "type": "Class",
            "name": node.name,
            "qualified_name": qualified_name,
            "uid": qualified_name,
            "docstring": docstring,
            "file_path": self.file_path,
            "start_line": node.lineno,
            "embedding": None
        }
        self.builder.nodes.append(node_data)
        
        self.builder.relationships.append({
            "start_id": parent_id,
            "end_id": qualified_name,
            "type": "DEFINES"
        })
        
        self.parent_stack.append(qualified_name)
        self.generic_visit(node)
        self.parent_stack.pop()

    def visit_FunctionDef(self, node):
        self._handle_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node):
        self._handle_func(node, is_async=True)

    def _handle_func(self, node, is_async):
        parent_id = self.parent_stack[-1]
        qualified_name = f"{parent_id}.{node.name}"
        docstring = ast.get_docstring(node) or ""
        
        node_data = {
            "type": "Function",
            "name": node.name,
            "qualified_name": qualified_name,
            "uid": qualified_name,
            "docstring": docstring,
            "file_path": self.file_path,
            "start_line": node.lineno,
            "is_async": is_async,
            "embedding": None
        }
        self.builder.nodes.append(node_data)
        
        self.builder.relationships.append({
            "start_id": parent_id,
            "end_id": qualified_name,
            "type": "DEFINES"
        })
        
        self.parent_stack.append(qualified_name)
        self.generic_visit(node)
        self.parent_stack.pop()

class CodeGraphBuilder:
    def __init__(self, uri, user, password, project_name, root_dir):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.project_name = project_name
        self.root_dir = root_dir
        self.nodes = []
        self.relationships = []
        self.hierarchy_nodes = {}  # Map path -> UID
        self.hashes = {}
        
        # Hash cache file is now project-specific
        self.hash_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".graph_hashes_{project_name}.json")
        self.load_hashes()

    def load_hashes(self):
        if os.path.exists(self.hash_cache_file):
            try:
                with open(self.hash_cache_file, 'r') as f:
                    self.hashes = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load hash cache: {e}")

    def save_hashes(self):
        try:
            with open(self.hash_cache_file, 'w') as f:
                json.dump(self.hashes, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save hash cache: {e}")

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            return session.run(query, parameters)

    def clear_database(self):
        """Clear all nodes and relationships for this project."""
        logger.info(f"Clearing existing database for project '{self.project_name}'...")
        query = "MATCH (n {project: $project}) DETACH DELETE n"
        try:
            self.run_query(query, {"project": self.project_name})
            logger.info(f"Cleared database for project: {self.project_name}")
        except Exception as e:
            logger.error(f"Failed to clear database for project {self.project_name}: {e}")
            raise  # Re-raise to let caller handle
        self.hashes = {}
        if os.path.exists(self.hash_cache_file):
            os.remove(self.hash_cache_file)

    def delete_file_from_graph(self, rel_path: str):
        """Delete a file and all its defined children from the graph for this project."""
        query = """
        MATCH (f:File {path: $path, project: $project})
        OPTIONAL MATCH (f)-[:DEFINES*0..]->(child)
        DETACH DELETE child, f
        """
        try:
            self.run_query(query, {"path": rel_path, "project": self.project_name})
            logger.debug(f"Deleted file from graph: {rel_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {rel_path} from graph: {e}")
            # Don't raise - continue with other files

    def create_constraints(self):
        logger.info("Creating constraints and indexes...")

        # Base constraints and indexes
        queries = [
            # Node constraints and indexes
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.uid IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.qualified_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.path)",
            # Full-text search index for code
            "CREATE FULLTEXT INDEX code_search IF NOT EXISTS FOR (n:Code) ON EACH [n.name, n.docstring]",
            # Vector index for embeddings
            f"""
            CREATE VECTOR INDEX code_embeddings IF NOT EXISTS
            FOR (n:Code) ON (n.embedding)
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
            }}}}
            """,
            # VeracityReport constraints and indexes for query audit trail
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:VeracityReport) REQUIRE r.query_id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (r:VeracityReport) ON (r.project)",
            "CREATE INDEX IF NOT EXISTS FOR (r:VeracityReport) ON (r.timestamp)",
        ]

        # Add multitenancy schema constraints for tenant isolation
        queries.extend(get_schema_constraints())

        for q in queries:
            try:
                self.run_query(q)
            except Exception as e:
                # Log warning for non-critical constraint failures
                # (e.g., constraint already exists with different name)
                logger.warning(f"Constraint creation warning: {e}")

    # NOTE: get_embedding method removed - now using shared core.embeddings.get_document_embedding

    def classify_asset(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.java', '.cpp', '.h', '.rs']:
            return "Code"
        elif filename in ['Dockerfile', 'docker-compose.yml', 'Makefile'] or ext in ['.tf', '.env', '.toml']:
            return "Infrastructure"
        elif ext in ['.md', '.txt', '.rst']:
            return "Documentation"
        elif ext in ['.json', '.yaml', '.yml', '.xml', '.ini']:
            return "Config"
        return "Data"

    def process_hierarchy(self, target_dirs: List[str]):
        """
        Scan directories to establish a 4-Tier Hierarchy:
        Capability -> Feature -> Component
        
        Heuristic:
          - Root/TargetDir -> Capability (e.g., 'services')
          - TargetDir/SubDir -> Feature (e.g., 'graph-rag')
          - FeatureDir/SubDir -> Component (e.g., 'core')
        """
        logger.info("Building 4-Tier hierarchy...")
        for target in target_dirs:
            abs_target = os.path.join(self.root_dir, target)
            if not os.path.isdir(abs_target):
                continue
                
            # Level 1: Capability
            cap_name = os.path.basename(target)
            cap_uid = f"{self.project_name}:cap:{cap_name}"
            
            self.nodes.append({
                "type": "Capability",
                "name": cap_name,
                "uid": cap_uid,
                "project": self.project_name,
                "embedding": []
            })
            self.hierarchy_nodes[target] = cap_uid
            
            # Level 2: Feature
            exclude_dirs = {'venv', '.venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 'dist', 'build'}
            for lvl2_entry in os.scandir(abs_target):
                if lvl2_entry.is_dir() and not lvl2_entry.name.startswith('.') and lvl2_entry.name not in exclude_dirs:
                    feat_name = lvl2_entry.name
                    feat_path = os.path.join(target, feat_name)
                    feat_uid = f"{self.project_name}:feat:{feat_path}"
                    
                    self.nodes.append({
                        "type": "Feature",
                        "name": feat_name,
                        "uid": feat_uid,
                        "project": self.project_name,
                        "embedding": []
                    })
                    self.hierarchy_nodes[feat_path] = feat_uid
                    
                    self.relationships.append({
                        "start_id": cap_uid,
                        "end_id": feat_uid,
                        "type": "HAS_FEATURE"
                    })
                    
                    # Level 3: Component
                    for lvl3_entry in os.scandir(lvl2_entry.path):
                        if lvl3_entry.is_dir() and not lvl3_entry.name.startswith('.') and lvl3_entry.name not in exclude_dirs:
                            comp_name = lvl3_entry.name
                            comp_path = os.path.join(feat_path, comp_name)
                            comp_uid = f"{self.project_name}:comp:{comp_path}"
                            
                            self.nodes.append({
                                "type": "Component",
                                "name": comp_name,
                                "uid": comp_uid,
                                "project": self.project_name,
                                "embedding": []
                            })
                            self.hierarchy_nodes[comp_path] = comp_uid
                            
                            self.relationships.append({
                                "start_id": feat_uid,
                                "end_id": comp_uid,
                                "type": "HAS_COMPONENT"
                            })

    def index_documents(self, target_dirs: List[str]):
        """Scan for markdown files, determine currency, and link to hierarchy."""
        logger.info("Indexing documentation...")
        exclude_dirs = {'venv', '.venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 'dist', 'build'}
        for target in target_dirs:
            t_path = os.path.join(self.root_dir, target)
            if not os.path.exists(t_path):
                continue

            for root, dirs, filenames in os.walk(t_path):
                # Prune excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.endswith('.egg-info')]
                for f in filenames:
                    if not f.endswith(".md") or f.startswith('.'):
                        continue
                        
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, self.root_dir)
                    last_modified = os.path.getmtime(abs_path)
                    
                    # Determine Parent (Feature or Capability)
                    parent_dir = os.path.dirname(rel_path)
                    # Traverse up to find nearest known hierarchy node
                    parent_uid = None
                    curr = parent_dir
                    while curr and curr != '.':
                        if curr in self.hierarchy_nodes:
                            parent_uid = self.hierarchy_nodes[curr]
                            break
                        curr = os.path.dirname(curr)
                    
                    # Fallback to Project Node (implied, or just attached to first cap?)
                    # For now if no parent found, skip or attach to a default? 
                    # We'll attach to the first known capability of this target dir if possible
                    if not parent_uid:
                         # Try finding the target dir capability
                         base_target = rel_path.split(os.sep)[0]
                         if base_target in self.hierarchy_nodes:
                             parent_uid = self.hierarchy_nodes[base_target]

                    doc_uid = f"{self.project_name}:doc:{rel_path}"
                    doc_type = "Architecture" if "ARCH" in f else "Spec" if "PRD" in f or "SPEC" in f else "Plan" if "TODO" in f else "General"

                    # Create provenance fields for the document
                    provenance = create_node_provenance_fields(
                        file_path=abs_path,
                        relative_path=rel_path,
                        is_binary=False,  # Markdown files are text
                    )

                    self.nodes.append({
                        "type": "Document",
                        "name": f,
                        "uid": doc_uid,
                        "path": rel_path,
                        "doc_type": doc_type,
                        "last_modified": last_modified,
                        "project": self.project_name,
                        "embedding": [],
                        # Provenance fields
                        **provenance,
                    })
                    
                    if parent_uid:
                        self.relationships.append({
                            "start_id": parent_uid,
                            "end_id": doc_uid,
                            "type": "HAS_DOCUMENT"
                        })

    def parse_file(self, file_path: str):
        rel_path = os.path.relpath(file_path, self.root_dir)
        current_hash = get_file_hash(file_path)
        
        # Link File to Hierarchy
        # Find nearest parent
        file_parent_dir = os.path.dirname(rel_path)
        hierarchy_parent_uid = None
        curr = file_parent_dir
        while curr and curr != '.':
            if curr in self.hierarchy_nodes:
                hierarchy_parent_uid = self.hierarchy_nodes[curr]
                break
            curr = os.path.dirname(curr)
            
        file_uid = f"{self.project_name}:{rel_path}"
        
        # Always re-link hierarchy even if hash matches (in case hierarchy logic changed)
        if hierarchy_parent_uid:
            self.relationships.append({
                "start_id": hierarchy_parent_uid,
                "end_id": file_uid,
                "type": "HAS_ASSET"
            })
        
        if self.hashes.get(rel_path) == current_hash:
            return False
            
        logger.info(f"Indexing changed file: {rel_path} in '{self.project_name}'")
        self.delete_file_from_graph(rel_path)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Create provenance fields for the file
            provenance = create_node_provenance_fields(
                file_path=file_path,
                relative_path=rel_path,
                is_binary=False,  # Python files are text
            )

            file_node = {
                "type": "File",
                "path": rel_path,
                "name": os.path.basename(file_path),
                "uid": file_uid,
                "project": self.project_name,
                "category": self.classify_asset(os.path.basename(file_path)),
                "embedding": [],
                # Provenance fields
                **provenance,
            }
            self.nodes.append(file_node)
            
            ext = os.path.splitext(file_path)[1].lower()

            if ext == '.py':
                # Python AST parsing
                tree = ast.parse(content)
                visitor = CodeVisitor(self, file_path, file_uid)
                visitor.visit(tree)
            else:
                # Multi-language regex-based extraction for JS/TS/Go/Java/etc.
                self._parse_with_regex(content, file_path, file_uid, ext)

            self.hashes[rel_path] = current_hash
            return True
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return False

    def _parse_with_regex(self, content: str, file_path: str, file_uid: str, ext: str):
        """
        Language-agnostic regex-based extraction for non-Python files.
        Extracts functions, classes, interfaces, and exports.
        """
        import re

        lines = content.split('\n')

        # Patterns for TypeScript/JavaScript
        ts_patterns = {
            'function': [
                # export function name(
                r'export\s+(?:async\s+)?function\s+(\w+)',
                # const name = (
                r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(',
                # function name(
                r'^(?:async\s+)?function\s+(\w+)',
                # name: function(
                r'(\w+)\s*:\s*(?:async\s+)?function',
                # Arrow functions: const name = () =>
                r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
            ],
            'class': [
                # export class Name
                r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)',
                # interface Name
                r'(?:export\s+)?interface\s+(\w+)',
                # type Name =
                r'(?:export\s+)?type\s+(\w+)\s*=',
            ],
        }

        # Patterns for Go
        go_patterns = {
            'function': [
                r'^func\s+(?:\([^)]+\)\s+)?(\w+)',
            ],
            'class': [
                r'^type\s+(\w+)\s+struct',
                r'^type\s+(\w+)\s+interface',
            ],
        }

        # Patterns for Java/Kotlin
        java_patterns = {
            'function': [
                r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+)?\s*\{',
                r'fun\s+(\w+)',  # Kotlin
            ],
            'class': [
                r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)',
                r'(?:public\s+)?interface\s+(\w+)',
                r'data\s+class\s+(\w+)',  # Kotlin data class
                r'sealed\s+class\s+(\w+)',  # Kotlin sealed class
            ],
        }

        # Patterns for Swift
        swift_patterns = {
            'function': [
                r'func\s+(\w+)',
            ],
            'class': [
                r'(?:public\s+)?(?:final\s+)?class\s+(\w+)',
                r'(?:public\s+)?struct\s+(\w+)',
                r'(?:public\s+)?protocol\s+(\w+)',
                r'(?:public\s+)?enum\s+(\w+)',
            ],
        }

        # Patterns for C#
        csharp_patterns = {
            'function': [
                r'(?:public|private|protected|internal)?\s*(?:static)?\s*(?:async)?\s*\w+\s+(\w+)\s*\([^)]*\)',
            ],
            'class': [
                r'(?:public\s+)?(?:abstract\s+)?(?:partial\s+)?class\s+(\w+)',
                r'(?:public\s+)?interface\s+(\w+)',
                r'(?:public\s+)?struct\s+(\w+)',
                r'(?:public\s+)?enum\s+(\w+)',
            ],
        }

        # Patterns for Ruby
        ruby_patterns = {
            'function': [
                r'def\s+(\w+)',
            ],
            'class': [
                r'class\s+(\w+)',
                r'module\s+(\w+)',
            ],
        }

        # Patterns for PHP
        php_patterns = {
            'function': [
                r'function\s+(\w+)',
                r'(?:public|private|protected)\s+function\s+(\w+)',
            ],
            'class': [
                r'class\s+(\w+)',
                r'interface\s+(\w+)',
                r'trait\s+(\w+)',
            ],
        }

        # Patterns for Rust
        rust_patterns = {
            'function': [
                r'(?:pub\s+)?fn\s+(\w+)',
                r'(?:pub\s+)?async\s+fn\s+(\w+)',
            ],
            'class': [
                r'(?:pub\s+)?struct\s+(\w+)',
                r'(?:pub\s+)?enum\s+(\w+)',
                r'(?:pub\s+)?trait\s+(\w+)',
                r'impl\s+(\w+)',
            ],
        }

        # Select patterns based on extension
        if ext in ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.vue', '.svelte']:
            patterns = ts_patterns
        elif ext == '.go':
            patterns = go_patterns
        elif ext in ['.java', '.kt', '.kts', '.scala', '.groovy']:
            patterns = java_patterns
        elif ext == '.swift':
            patterns = swift_patterns
        elif ext in ['.cs', '.fs']:
            patterns = csharp_patterns
        elif ext in ['.rb', '.rake']:
            patterns = ruby_patterns
        elif ext == '.php':
            patterns = php_patterns
        elif ext == '.rs':
            patterns = rust_patterns
        else:
            patterns = ts_patterns  # Default to TS patterns for unknown

        # Extract functions
        for pattern in patterns.get('function', []):
            for line_no, line in enumerate(lines, 1):
                matches = re.findall(pattern, line)
                for match in matches:
                    func_name = match if isinstance(match, str) else match[0]
                    if func_name and not func_name.startswith('_'):
                        # Extract docstring/comment above
                        docstring = self._extract_comment_above(lines, line_no - 1)
                        func_uid = f"{file_uid}:{func_name}:{line_no}"
                        func_node = {
                            "type": "Function",
                            "name": func_name,
                            "uid": func_uid,
                            "project": self.project_name,
                            "docstring": docstring,
                            "line_start": line_no,
                            "start_line": line_no,
                            "file_path": file_path,
                            "qualified_name": f"{os.path.basename(file_path)}:{func_name}",
                            "is_async": "async" in line.lower(),
                            "embedding": [],
                        }
                        self.nodes.append(func_node)
                        self.relationships.append({
                            "start_id": file_uid,
                            "end_id": func_uid,
                            "type": "DEFINES"
                        })

        # Extract classes/interfaces
        for pattern in patterns.get('class', []):
            for line_no, line in enumerate(lines, 1):
                matches = re.findall(pattern, line)
                for match in matches:
                    class_name = match if isinstance(match, str) else match[0]
                    if class_name:
                        docstring = self._extract_comment_above(lines, line_no - 1)
                        class_uid = f"{file_uid}:{class_name}"
                        class_node = {
                            "type": "Class",
                            "name": class_name,
                            "uid": class_uid,
                            "project": self.project_name,
                            "docstring": docstring,
                            "line_start": line_no,
                            "start_line": line_no,
                            "file_path": file_path,
                            "qualified_name": f"{os.path.basename(file_path)}:{class_name}",
                            "is_async": False,
                            "embedding": [],
                        }
                        self.nodes.append(class_node)
                        self.relationships.append({
                            "start_id": file_uid,
                            "end_id": class_uid,
                            "type": "DEFINES"
                        })

    def _extract_comment_above(self, lines: list, line_idx: int) -> str:
        """Extract JSDoc/comment block above a line."""
        comments = []
        idx = line_idx - 1

        while idx >= 0:
            line = lines[idx].strip()
            if line.startswith('//'):
                comments.insert(0, line[2:].strip())
            elif line.startswith('*') or line.startswith('/*') or line.startswith('/**'):
                comments.insert(0, line.lstrip('/*').rstrip('*/').strip())
            elif line == '':
                idx -= 1
                continue
            else:
                break
            idx -= 1

        return ' '.join(comments) if comments else ""

    def batch_process_embeddings(self):
        target_nodes = [n for n in self.nodes if n["type"] in ["Class", "Function"]]
        if not target_nodes:
            return

        logger.info(f"Generating embeddings for {len(target_nodes)} nodes...")
        count = 0
        for node in target_nodes:
            text = f"{node['type']}: {node['name']}\nDocumentation: {node['docstring']}"
            node["embedding"] = get_document_embedding(text)
            count += 1
            if count % 100 == 0:
                logger.info(f"Generated {count} embeddings...")

    def commit_to_neo4j(self):
        if not self.nodes and not self.relationships:
            return
            
        logger.info(f"Committing {len(self.nodes)} nodes and {len(self.relationships)} relationships...")
        
        with self.driver.session() as session:
            # 1. Commit Nodes
            for node in self.nodes:
                if node['type'] == 'File':
                    query = """
                    MERGE (n:File:Node:Project {uid: $uid})
                    SET n.name = $name, n.path = $path, n.project = $project, n.category = $category,
                        n.prov_path = $prov_path, n.prov_file_hash = $prov_file_hash,
                        n.prov_text_hash = $prov_text_hash, n.prov_last_modified = $prov_last_modified,
                        n.prov_extractor = $prov_extractor, n.prov_extractor_version = $prov_extractor_version
                    """
                    params = {
                        "uid": node["uid"],
                        "name": node["name"],
                        "path": node["path"],
                        "project": self.project_name,
                        "category": node.get("category", "Code"),
                        # Provenance fields
                        "prov_path": node.get("prov_path", ""),
                        "prov_file_hash": node.get("prov_file_hash", ""),
                        "prov_text_hash": node.get("prov_text_hash", ""),
                        "prov_last_modified": node.get("prov_last_modified", 0),
                        "prov_extractor": node.get("prov_extractor", ""),
                        "prov_extractor_version": node.get("prov_extractor_version", ""),
                    }
                elif node['type'] in ['Capability', 'Feature', 'Component']:
                    labels = f":{node['type']}:Node:Project"
                    query = f"MERGE (n{labels} {{uid: $uid}}) SET n.name = $name, n.project = $project"
                    params = {"uid": node["uid"], "name": node["name"], "project": self.project_name} 
                elif node['type'] == 'Document':
                    query = """
                    MERGE (n:Document:Node:Project {uid: $uid})
                    SET n.name = $name, n.path = $path, n.doc_type = $doc_type,
                        n.last_modified = $last_modified, n.project = $project,
                        n.prov_path = $prov_path, n.prov_file_hash = $prov_file_hash,
                        n.prov_text_hash = $prov_text_hash, n.prov_last_modified = $prov_last_modified,
                        n.prov_extractor = $prov_extractor, n.prov_extractor_version = $prov_extractor_version
                    """
                    params = {
                        "uid": node["uid"],
                        "name": node["name"],
                        "path": node["path"],
                        "doc_type": node["doc_type"],
                        "last_modified": node["last_modified"],
                        "project": self.project_name,
                        # Provenance fields
                        "prov_path": node.get("prov_path", ""),
                        "prov_file_hash": node.get("prov_file_hash", ""),
                        "prov_text_hash": node.get("prov_text_hash", ""),
                        "prov_last_modified": node.get("prov_last_modified", 0),
                        "prov_extractor": node.get("prov_extractor", ""),
                        "prov_extractor_version": node.get("prov_extractor_version", ""),
                    }
                else:
                    labels = f":{node['type']}:Code:Node:Project"
                    query = f"""
                    MERGE (n{labels} {{uid: $uid}})
                    SET n.name = $name,
                        n.path = $path,
                        n.qualified_name = $qualified_name,
                        n.docstring = $docstring,
                        n.embedding = $embedding,
                        n.project = $project,
                        n.start_line = $start_line,
                        n.is_async = $is_async
                    """
                    params = {
                        "uid": node["uid"],
                        "name": node["name"],
                        "path": node["file_path"],
                        "qualified_name": node["qualified_name"],
                        "docstring": node.get("docstring", ""),
                        "embedding": node.get("embedding"),
                        "project": self.project_name,
                        "start_line": node.get("start_line", 0),
                        "is_async": node.get("is_async", False)
                    }
                try:
                    session.run(query, params)
                except Exception as e:
                    logger.error(f"Failed to commit node {node.get('name', 'unknown')}: {e}")
                    # Continue with other nodes
                
            # 2. Commit Relationships in Optimized Batches
            batch_size = 5000

            # Structural relationships (DEFINES, HAS_FEATURE, HAS_FILE, HAS_DOCUMENT)
            # use direct UID lookup for both endpoints.
            # Note: Cypher doesn't support parameterized relationship types,
            # so we group relationships by type and create them in batches.
            structural_rels = [r for r in self.relationships if "end_id" in r]

            from collections import defaultdict
            rels_by_type = defaultdict(list)
            for r in structural_rels:
                rels_by_type[r['type']].append(r)
                
            for r_type, rels in rels_by_type.items():
                for i in range(0, len(rels), batch_size):
                    batch = rels[i:i + batch_size]
                    query = f"""
                    UNWIND $batch as rel
                    MATCH (a:Node {{uid: rel.start_id}})
                    MATCH (b:Node {{uid: rel.end_id}})
                    MERGE (a)-[:{r_type}]->(b)
                    """
                    try:
                        session.run(query, {"batch": batch})
                    except Exception as e:
                        logger.error(f"Failed to commit {r_type} relationships batch: {e}")
                        # Continue with other batches
            
            # CALLS/DEPENDS_ON: UID lookup for start, Name lookup for end (Scoped to same project)
            fuzzy_rels = [r for r in self.relationships if "end_target" in r]
            for r_type in ["CALLS", "DEPENDS_ON"]:
                typed_rels = [r for r in fuzzy_rels if r["type"] == r_type]
                for i in range(0, len(typed_rels), batch_size):
                    batch = typed_rels[i:i + batch_size]
                    query = f"""
                    UNWIND $batch as rel
                    MATCH (a:Node {{uid: rel.start_id}})
                    MATCH (b:Code {{name: rel.end_target, project: $project}})
                    MERGE (a)-[:{r_type}]->(b)
                    """
                    try:
                        session.run(query, {"batch": batch, "project": self.project_name})
                    except Exception as e:
                        logger.error(f"Failed to commit {r_type} fuzzy relationships batch: {e}")
                        # Continue with other batches

def main():
    parser = argparse.ArgumentParser(description="Build/Update Codebase Graph")
    parser.add_argument("--project-name", required=True, help="Unique name for the project (tenant)")
    parser.add_argument("--root-dir", help="Project root directory (defaults to current dir)")
    parser.add_argument("--target-dirs", nargs="+", help="Specific directories to scan (relative to root)")
    parser.add_argument("--force", action="store_true", help="Clear database for this project and rebuild")
    parser.add_argument("--config", help="Path to configuration file (YAML)")
    args = parser.parse_args()

    # Load configuration with hierarchy: CLI args -> env vars -> config file -> defaults
    config = ConfigLoader.load(
        config_file=args.config,
        # CLI args can override specific config values if needed in future
    )

    # Configure logging from config
    logging.getLogger().setLevel(getattr(logging, config.logging.level))

    # Get default target dirs from config
    default_target_dirs = config.project.target_dirs

    # Validate inputs to prevent path traversal and injection attacks
    try:
        project_name = validate_project_name(args.project_name)
        root_dir = validate_path(
            args.root_dir if args.root_dir else os.getcwd(),
            must_exist=True,
            must_be_dir=True
        )
        if args.target_dirs:
            target_dirs = validate_target_dirs(args.target_dirs, root_dir)
        else:
            target_dirs = validate_target_dirs(default_target_dirs, root_dir)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)

    # Get Neo4j credentials from config (secrets handled securely)
    neo4j_uri = config.neo4j.uri
    neo4j_user = config.neo4j.user
    neo4j_password = config.neo4j.password.get_secret_value()

    logger.info(f"Config loaded: Neo4j={neo4j_uri}, user={neo4j_user}")

    builder = CodeGraphBuilder(neo4j_uri, neo4j_user, neo4j_password, project_name, root_dir)
    try:
        if args.force:
            builder.clear_database()
            
        builder.create_constraints()
        
        # Directories to always exclude
        EXCLUDE_DIRS = {'venv', '.venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 'dist', 'build', 'egg-info', '.next'}

        # Supported code file extensions - comprehensive list
        CODE_EXTENSIONS = {
            # Python
            '.py', '.pyi', '.pyx',
            # JavaScript/TypeScript
            '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
            # Web frameworks
            '.vue', '.svelte',
            # Go
            '.go',
            # Java/JVM
            '.java', '.kt', '.kts', '.scala', '.groovy',
            # C/C++
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
            # Rust
            '.rs',
            # Swift/Objective-C
            '.swift', '.m', '.mm',
            # C#/.NET
            '.cs', '.fs',
            # Ruby
            '.rb', '.rake',
            # PHP
            '.php',
            # Dart/Flutter
            '.dart',
            # Shell
            '.sh', '.bash', '.zsh',
            # Other
            '.lua', '.r', '.R', '.pl', '.pm',
        }

        current_files = []
        for target in target_dirs:
            t_path = os.path.join(root_dir, target)
            if os.path.exists(t_path):
                for root, dirs, filenames in os.walk(t_path):
                    # Prune excluded directories in-place
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith('.egg-info')]
                    for f in filenames:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in CODE_EXTENSIONS and not f.startswith('.'):
                            current_files.append(os.path.join(root, f))
        
        builder.process_hierarchy(target_dirs)
        builder.index_documents(target_dirs)
        
        rel_files = {os.path.relpath(f, root_dir) for f in current_files}
        
        # 1. Handle Deleted Files
        deleted_files = set(builder.hashes.keys()) - rel_files
        if deleted_files:
            logger.info(f"Removing {len(deleted_files)} deleted files from project '{project_name}'...")
            for rel_path in deleted_files:
                builder.delete_file_from_graph(rel_path)
                if rel_path in builder.hashes:
                    del builder.hashes[rel_path]

        # 2. Parse New/Changed Files
        changed_count = 0
        for f in current_files:
            if builder.parse_file(f):
                changed_count += 1

        if changed_count > 0 or deleted_files:
            builder.batch_process_embeddings()
            builder.commit_to_neo4j()
            builder.save_hashes()
            logger.info(f"Graph update complete for '{project_name}'. Processed {changed_count} files.")
        else:
            logger.info(f"Project '{project_name}' is up to date.")
            
    finally:
        builder.close()

if __name__ == "__main__":
    main()

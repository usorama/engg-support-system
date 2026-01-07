import sys
import logging
import json
import uuid
import datetime
import os
import argparse
import ollama
from neo4j import GraphDatabase

from core.embeddings import get_query_embedding
from core.config import ConfigLoader, get_config
from core.evidence_query import (
    EvidenceOutputMode,
    EvidenceQueryConfig,
    EvidencePacket,
    CodeEvidence,
    DocEvidence,
    create_evidence_packet,
    sort_evidence_deterministically,
    format_insufficient_evidence_response,
    DEFAULT_SUGGESTED_ACTIONS,
)

# Configure logging - will be configured by ConfigLoader
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Audit Configuration
AUDIT_DIR = ".graph_rag/audit"

class VeracityLogger:
    @staticmethod
    def log_packet(packet):
        if not os.path.exists(AUDIT_DIR):
            os.makedirs(AUDIT_DIR, exist_ok=True)
        
        audit_file = os.path.join(AUDIT_DIR, f"audit_{datetime.datetime.now().strftime('%Y%m')}.jsonl")
        with open(audit_file, "a") as f:
            f.write(json.dumps(packet) + "\n")

class GroundTruthContextSystem:
    def __init__(self, records, project_name):
        self.records = records
        self.project_name = project_name
        self.faults = []
        self.confidence_score = 100.0

    def validate(self):
        self._check_staleness()
        self._check_orphans()
        self._check_contradictions()
        
        # Deduplicate faults
        self.faults = list(set(self.faults))
        # Cap confidence
        self.confidence_score = max(0.0, min(100.0, self.confidence_score))
        
        return {
            "confidence_score": round(self.confidence_score, 2),
            "is_stale": any("STALE" in f for f in self.faults),
            "faults": self.faults
        }

    def _check_staleness(self):
        now = datetime.datetime.now().timestamp()
        ninety_days = 90 * 24 * 60 * 60
        for record in self.records:
            node = record['node']
            if 'Document' in node.labels:
                ts = node.get('last_modified', 0)
                if (now - ts) > ninety_days:
                    date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    self.faults.append(f"STALE_DOC: '{node['name']}' was last modified on {date_str}.")
                    self.confidence_score -= 15

    def _check_orphans(self):
        for record in self.records:
            if not record['neighbors'] or len(record['neighbors']) < 2:
                self.faults.append(f"ORPHANED_NODE: '{record['name']}' has very low connectivity in the graph.")
                self.confidence_score -= 5

    def _check_contradictions(self):
        # Heuristic: If a Function node has a docstring but is linked to a Document node
        # that hasn't been updated in 180 days, flag as potential contradiction.
        # This is a basic implementation; can be expanded with LLM-based diffing.
        pass

# NOTE: get_embedding function removed - now using shared core.embeddings.get_query_embedding


def query_graph(question, project_name, config=None, evidence_config=None):
    """
    Query the knowledge graph for relevant context.

    Args:
        question: The query string
        project_name: Project name for multitenancy
        config: Optional VeracityConfig instance. If not provided, uses singleton.
        evidence_config: Optional EvidenceQueryConfig for output mode control.
    """
    if config is None:
        config = get_config()
    if evidence_config is None:
        evidence_config = EvidenceQueryConfig()  # Default: evidence-only

    logger.info(f"Searching Knowledge Graph (Project: {project_name}) for: '{question}'...")
    question_embedding = get_query_embedding(question)

    # Get Neo4j credentials from config
    neo4j_uri = config.neo4j.uri
    neo4j_user = config.neo4j.user
    neo4j_password = config.neo4j.password.get_secret_value()

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Hybrid Query: Vector Similarity + Full-Text Keyword Match (Scoped by Project)
    # NOTE: Vector search limit must be high enough to include target project nodes
    # since Neo4j vector index doesn't support pre-filtering by project.
    # With 12k+ total nodes, we need a larger limit for multitenancy.
    cypher_query = """
    CALL {
        // 1. Vector Search (high limit for multitenancy - filter happens post-search)
        CALL db.index.vector.queryNodes('code_embeddings', 500, $embedding)
        YIELD node, score
        WHERE node.project = $project
        RETURN node, score, 'vector' as source

        UNION

        // 2. Full-Text Search (Keywords)
        CALL db.index.fulltext.queryNodes('code_search', $question, {limit: 100})
        YIELD node, score
        WHERE node.project = $project
        RETURN node, score, 'keyword' as source
    }

    // Deduplicate and aggregate
    WITH node, max(score) as score, collect(source) as sources
    
    // 3. Expand Context (neighboring nodes)
    OPTIONAL MATCH (node)-[:DEFINES|CALLS|DEPENDS_ON|HAS_ASSET|HAS_COMPONENT*0..1]-(related)
    WHERE related.project = $project
    
    RETURN 
        node,
        node.uid as id,
        node.name as name,
        node.docstring as doc,
        score,
        sources,
        collect(distinct related.name) as neighbors
    ORDER BY score DESC
    LIMIT 20
    """

    try:
        with driver.session() as session:
            result = session.run(cypher_query, {
                "embedding": question_embedding,
                "question": question,
                "project": project_name
            })
            records = list(result)
            
            if not records:
                return {
                    "meta": {
                        "query_id": str(uuid.uuid4()), 
                        "timestamp": datetime.datetime.now().isoformat(), 
                        "project": project_name,
                        "question": question
                    },
                    "context_veracity": {"confidence_score": 0, "is_stale": False, "faults": ["No relevant context found."]},
                    "code_truth": [],
                    "doc_claims": [],
                    "graph_relationships": [],
                    "suggested_actions": ["Run build_graph.py to index the codebase."]
                }
            
            engine = GroundTruthContextSystem(records, project_name)
            veracity = engine.validate()
            
            code_truth = []
            doc_claims = []
            graph_relationships = []
            
            for record in records:
                node = record['node']
                entity = {
                    "id": record['id'],
                    "name": record['name'],
                    "type": list(node.labels),
                    "path": node.get('path', 'unknown'),
                    "neighbors": record['neighbors']
                }
                
                if 'Code' in node.labels:
                    entity["docstring"] = record['doc']
                    code_truth.append(entity)
                elif 'Document' in node.labels:
                    entity["last_modified"] = node.get('last_modified')
                    entity["doc_type"] = node.get('doc_type')
                    doc_claims.append(entity)
                
                # Capture relationships
                for neighbor in record['neighbors']:
                    graph_relationships.append({"from": record['name'], "to": neighbor})

            packet = {
                "meta": {
                    "query_id": str(uuid.uuid4()),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "project": project_name,
                    "question": question
                },
                "context_veracity": veracity,
                "code_truth": code_truth,
                "doc_claims": doc_claims,
                "graph_relationships": graph_relationships,
                "suggested_actions": [] # To be populated by LLM
            }
            
            VeracityLogger.log_packet(packet)
            
            # 4. Optional: Persist Report to Neo4j for UI visibility
            try:
                with driver.session() as report_session:
                    report_session.run("""
                    MERGE (r:VeracityReport {query_id: $query_id})
                    SET r.timestamp = $timestamp,
                        r.project = $project,
                        r.confidence_score = $score,
                        r.faults = $faults,
                        r.question = $question
                    """, {
                        "query_id": packet['meta']['query_id'],
                        "timestamp": packet['meta']['timestamp'],
                        "project": project_name,
                        "score": veracity['confidence_score'],
                        "faults": veracity['faults'],
                        "question": question
                    })
            except Exception as e:
                logger.error(f"Failed to persist VeracityReport: {e}")
                # Don't fail the query - report persistence is non-critical

            return packet
            
    finally:
        driver.close()

def main():
    parser = argparse.ArgumentParser(description="Query the Codebase Knowledge Graph (Neo4j)")
    parser.add_argument("--project-name", required=True, help="Unique name for the project (tenant)")
    parser.add_argument("--config", help="Path to configuration file (YAML)")
    parser.add_argument("--evidence-only", action="store_true", default=True,
                        help="Output evidence only, no LLM synthesis (default: True)")
    parser.add_argument("--allow-synthesis", action="store_true", default=False,
                        help="Allow LLM synthesis in output (default: False)")
    parser.add_argument("--json", action="store_true", default=False,
                        help="Output raw JSON packet (default: False)")
    parser.add_argument("query", type=str, help="The question to ask")
    args = parser.parse_args()

    # Determine output mode (--allow-synthesis overrides --evidence-only)
    if args.allow_synthesis:
        output_mode = EvidenceOutputMode.SYNTHESIS
    else:
        output_mode = EvidenceOutputMode.EVIDENCE_ONLY

    evidence_config = EvidenceQueryConfig(mode=output_mode)

    # Load configuration with hierarchy: CLI args -> env vars -> config file -> defaults
    config = ConfigLoader.load(config_file=args.config)

    # Configure logging from config
    logging.getLogger().setLevel(getattr(logging, config.logging.level))

    try:
        packet = query_graph(args.query, args.project_name, config, evidence_config)

        # Log veracity summary for observability
        logger.info(f"VERACITY REPORT - Confidence: {packet['context_veracity']['confidence_score']}%, Faults: {len(packet['context_veracity']['faults'])}")

        # JSON output mode - raw packet
        if args.json:
            # Add mode to meta for clarity
            packet['meta']['mode'] = output_mode.value
            print(json.dumps(packet, indent=2))
            return

        # User-facing formatted output
        print("\n" + "="*50)
        print(f"VERACITY REPORT (Confidence: {packet['context_veracity']['confidence_score']}%)")
        print(f"Mode: {output_mode.value}")
        if packet['context_veracity']['faults']:
            print("FAULTS DETECTED:")
            for fault in packet['context_veracity']['faults']:
                print(f"  - {fault}")
        print("="*50 + "\n")

        # Evidence-only mode: just print the evidence
        if output_mode == EvidenceOutputMode.EVIDENCE_ONLY:
            print("EVIDENCE (Code Truth):")
            for entity in packet.get('code_truth', []):
                print(f"  [{entity.get('type', ['Unknown'])[0]}] {entity.get('name')} ({entity.get('path', 'unknown')})")
                if entity.get('docstring'):
                    doc_preview = entity['docstring'][:100] + "..." if len(entity.get('docstring', '')) > 100 else entity.get('docstring', '')
                    print(f"      Doc: {doc_preview}")

            if packet.get('doc_claims'):
                print("\nEVIDENCE (Doc Claims):")
                for claim in packet['doc_claims']:
                    print(f"  [{claim.get('doc_type', 'Doc')}] {claim.get('name')} ({claim.get('path', 'unknown')})")

            if packet.get('suggested_actions'):
                print("\nSUGGESTED ACTIONS:")
                for action in packet['suggested_actions']:
                    print(f"  - {action}")

            # Log packet (without synthesis)
            VeracityLogger.log_packet(packet)

        # Synthesis mode: include LLM-generated brief
        else:
            logger.info("Synthesizing Technical Brief (synthesis mode enabled)...")
            print("Synthesizing Technical Brief...\n")

            # Redact dynamic fields for determinism in LLM reasoning
            prompt_packet = packet.copy()
            prompt_packet['meta'] = {
                "project": packet['meta'].get('project'),
                "question": packet['meta'].get('question')
            }

            prompt = f"""
[SYSTEM: AGENT-TO-AGENT HANDSHAKE]
Goal: Provide a high-fidelity Technical Brief for following agents (Cursor/Claude Code).
Rules:
1. No conversational fluff or introductory text.
2. Prioritize Code Truth over Doc Claims.
3. Explicitly list FAULTS and suggest REMEDIATIONS using file paths and line numbers.
4. Every claim MUST cite evidence sources from the CONTEXT PACKET.
5. Output MUST follow this EXACT XML schema:

<technical_brief>
    <veracity_summary confidence_score="FLOAT" is_stale="BOOL" />
    <code_entities>
        <entity id="UID">
            <truth>ENTITY_DESCRIPTION</truth>
            <faults>
                <fault description="DESCRIPTION" remediation="ACTION" path="PATH" line="INT" />
            </faults>
        </entity>
    </code_entities>
    <doc_claims>
        <claim id="UID">CLAIM_TEXT</claim>
    </doc_claims>
    <suggested_remediations>
        <action path="PATH" line="INT">DESCRIPTION</action>
    </suggested_remediations>
</technical_brief>

[CONTEXT PACKET]
{json.dumps(prompt_packet, indent=2)}

[USER QUERY]
{args.query}
"""

            # Deterministic Agent Handshake - using config for LLM settings
            response = ollama.chat(
                model=config.llm.model,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': config.llm.temperature,
                    'seed': config.llm.seed,
                    'repeat_penalty': config.llm.repeat_penalty
                }
            )

            brief = response['message']['content']
            logger.info(f"Technical Brief generated ({len(brief)} chars)")
            print("TECHNICAL BRIEF:")
            print(brief)

            # Log the brief as well
            packet['technical_brief'] = brief
            VeracityLogger.log_packet(packet)

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
Tree-sitter based multi-language AST parser for the Veracity Engine.

STORY-020: Multi-language AST support using tree-sitter

This module provides deterministic AST parsing for multiple programming languages,
replacing the regex-based fallback in build_graph.py with proper syntax tree analysis.

Supported languages:
- Python (via tree-sitter-python)
- TypeScript/JavaScript (via tree-sitter-typescript, tree-sitter-javascript)
- Go (via tree-sitter-go)
- Rust (via tree-sitter-rust)
- Java (via tree-sitter-java)

Usage:
    parser = TreeSitterParser()
    result = parser.parse_file(content, 'typescript')
    # result contains: functions, classes, imports, calls
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Tree-sitter imports with graceful degradation
try:
    import tree_sitter
    from tree_sitter import Language, Parser

    # Language-specific parsers
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_go
    import tree_sitter_rust
    import tree_sitter_java

    TREE_SITTER_AVAILABLE = True
except ImportError as e:
    TREE_SITTER_AVAILABLE = False
    logging.warning(f"tree-sitter not available: {e}. Falling back to regex parsing.")

logger = logging.getLogger(__name__)


@dataclass
class ParsedFunction:
    """Represents a parsed function/method."""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    parent_class: Optional[str] = None
    parameters: list[str] = field(default_factory=list)


@dataclass
class ParsedClass:
    """Represents a parsed class/struct/interface."""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    parent_classes: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)


@dataclass
class ParsedImport:
    """Represents a parsed import statement."""
    module: str
    alias: Optional[str] = None
    is_from_import: bool = False
    imported_names: list[str] = field(default_factory=list)


@dataclass
class ParsedCall:
    """Represents a function/method call."""
    name: str
    caller_function: Optional[str] = None
    line: int = 0


@dataclass
class ParseResult:
    """Result of parsing a source file."""
    functions: list[ParsedFunction] = field(default_factory=list)
    classes: list[ParsedClass] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    calls: list[ParsedCall] = field(default_factory=list)
    language: str = "unknown"
    success: bool = True
    error: Optional[str] = None


# Language mapping from file extensions
EXTENSION_TO_LANGUAGE = {
    # Python
    '.py': 'python',
    '.pyi': 'python',
    '.pyx': 'python',

    # JavaScript/TypeScript
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx',

    # Go
    '.go': 'go',

    # Rust
    '.rs': 'rust',

    # Java
    '.java': 'java',
}


class TreeSitterParser:
    """Multi-language AST parser using tree-sitter."""

    def __init__(self):
        """Initialize the parser with all supported language grammars."""
        self._parsers: dict[str, Parser] = {}
        self._languages: dict[str, Language] = {}

        if not TREE_SITTER_AVAILABLE:
            logger.warning("TreeSitterParser initialized but tree-sitter not available")
            return

        # Initialize language parsers
        self._init_languages()

    def _init_languages(self) -> None:
        """Initialize all supported language parsers."""
        language_modules = {
            'python': tree_sitter_python,
            'javascript': tree_sitter_javascript,
            'typescript': tree_sitter_typescript,
            'tsx': tree_sitter_typescript,
            'go': tree_sitter_go,
            'rust': tree_sitter_rust,
            'java': tree_sitter_java,
        }

        for lang_name, lang_module in language_modules.items():
            try:
                # Get the language from the module
                if lang_name == 'tsx':
                    language = Language(lang_module.language_tsx())
                elif lang_name == 'typescript':
                    language = Language(lang_module.language_typescript())
                else:
                    language = Language(lang_module.language())

                self._languages[lang_name] = language

                # Create parser for this language
                parser = Parser()
                parser.language = language
                self._parsers[lang_name] = parser

                logger.debug(f"Initialized tree-sitter parser for {lang_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize {lang_name} parser: {e}")

    def is_available(self) -> bool:
        """Check if tree-sitter is available."""
        return TREE_SITTER_AVAILABLE and len(self._parsers) > 0

    def get_language_for_extension(self, extension: str) -> Optional[str]:
        """Get the language name for a file extension."""
        return EXTENSION_TO_LANGUAGE.get(extension.lower())

    def supports_language(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self._parsers

    def parse_file(self, content: str, language: str) -> ParseResult:
        """
        Parse source code and extract structural information.

        Args:
            content: Source code content
            language: Language identifier (python, typescript, go, etc.)

        Returns:
            ParseResult with functions, classes, imports, and calls
        """
        if not self.is_available():
            return ParseResult(
                language=language,
                success=False,
                error="tree-sitter not available"
            )

        if language not in self._parsers:
            return ParseResult(
                language=language,
                success=False,
                error=f"Language '{language}' not supported"
            )

        try:
            parser = self._parsers[language]
            tree = parser.parse(content.encode('utf-8'))

            result = ParseResult(language=language)

            # Extract based on language
            if language == 'python':
                self._extract_python(tree.root_node, content, result)
            elif language in ('javascript', 'typescript', 'tsx'):
                self._extract_javascript(tree.root_node, content, result)
            elif language == 'go':
                self._extract_go(tree.root_node, content, result)
            elif language == 'rust':
                self._extract_rust(tree.root_node, content, result)
            elif language == 'java':
                self._extract_java(tree.root_node, content, result)

            return result

        except Exception as e:
            logger.error(f"Failed to parse {language} content: {e}")
            return ParseResult(
                language=language,
                success=False,
                error=str(e)
            )

    def _get_node_text(self, node, content: str) -> str:
        """Get the text content of a node."""
        return content[node.start_byte:node.end_byte]

    def _find_children(self, node, types: list[str]) -> list:
        """Find all immediate children of specified types."""
        return [child for child in node.children if child.type in types]

    def _find_descendants(self, node, types: list[str]) -> list:
        """Find all descendants of specified types."""
        results = []
        for child in node.children:
            if child.type in types:
                results.append(child)
            results.extend(self._find_descendants(child, types))
        return results

    def _extract_docstring(self, node, content: str) -> Optional[str]:
        """Extract docstring from a node (first string literal in body)."""
        if node.type in ('function_definition', 'class_definition'):
            body = None
            for child in node.children:
                if child.type == 'block':
                    body = child
                    break

            if body and body.children:
                first_stmt = body.children[0]
                if first_stmt.type == 'expression_statement':
                    expr = first_stmt.children[0] if first_stmt.children else None
                    if expr and expr.type == 'string':
                        return self._get_node_text(expr, content).strip('"\'')
        return None

    # ==========================================================================
    # Python Extraction
    # ==========================================================================

    def _extract_python(self, root, content: str, result: ParseResult) -> None:
        """Extract Python AST elements."""
        self._extract_python_imports(root, content, result)
        self._extract_python_classes(root, content, result)
        self._extract_python_functions(root, content, result)
        self._extract_python_calls(root, content, result)

    def _extract_python_imports(self, root, content: str, result: ParseResult) -> None:
        """Extract Python import statements."""
        for node in self._find_descendants(root, ['import_statement', 'import_from_statement']):
            if node.type == 'import_statement':
                # import foo, bar
                for name_node in self._find_descendants(node, ['dotted_name', 'aliased_import']):
                    if name_node.type == 'aliased_import':
                        name = self._get_node_text(name_node.children[0], content)
                        alias = self._get_node_text(name_node.children[-1], content) if len(name_node.children) > 1 else None
                    else:
                        name = self._get_node_text(name_node, content)
                        alias = None
                    result.imports.append(ParsedImport(module=name, alias=alias))

            elif node.type == 'import_from_statement':
                # from foo import bar, baz
                module_node = None
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_node = child
                        break

                if module_node:
                    module = self._get_node_text(module_node, content)
                    names = []
                    for name_node in self._find_descendants(node, ['dotted_name', 'aliased_import']):
                        if name_node != module_node:
                            if name_node.type == 'aliased_import':
                                names.append(self._get_node_text(name_node.children[0], content))
                            else:
                                names.append(self._get_node_text(name_node, content))

                    result.imports.append(ParsedImport(
                        module=module,
                        is_from_import=True,
                        imported_names=names
                    ))

    def _extract_python_classes(self, root, content: str, result: ParseResult, parent: str = "") -> None:
        """Extract Python class definitions."""
        for node in self._find_children(root, ['class_definition']):
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{parent}.{name}" if parent else name

                # Extract parent classes
                parents = []
                arg_list = None
                for child in node.children:
                    if child.type == 'argument_list':
                        arg_list = child
                        break

                if arg_list:
                    for arg in self._find_descendants(arg_list, ['identifier', 'attribute']):
                        parents.append(self._get_node_text(arg, content))

                result.classes.append(ParsedClass(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    docstring=self._extract_docstring(node, content),
                    parent_classes=parents
                ))

                # Extract nested classes and methods
                for child in node.children:
                    if child.type == 'block':
                        self._extract_python_classes(child, content, result, qualified)
                        self._extract_python_functions(child, content, result, qualified, is_method=True)

    def _extract_python_functions(self, root, content: str, result: ParseResult,
                                   parent: str = "", is_method: bool = False) -> None:
        """Extract Python function definitions."""
        func_types = ['function_definition']
        for node in self._find_children(root, func_types):
            name_node = None
            is_async = False

            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break

            # Check for async
            for child in node.children:
                if child.type == 'async':
                    is_async = True
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{parent}.{name}" if parent else name

                # Extract parameters
                params = []
                for param_node in self._find_descendants(node, ['parameters']):
                    for param in self._find_descendants(param_node, ['identifier']):
                        param_name = self._get_node_text(param, content)
                        if param_name not in ('self', 'cls'):
                            params.append(param_name)

                result.functions.append(ParsedFunction(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    docstring=self._extract_docstring(node, content),
                    is_async=is_async,
                    is_method=is_method,
                    parent_class=parent if is_method else None,
                    parameters=params
                ))

    def _extract_python_calls(self, root, content: str, result: ParseResult,
                              current_func: str = "") -> None:
        """Extract Python function calls."""
        for node in self._find_descendants(root, ['call']):
            func_node = node.children[0] if node.children else None
            if func_node:
                call_name = self._get_node_text(func_node, content)
                result.calls.append(ParsedCall(
                    name=call_name,
                    caller_function=current_func or None,
                    line=node.start_point[0] + 1
                ))

    # ==========================================================================
    # JavaScript/TypeScript Extraction
    # ==========================================================================

    def _extract_javascript(self, root, content: str, result: ParseResult) -> None:
        """Extract JavaScript/TypeScript AST elements."""
        self._extract_js_imports(root, content, result)
        self._extract_js_classes(root, content, result)
        self._extract_js_functions(root, content, result)
        self._extract_js_calls(root, content, result)

    def _extract_js_imports(self, root, content: str, result: ParseResult) -> None:
        """Extract JS/TS import statements."""
        for node in self._find_descendants(root, ['import_statement']):
            source_node = None
            for child in node.children:
                if child.type == 'string':
                    source_node = child
                    break

            if source_node:
                module = self._get_node_text(source_node, content).strip('"\'')
                names = []

                # Extract imported names
                for spec in self._find_descendants(node, ['import_specifier', 'identifier']):
                    name = self._get_node_text(spec, content)
                    if name not in ('import', 'from', 'as'):
                        names.append(name)

                result.imports.append(ParsedImport(
                    module=module,
                    is_from_import=True,
                    imported_names=names
                ))

    def _extract_js_classes(self, root, content: str, result: ParseResult, parent: str = "") -> None:
        """Extract JS/TS class definitions."""
        for node in self._find_descendants(root, ['class_declaration', 'class']):
            name_node = None
            for child in node.children:
                if child.type in ('identifier', 'type_identifier'):
                    name_node = child
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{parent}.{name}" if parent else name

                # Extract parent class (extends)
                parents = []
                for child in node.children:
                    if child.type == 'class_heritage':
                        for heritage in self._find_descendants(child, ['identifier', 'type_identifier']):
                            parents.append(self._get_node_text(heritage, content))

                # Extract interfaces (implements)
                interfaces = []
                for child in self._find_descendants(node, ['implements_clause']):
                    for iface in self._find_descendants(child, ['identifier', 'type_identifier']):
                        interfaces.append(self._get_node_text(iface, content))

                result.classes.append(ParsedClass(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent_classes=parents,
                    interfaces=interfaces
                ))

    def _extract_js_functions(self, root, content: str, result: ParseResult, parent: str = "") -> None:
        """Extract JS/TS function definitions."""
        func_types = ['function_declaration', 'arrow_function', 'method_definition', 'function']

        for node in self._find_descendants(root, func_types):
            name_node = None
            is_async = False

            # Check for async
            for child in node.children:
                if child.type == 'async':
                    is_async = True
                    break

            # Get function name
            for child in node.children:
                if child.type in ('identifier', 'property_identifier'):
                    name_node = child
                    break

            # For arrow functions in variable declarations
            if not name_node and node.parent and node.parent.type == 'variable_declarator':
                for child in node.parent.children:
                    if child.type == 'identifier':
                        name_node = child
                        break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{parent}.{name}" if parent else name

                result.functions.append(ParsedFunction(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    is_async=is_async,
                    is_method=node.type == 'method_definition'
                ))

    def _extract_js_calls(self, root, content: str, result: ParseResult) -> None:
        """Extract JS/TS function calls."""
        for node in self._find_descendants(root, ['call_expression']):
            func_node = node.children[0] if node.children else None
            if func_node:
                call_name = self._get_node_text(func_node, content)
                result.calls.append(ParsedCall(
                    name=call_name,
                    line=node.start_point[0] + 1
                ))

    # ==========================================================================
    # Go Extraction
    # ==========================================================================

    def _extract_go(self, root, content: str, result: ParseResult) -> None:
        """Extract Go AST elements."""
        self._extract_go_imports(root, content, result)
        self._extract_go_structs(root, content, result)
        self._extract_go_functions(root, content, result)
        self._extract_go_calls(root, content, result)

    def _extract_go_imports(self, root, content: str, result: ParseResult) -> None:
        """Extract Go import statements."""
        for node in self._find_descendants(root, ['import_declaration', 'import_spec']):
            if node.type == 'import_spec':
                path_node = None
                alias_node = None
                for child in node.children:
                    if child.type == 'interpreted_string_literal':
                        path_node = child
                    elif child.type == 'package_identifier':
                        alias_node = child

                if path_node:
                    module = self._get_node_text(path_node, content).strip('"')
                    alias = self._get_node_text(alias_node, content) if alias_node else None
                    result.imports.append(ParsedImport(module=module, alias=alias))

    def _extract_go_structs(self, root, content: str, result: ParseResult) -> None:
        """Extract Go struct definitions."""
        for node in self._find_descendants(root, ['type_declaration']):
            for child in node.children:
                if child.type == 'type_spec':
                    name_node = None
                    for spec_child in child.children:
                        if spec_child.type == 'type_identifier':
                            name_node = spec_child
                            break

                    if name_node:
                        name = self._get_node_text(name_node, content)
                        result.classes.append(ParsedClass(
                            name=name,
                            qualified_name=name,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        ))

    def _extract_go_functions(self, root, content: str, result: ParseResult) -> None:
        """Extract Go function definitions."""
        for node in self._find_descendants(root, ['function_declaration', 'method_declaration']):
            name_node = None
            receiver_type = None

            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                elif child.type == 'parameter_list' and not name_node:
                    # This is a method receiver
                    for param in self._find_descendants(child, ['type_identifier']):
                        receiver_type = self._get_node_text(param, content)
                        break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{receiver_type}.{name}" if receiver_type else name

                result.functions.append(ParsedFunction(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    is_method=receiver_type is not None,
                    parent_class=receiver_type
                ))

    def _extract_go_calls(self, root, content: str, result: ParseResult) -> None:
        """Extract Go function calls."""
        for node in self._find_descendants(root, ['call_expression']):
            func_node = node.children[0] if node.children else None
            if func_node:
                call_name = self._get_node_text(func_node, content)
                result.calls.append(ParsedCall(
                    name=call_name,
                    line=node.start_point[0] + 1
                ))

    # ==========================================================================
    # Rust Extraction
    # ==========================================================================

    def _extract_rust(self, root, content: str, result: ParseResult) -> None:
        """Extract Rust AST elements."""
        self._extract_rust_imports(root, content, result)
        self._extract_rust_structs(root, content, result)
        self._extract_rust_functions(root, content, result)
        self._extract_rust_calls(root, content, result)

    def _extract_rust_imports(self, root, content: str, result: ParseResult) -> None:
        """Extract Rust use statements."""
        for node in self._find_descendants(root, ['use_declaration']):
            path_parts = []
            for child in self._find_descendants(node, ['identifier', 'scoped_identifier']):
                path_parts.append(self._get_node_text(child, content))

            if path_parts:
                result.imports.append(ParsedImport(
                    module='::'.join(path_parts),
                    is_from_import=True
                ))

    def _extract_rust_structs(self, root, content: str, result: ParseResult) -> None:
        """Extract Rust struct/enum definitions."""
        for node in self._find_descendants(root, ['struct_item', 'enum_item', 'trait_item']):
            name_node = None
            for child in node.children:
                if child.type == 'type_identifier':
                    name_node = child
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                result.classes.append(ParsedClass(
                    name=name,
                    qualified_name=name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))

    def _extract_rust_functions(self, root, content: str, result: ParseResult) -> None:
        """Extract Rust function definitions."""
        for node in self._find_descendants(root, ['function_item']):
            name_node = None
            is_async = False

            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                elif child.type == 'async':
                    is_async = True

            if name_node:
                name = self._get_node_text(name_node, content)
                result.functions.append(ParsedFunction(
                    name=name,
                    qualified_name=name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    is_async=is_async
                ))

    def _extract_rust_calls(self, root, content: str, result: ParseResult) -> None:
        """Extract Rust function calls."""
        for node in self._find_descendants(root, ['call_expression']):
            func_node = node.children[0] if node.children else None
            if func_node:
                call_name = self._get_node_text(func_node, content)
                result.calls.append(ParsedCall(
                    name=call_name,
                    line=node.start_point[0] + 1
                ))

    # ==========================================================================
    # Java Extraction
    # ==========================================================================

    def _extract_java(self, root, content: str, result: ParseResult) -> None:
        """Extract Java AST elements."""
        self._extract_java_imports(root, content, result)
        self._extract_java_classes(root, content, result)
        self._extract_java_functions(root, content, result)
        self._extract_java_calls(root, content, result)

    def _extract_java_imports(self, root, content: str, result: ParseResult) -> None:
        """Extract Java import statements."""
        for node in self._find_descendants(root, ['import_declaration']):
            path_parts = []
            for child in self._find_descendants(node, ['identifier', 'scoped_identifier']):
                path_parts.append(self._get_node_text(child, content))

            if path_parts:
                result.imports.append(ParsedImport(
                    module='.'.join(path_parts),
                    is_from_import=True
                ))

    def _extract_java_classes(self, root, content: str, result: ParseResult, parent: str = "") -> None:
        """Extract Java class definitions."""
        for node in self._find_descendants(root, ['class_declaration', 'interface_declaration', 'enum_declaration']):
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                qualified = f"{parent}.{name}" if parent else name

                # Extract parent class (extends)
                parents = []
                for child in self._find_descendants(node, ['superclass']):
                    for type_node in self._find_descendants(child, ['type_identifier']):
                        parents.append(self._get_node_text(type_node, content))

                # Extract interfaces (implements)
                interfaces = []
                for child in self._find_descendants(node, ['super_interfaces']):
                    for iface in self._find_descendants(child, ['type_identifier']):
                        interfaces.append(self._get_node_text(iface, content))

                result.classes.append(ParsedClass(
                    name=name,
                    qualified_name=qualified,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent_classes=parents,
                    interfaces=interfaces
                ))

    def _extract_java_functions(self, root, content: str, result: ParseResult) -> None:
        """Extract Java method definitions."""
        for node in self._find_descendants(root, ['method_declaration', 'constructor_declaration']):
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break

            if name_node:
                name = self._get_node_text(name_node, content)
                result.functions.append(ParsedFunction(
                    name=name,
                    qualified_name=name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    is_method=True
                ))

    def _extract_java_calls(self, root, content: str, result: ParseResult) -> None:
        """Extract Java method calls."""
        for node in self._find_descendants(root, ['method_invocation']):
            name_node = None
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break

            if name_node:
                call_name = self._get_node_text(name_node, content)
                result.calls.append(ParsedCall(
                    name=call_name,
                    line=node.start_point[0] + 1
                ))


# Singleton instance for global use
_parser_instance: Optional[TreeSitterParser] = None


def get_parser() -> TreeSitterParser:
    """Get the global TreeSitterParser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = TreeSitterParser()
    return _parser_instance


def parse_source_file(content: str, extension: str) -> ParseResult:
    """
    Convenience function to parse a source file.

    Args:
        content: Source code content
        extension: File extension (e.g., '.py', '.ts', '.go')

    Returns:
        ParseResult with extracted AST elements
    """
    parser = get_parser()
    language = parser.get_language_for_extension(extension)

    if not language:
        return ParseResult(
            language="unknown",
            success=False,
            error=f"Unsupported file extension: {extension}"
        )

    return parser.parse_file(content, language)

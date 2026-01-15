"""
Code analyzer for detecting TODOs, incomplete code, and error patterns.

Supports multiple languages: Python (.py), JavaScript (.js), TypeScript (.ts)
Uses confidence scoring to reduce false positives.
"""

import re
import ast
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict


class IssueType(Enum):
    """Types of issues that can be detected."""
    TODO = "todo"
    FIXME = "fixme"
    INCOMPLETE = "incomplete"
    ERROR_PATTERN = "error_pattern"


class Confidence(Enum):
    """Confidence levels for detected issues."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Issue:
    """Represents a detected code issue."""
    issue_type: IssueType
    file_path: str
    line_number: int
    message: str
    confidence: Confidence
    context: str = ""


@dataclass
class AnalysisResult:
    """Results from analyzing a codebase."""
    all_issues: List[Issue] = field(default_factory=list)
    total_files_analyzed: int = 0
    issues_by_type: Dict[IssueType, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def total_issues(self) -> int:
        """Get total number of issues."""
        return len(self.all_issues)

    def group_by_file(self) -> Dict[str, List[Issue]]:
        """Group issues by file path."""
        result = defaultdict(list)
        for issue in self.all_issues:
            result[issue.file_path].append(issue)
        return dict(result)

    def get_sorted_issues_by_severity(self) -> List[Issue]:
        """Sort issues by confidence/severity (HIGH first)."""
        confidence_order = {
            Confidence.HIGH: 0,
            Confidence.MEDIUM: 1,
            Confidence.LOW: 2
        }
        return sorted(self.all_issues, key=lambda x: confidence_order[x.confidence])

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        issues_by_confidence = defaultdict(int)
        for issue in self.all_issues:
            issues_by_confidence[issue.confidence.value] += 1

        return {
            'total_files': self.total_files_analyzed,
            'total_issues': self.total_issues,
            'issues_by_type': {k.value: v for k, v in self.issues_by_type.items()},
            'issues_by_confidence': dict(issues_by_confidence)
        }


class TodoScanner:
    """Scanner for TODO and FIXME comments."""

    def __init__(self):
        # Patterns for TODO/FIXME detection
        # Matches: # TODO, // TODO, or bare TODO (in docstrings)
        self.todo_pattern = re.compile(r'(?:#|//)\s*TODO:?\s*(.+)|^\s*TODO:?\s*(.+)', re.IGNORECASE)
        self.fixme_pattern = re.compile(r'(?:#|//)\s*FIXME:?\s*(.+)|^\s*FIXME:?\s*(.+)', re.IGNORECASE)

    def scan(self, code: str, file_extension: str, file_path: str) -> List[Issue]:
        """Scan code for TODO/FIXME comments with confidence scoring."""
        issues = []
        lines = code.split('\n')

        in_docstring = False
        docstring_delim = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstring state (Python)
            if '"""' in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_delim = '"""'
                elif docstring_delim == '"""':
                    in_docstring = False
                    docstring_delim = None
            elif "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_delim = "'''"
                elif docstring_delim == "'''":
                    in_docstring = False
                    docstring_delim = None

            # Detect if in string literal (simple check)
            in_string = self._is_in_string_literal(line)

            # Check for TODO
            todo_match = self.todo_pattern.search(line)
            if todo_match:
                # Extract message from whichever group matched
                message = todo_match.group(1) or todo_match.group(2) or ""
                confidence = self._determine_confidence(line, in_docstring, in_string)

                # Skip LOW confidence in strings
                if in_string and confidence == Confidence.LOW:
                    continue

                issues.append(Issue(
                    issue_type=IssueType.TODO,
                    file_path=file_path,
                    line_number=i,
                    message=message.strip(),
                    confidence=confidence
                ))

            # Check for FIXME
            fixme_match = self.fixme_pattern.search(line)
            if fixme_match:
                # Extract message from whichever group matched
                message = fixme_match.group(1) or fixme_match.group(2) or ""
                confidence = self._determine_confidence(line, in_docstring, in_string)

                # Skip LOW confidence in strings
                if in_string and confidence == Confidence.LOW:
                    continue

                issues.append(Issue(
                    issue_type=IssueType.FIXME,
                    file_path=file_path,
                    line_number=i,
                    message=message.strip(),
                    confidence=confidence
                ))

        return issues

    def _is_in_string_literal(self, line: str) -> bool:
        """Check if line contains TODO/FIXME in a string literal."""
        # Simple heuristic: check if TODO/FIXME appears after quote and before closing quote
        # This is not perfect but works for most cases

        # Remove comments first
        if '#' in line:
            comment_pos = line.find('#')
            before_comment = line[:comment_pos]
            if 'TODO' in before_comment or 'FIXME' in before_comment:
                # It's in a string literal if it's before the comment
                return '"' in before_comment or "'" in before_comment

        # Check for string literal patterns
        if ('"TODO' in line or "'TODO" in line or
            '"FIXME' in line or "'FIXME" in line):
            return True

        return False

    def _determine_confidence(self, line: str, in_docstring: bool, in_string: bool) -> Confidence:
        """Determine confidence level based on context."""
        if in_string and ('"' in line or "'" in line):
            return Confidence.LOW
        elif in_docstring or '"""' in line or "'''" in line:
            return Confidence.MEDIUM
        elif '#' in line or '//' in line:
            return Confidence.HIGH
        else:
            return Confidence.HIGH


class IncompleteDetector:
    """Detector for incomplete code (empty functions, NotImplementedError, etc)."""

    def scan(self, code: str, file_extension: str, file_path: str) -> List[Issue]:
        """Scan code for incomplete implementations."""
        issues = []

        if file_extension == '.py':
            issues.extend(self._scan_python(code, file_path))
        elif file_extension in ['.js', '.ts']:
            issues.extend(self._scan_javascript(code, file_path))

        return issues

    def _scan_python(self, code: str, file_path: str) -> List[Issue]:
        """Scan Python code using AST."""
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check for empty functions with only pass
                if isinstance(node, ast.FunctionDef):
                    if self._is_empty_function(node):
                        # Check if it's an abstract method
                        is_abstract = self._is_abstract_method(node)
                        confidence = Confidence.LOW if is_abstract else Confidence.HIGH

                        if is_abstract:
                            # Skip abstract methods entirely
                            continue

                        issues.append(Issue(
                            issue_type=IssueType.INCOMPLETE,
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Function '{node.name}' has empty implementation",
                            confidence=confidence
                        ))

                # Check for NotImplementedError
                if isinstance(node, ast.Raise):
                    if isinstance(node.exc, ast.Call):
                        if isinstance(node.exc.func, ast.Name):
                            if node.exc.func.id == 'NotImplementedError':
                                issues.append(Issue(
                                    issue_type=IssueType.INCOMPLETE,
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    message="NotImplementedError placeholder",
                                    confidence=Confidence.HIGH
                                ))

                # Check for empty classes
                if isinstance(node, ast.ClassDef):
                    if self._is_empty_class(node):
                        issues.append(Issue(
                            issue_type=IssueType.INCOMPLETE,
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Class '{node.name}' has no methods",
                            confidence=Confidence.MEDIUM
                        ))

        except SyntaxError:
            # Skip files with syntax errors
            pass

        return issues

    def _is_empty_function(self, node: ast.FunctionDef) -> bool:
        """Check if function body only contains pass or docstring."""
        body = node.body

        # Filter out docstrings
        filtered_body = [
            stmt for stmt in body
            if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
        ]

        # Check if only pass remains
        if len(filtered_body) == 1:
            if isinstance(filtered_body[0], ast.Pass):
                return True

        return False

    def _is_abstract_method(self, node: ast.FunctionDef) -> bool:
        """Check if function is an abstract method."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == 'abstractmethod':
                    return True
        return False

    def _is_empty_class(self, node: ast.ClassDef) -> bool:
        """Check if class has no methods."""
        body = node.body

        # Filter out docstrings
        filtered_body = [
            stmt for stmt in body
            if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
        ]

        # Check if only pass remains
        if len(filtered_body) == 1:
            if isinstance(filtered_body[0], ast.Pass):
                return True

        return False

    def _scan_javascript(self, code: str, file_path: str) -> List[Issue]:
        """Scan JavaScript/TypeScript code using regex patterns."""
        issues = []

        # Pattern for empty function bodies (multi-line support)
        empty_function_pattern = re.compile(
            r'function\s+\w+\s*\([^)]*\)\s*\{\s*(?://[^\n]*)?\s*\}',
            re.MULTILINE | re.DOTALL
        )

        # Pattern for throw new Error("Not implemented")
        not_implemented_pattern = re.compile(
            r'throw\s+new\s+Error\s*\(\s*["\'].*not\s+implemented.*["\']\s*\)',
            re.IGNORECASE
        )

        # Find all empty functions
        for match in empty_function_pattern.finditer(code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(Issue(
                issue_type=IssueType.INCOMPLETE,
                file_path=file_path,
                line_number=line_number,
                message="Empty function implementation",
                confidence=Confidence.HIGH
            ))

        # Find all "not implemented" errors
        for match in not_implemented_pattern.finditer(code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(Issue(
                issue_type=IssueType.INCOMPLETE,
                file_path=file_path,
                line_number=line_number,
                message="Not implemented placeholder",
                confidence=Confidence.HIGH
            ))

        return issues


class ErrorPatternDetector:
    """Detector for error patterns and anti-patterns."""

    def scan(self, code: str, file_extension: str, file_path: str) -> List[Issue]:
        """Scan code for error patterns."""
        # Skip test files
        if self._is_test_file(file_path):
            return []

        issues = []

        if file_extension == '.py':
            issues.extend(self._scan_python_errors(code, file_path))
        elif file_extension in ['.js', '.ts']:
            issues.extend(self._scan_javascript_errors(code, file_path))

        return issues

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        # Get just the filename, not the full path
        filename = Path(file_path).name

        test_patterns = [
            'test.js', 'test.ts', 'spec.js', 'spec.ts',
            'test_', '_test.py', '.test.', '.spec.'
        ]
        return any(pattern in filename for pattern in test_patterns)

    def _scan_python_errors(self, code: str, file_path: str) -> List[Issue]:
        """Scan Python code for error patterns."""
        issues = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check for empty except blocks
                if isinstance(node, ast.ExceptHandler):
                    if self._is_empty_except(node):
                        issues.append(Issue(
                            issue_type=IssueType.ERROR_PATTERN,
                            file_path=file_path,
                            line_number=node.lineno,
                            message="Empty except block (swallowing errors)",
                            confidence=Confidence.HIGH
                        ))

                    # Check for bare except
                    if node.type is None:
                        issues.append(Issue(
                            issue_type=IssueType.ERROR_PATTERN,
                            file_path=file_path,
                            line_number=node.lineno,
                            message="Bare except clause (anti-pattern)",
                            confidence=Confidence.HIGH
                        ))

        except SyntaxError:
            pass

        return issues

    def _is_empty_except(self, node: ast.ExceptHandler) -> bool:
        """Check if except block only contains pass."""
        if len(node.body) == 1:
            if isinstance(node.body[0], ast.Pass):
                return True
        return False

    def _scan_javascript_errors(self, code: str, file_path: str) -> List[Issue]:
        """Scan JavaScript/TypeScript code for error patterns."""
        issues = []

        # Pattern for console.log
        console_log_pattern = re.compile(r'console\.log\s*\(')

        # Pattern for empty catch blocks (multi-line support)
        empty_catch_pattern = re.compile(
            r'catch\s*\([^)]*\)\s*\{\s*(?://[^\n]*)?\s*\}',
            re.MULTILINE | re.DOTALL
        )

        # Find all console.log occurrences
        for match in console_log_pattern.finditer(code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(Issue(
                issue_type=IssueType.ERROR_PATTERN,
                file_path=file_path,
                line_number=line_number,
                message="console.log found in production code",
                confidence=Confidence.HIGH
            ))

        # Find all empty catch blocks
        for match in empty_catch_pattern.finditer(code):
            line_number = code[:match.start()].count('\n') + 1
            issues.append(Issue(
                issue_type=IssueType.ERROR_PATTERN,
                file_path=file_path,
                line_number=line_number,
                message="Empty catch block (swallowing error)",
                confidence=Confidence.HIGH
            ))

        return issues


class CodeAnalyzer:
    """Main orchestrator for code analysis."""

    def __init__(self, min_confidence: Confidence = None):
        """Initialize analyzer with optional confidence filter."""
        self.min_confidence = min_confidence
        self.todo_scanner = TodoScanner()
        self.incomplete_detector = IncompleteDetector()
        self.error_pattern_detector = ErrorPatternDetector()

        # Supported file extensions
        self.supported_extensions = {'.py', '.js', '.ts'}

        # Confidence order for filtering
        self.confidence_order = {
            Confidence.HIGH: 3,
            Confidence.MEDIUM: 2,
            Confidence.LOW: 1
        }

    def analyze_codebase(self, root_path: str) -> AnalysisResult:
        """Analyze entire codebase directory."""
        root = Path(root_path)

        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root_path}")

        result = AnalysisResult()

        # Walk directory tree
        for file_path in root.rglob('*'):
            if not file_path.is_file():
                continue

            # Filter by extension
            if file_path.suffix not in self.supported_extensions:
                continue

            # Skip test files
            if self._is_test_file(str(file_path)):
                continue

            # Analyze file
            issues = self._analyze_file(file_path)

            # Filter by confidence if specified
            if self.min_confidence:
                issues = self._filter_by_confidence(issues)

            result.all_issues.extend(issues)
            result.total_files_analyzed += 1

        # Update issue counts by type
        for issue in result.all_issues:
            result.issues_by_type[issue.issue_type] += 1

        return result

    def _analyze_file(self, file_path: Path) -> List[Issue]:
        """Analyze a single file."""
        issues = []

        try:
            code = file_path.read_text(encoding='utf-8')
            extension = file_path.suffix
            file_str = str(file_path)

            # Run all scanners
            issues.extend(self.todo_scanner.scan(code, extension, file_str))
            issues.extend(self.incomplete_detector.scan(code, extension, file_str))
            issues.extend(self.error_pattern_detector.scan(code, extension, file_str))

        except Exception:
            # Skip files that can't be read
            pass

        return issues

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        # Get just the filename, not the full path
        filename = Path(file_path).name

        test_patterns = [
            'test.js', 'test.ts', 'spec.js', 'spec.ts',
            'test_', '_test.py', '.test.', '.spec.'
        ]
        return any(pattern in filename for pattern in test_patterns)

    def _filter_by_confidence(self, issues: List[Issue]) -> List[Issue]:
        """Filter issues by minimum confidence level."""
        min_level = self.confidence_order[self.min_confidence]
        return [
            issue for issue in issues
            if self.confidence_order[issue.confidence] >= min_level
        ]

"""
Comprehensive test suite for code_analyzer.py

Tests for TODO/FIXME scanning, incomplete code detection, error pattern detection,
and false positive prevention with confidence scoring.

Following TDD principles - tests written before implementation.
"""

import pytest
import ast
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import will fail initially (TDD approach - implementation doesn't exist yet)
try:
    from core.code_analyzer import (
        TodoScanner,
        IncompleteDetector,
        ErrorPatternDetector,
        CodeAnalyzer,
        AnalysisResult,
        Issue,
        IssueType,
        Confidence
    )
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    # Define placeholders for test structure
    class IssueType:
        TODO = "todo"
        FIXME = "fixme"
        INCOMPLETE = "incomplete"
        ERROR_PATTERN = "error_pattern"

    class Confidence:
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"


# Mark all tests to expect import failure initially
pytestmark = pytest.mark.skipif(
    not ANALYZER_AVAILABLE,
    reason="code_analyzer.py not implemented yet (TDD)"
)


class TestTodoScanner:
    """Test suite for TODO/FIXME scanning with confidence scoring."""

    def test_detect_todo_in_comment(self):
        """Test detection of TODO in code comments."""
        code = '''
def process_data():
    # TODO: Add validation logic here
    return data
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'test.py')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.TODO
        assert issues[0].line_number == 3
        assert issues[0].confidence == Confidence.HIGH
        assert 'validation logic' in issues[0].message

    def test_detect_fixme_in_comment(self):
        """Test detection of FIXME in code comments."""
        code = '''
async def fetch_data():
    # FIXME: Handle connection timeout
    response = await client.get(url)
    return response
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'api.py')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.FIXME
        assert issues[0].line_number == 3
        assert issues[0].confidence == Confidence.HIGH

    def test_ignore_todo_in_string_literal(self):
        """Test that TODO in string literals are ignored (false positive prevention)."""
        code = '''
def get_help_text():
    return "Remember to TODO: update this later"
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'help.py')

        # Should detect this as LOW confidence or skip entirely
        if len(issues) > 0:
            assert issues[0].confidence == Confidence.LOW
        else:
            assert len(issues) == 0

    def test_todo_in_docstring_medium_confidence(self):
        """Test that TODO in docstrings get medium confidence."""
        code = '''
def authenticate_user(username, password):
    """
    Authenticate a user.

    TODO: Add OAuth2 support
    """
    return check_credentials(username, password)
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'auth.py')

        assert len(issues) == 1
        assert issues[0].confidence == Confidence.MEDIUM
        assert 'OAuth2' in issues[0].message

    def test_multiple_todos_in_same_file(self):
        """Test detection of multiple TODO/FIXME in same file."""
        code = '''
# TODO: Refactor this module
def process():
    # FIXME: Memory leak here
    data = load_data()
    # TODO: Add error handling
    return transform(data)
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'processor.py')

        assert len(issues) == 3
        todo_count = sum(1 for i in issues if i.issue_type == IssueType.TODO)
        fixme_count = sum(1 for i in issues if i.issue_type == IssueType.FIXME)
        assert todo_count == 2
        assert fixme_count == 1

    def test_javascript_todo_detection(self):
        """Test TODO detection in JavaScript files."""
        code = '''
function initializeApp() {
    // TODO: Load configuration from server
    const config = getDefaultConfig();
    return config;
}
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.js', 'app.js')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.TODO

    def test_typescript_fixme_detection(self):
        """Test FIXME detection in TypeScript files."""
        code = '''
class UserService {
    // FIXME: Add proper error handling
    async getUser(id: string): Promise<User> {
        return fetch(`/api/users/${id}`);
    }
}
'''
        scanner = TodoScanner()
        issues = scanner.scan(code, '.ts', 'user-service.ts')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.FIXME


class TestIncompleteDetector:
    """Test suite for incomplete code detection."""

    def test_detect_empty_function_body(self):
        """Test detection of function with only pass statement."""
        code = '''
def calculate_total(items):
    pass
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'math_utils.py')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.INCOMPLETE
        assert issues[0].confidence == Confidence.HIGH
        assert 'empty' in issues[0].message.lower() or 'incomplete' in issues[0].message.lower()

    def test_detect_not_implemented_error(self):
        """Test detection of NotImplementedError placeholder."""
        code = '''
class PaymentProcessor:
    def process_payment(self, amount):
        raise NotImplementedError("Payment processing not implemented yet")
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'payment.py')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.INCOMPLETE
        assert issues[0].confidence == Confidence.HIGH

    def test_detect_empty_class(self):
        """Test detection of class with no methods."""
        code = '''
class EmptyModel:
    pass
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'models.py')

        assert len(issues) == 1
        assert issues[0].confidence == Confidence.MEDIUM

    def test_ignore_abstract_base_class_pass(self):
        """Test that ABC classes with pass are treated differently."""
        code = '''
from abc import ABC, abstractmethod

class BaseProcessor(ABC):
    @abstractmethod
    def process(self):
        pass
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'base.py')

        # Should either skip or mark as LOW confidence
        if len(issues) > 0:
            assert issues[0].confidence == Confidence.LOW
        else:
            assert len(issues) == 0

    def test_javascript_empty_function(self):
        """Test detection of empty JavaScript function."""
        code = '''
function processData(data) {
    // Empty implementation
}
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.js', 'processor.js')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.INCOMPLETE

    def test_typescript_unimplemented_method(self):
        """Test detection of TypeScript method that throws error."""
        code = '''
class DataService {
    fetchData(): Promise<Data> {
        throw new Error("Not implemented");
    }
}
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.ts', 'data-service.ts')

        assert len(issues) == 1
        assert issues[0].confidence == Confidence.HIGH


class TestErrorPatternDetector:
    """Test suite for error pattern and anti-pattern detection."""

    def test_detect_empty_except_block(self):
        """Test detection of empty except block (swallowing errors)."""
        code = '''
def load_config():
    try:
        return read_file('config.json')
    except Exception:
        pass
'''
        detector = ErrorPatternDetector()
        issues = detector.scan(code, '.py', 'config.py')

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.ERROR_PATTERN
        assert issues[0].confidence == Confidence.HIGH
        assert 'except' in issues[0].message.lower() or 'error' in issues[0].message.lower()

    def test_detect_bare_except(self):
        """Test detection of bare except clause (anti-pattern)."""
        code = '''
def process_request():
    try:
        handle_request()
    except:
        log_error("Failed")
'''
        detector = ErrorPatternDetector()
        issues = detector.scan(code, '.py', 'handler.py')

        assert len(issues) == 1
        assert issues[0].confidence == Confidence.HIGH

    def test_detect_console_log_in_production(self):
        """Test detection of console.log in production code."""
        code = '''
function processOrder(order) {
    console.log("Processing order:", order.id);
    return submitOrder(order);
}
'''
        detector = ErrorPatternDetector()
        issues = detector.scan(code, '.js', 'orders.js')

        assert len(issues) == 1
        assert 'console.log' in issues[0].message.lower()

    def test_ignore_console_log_in_test_file(self):
        """Test that console.log in test files are ignored."""
        code = '''
test('processes order correctly', () => {
    console.log("Debug: testing order processing");
    expect(processOrder(order)).toBeDefined();
});
'''
        detector = ErrorPatternDetector()
        issues = detector.scan(code, '.test.js', 'orders.test.js')

        # Should skip test files
        assert len(issues) == 0

    def test_detect_empty_catch_block_javascript(self):
        """Test detection of empty catch block in JavaScript."""
        code = '''
async function fetchData() {
    try {
        const response = await fetch(url);
        return response.json();
    } catch (error) {
        // Empty catch - swallowing error
    }
}
'''
        detector = ErrorPatternDetector()
        issues = detector.scan(code, '.js', 'api.js')

        assert len(issues) == 1
        assert issues[0].confidence == Confidence.HIGH


class TestCodeAnalyzer:
    """Integration tests for the main CodeAnalyzer orchestrator."""

    @pytest.fixture
    def sample_codebase(self, tmp_path):
        """Create a sample codebase directory for testing."""
        project = tmp_path / "test_project"
        project.mkdir()

        # Python file with issues
        py_file = project / "incomplete.py"
        py_file.write_text('''
def process_data():
    # TODO: Implement this function
    pass

def handle_error():
    try:
        risky_operation()
    except:
        pass
''')

        # JavaScript file with issues
        js_file = project / "debug.js"
        js_file.write_text('''
function debugHelper() {
    console.log("Debug info");
    // FIXME: Remove before production
}
''')

        # Test file (should be ignored)
        test_file = project / "example.test.js"
        test_file.write_text('''
test('example', () => {
    console.log("This should be ignored");
});
''')

        # Non-code file (should be ignored)
        txt_file = project / "notes.txt"
        txt_file.write_text("TODO: Remember to do something")

        return project

    def test_analyze_codebase_basic(self, sample_codebase):
        """Test full codebase analysis."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        assert result.total_files_analyzed > 0
        assert result.total_issues > 0
        assert result.issues_by_type[IssueType.TODO] > 0
        assert result.issues_by_type[IssueType.FIXME] > 0
        assert result.issues_by_type[IssueType.INCOMPLETE] > 0
        assert result.issues_by_type[IssueType.ERROR_PATTERN] > 0

    def test_file_filtering_python_js_ts_only(self, sample_codebase):
        """Test that only .py, .js, .ts files are analyzed."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        # Should analyze .py and .js files
        analyzed_extensions = {Path(issue.file_path).suffix for issue in result.all_issues}
        assert '.py' in analyzed_extensions or '.js' in analyzed_extensions

        # Should NOT analyze .txt files
        txt_issues = [i for i in result.all_issues if i.file_path.endswith('.txt')]
        assert len(txt_issues) == 0

    def test_test_file_filtering(self, sample_codebase):
        """Test that test files are excluded from analysis."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        # Should NOT flag console.log in test files
        test_file_issues = [
            i for i in result.all_issues
            if 'test.js' in i.file_path
        ]
        assert len(test_file_issues) == 0

    def test_confidence_filtering(self, sample_codebase):
        """Test filtering issues by confidence level."""
        analyzer = CodeAnalyzer(min_confidence=Confidence.HIGH)
        result = analyzer.analyze_codebase(str(sample_codebase))

        # All issues should have HIGH confidence
        for issue in result.all_issues:
            assert issue.confidence == Confidence.HIGH

    def test_issue_grouping_by_file(self, sample_codebase):
        """Test that issues are properly grouped by file."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        issues_by_file = result.group_by_file()
        assert len(issues_by_file) > 0

        # Each file should have a list of issues
        for file_path, issues in issues_by_file.items():
            assert isinstance(issues, list)
            assert all(isinstance(i, Issue) for i in issues)

    def test_empty_directory_handling(self, tmp_path):
        """Test analysis of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(empty_dir))

        assert result.total_files_analyzed == 0
        assert result.total_issues == 0

    def test_nonexistent_directory_error(self):
        """Test error handling for nonexistent directory."""
        analyzer = CodeAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_codebase("/nonexistent/path")

    def test_issue_sorting_by_severity(self, sample_codebase):
        """Test that issues can be sorted by severity/confidence."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        sorted_issues = result.get_sorted_issues_by_severity()

        # HIGH confidence issues should come first
        high_issues = [i for i in sorted_issues if i.confidence == Confidence.HIGH]
        if len(high_issues) > 0:
            assert sorted_issues[0].confidence == Confidence.HIGH

    def test_summary_statistics(self, sample_codebase):
        """Test generation of summary statistics."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_codebase(str(sample_codebase))

        summary = result.get_summary()

        assert 'total_files' in summary
        assert 'total_issues' in summary
        assert 'issues_by_type' in summary
        assert 'issues_by_confidence' in summary
        assert summary['total_files'] > 0
        assert summary['total_issues'] > 0


class TestConfidenceScoring:
    """Test suite for confidence scoring algorithm."""

    def test_todo_in_comment_high_confidence(self):
        """Test that TODO in regular comment gets HIGH confidence."""
        code = '# TODO: Fix this'
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'test.py')

        assert issues[0].confidence == Confidence.HIGH

    def test_todo_in_string_low_confidence(self):
        """Test that TODO in string gets LOW confidence or is ignored."""
        code = 'msg = "TODO: Check this"'
        scanner = TodoScanner()
        issues = scanner.scan(code, '.py', 'test.py')

        if len(issues) > 0:
            assert issues[0].confidence != Confidence.HIGH

    def test_incomplete_with_not_implemented_high_confidence(self):
        """Test that NotImplementedError gets HIGH confidence."""
        code = '''
def foo():
    raise NotImplementedError()
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'test.py')

        assert issues[0].confidence == Confidence.HIGH

    def test_empty_class_medium_confidence(self):
        """Test that empty class gets MEDIUM confidence (could be placeholder)."""
        code = '''
class EmptyClass:
    pass
'''
        detector = IncompleteDetector()
        issues = detector.scan(code, '.py', 'test.py')

        # Empty classes are less severe than empty functions
        assert issues[0].confidence in [Confidence.MEDIUM, Confidence.LOW]

# src/ast_detection/tests/test_parser.py
"""Unit tests for the Parser module."""

import ast
import pytest
from src.ast_detection.parser import Parser, sanitize_code
class TestParser:
    """Test suite for the Parser class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = Parser()

    def test_parse_simple_code(self):
        """Test parsing of simple Python code."""
        code = "x = 1 + 2"
        ast_root = self.parser.parse(code)
        assert ast_root is not None
        assert isinstance(ast_root, ast.AST)

    def test_parse_function(self):
        """Test parsing of function definition."""
        code = "def foo(x):\n    return x * 2"
        ast_root = self.parser.parse(code)
        assert ast_root is not None
        
        # Find the function definition
        func_def = None
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                func_def = node
                break
        assert func_def is not None
        assert func_def.name == "foo"

    def test_parse_class(self):
        """Test parsing of class definition."""
        code = "class MyClass:\n    def method(self):\n        pass"
        ast_root = self.parser.parse(code)
        assert ast_root is not None
        
        # Find the class definition
        class_def = None
        for node in ast.walk(ast_root):
            if isinstance(node, ast.ClassDef):
                class_def = node
                break
        assert class_def is not None
        assert class_def.name == "MyClass"

    def test_is_valid_python_valid(self):
        """Test is_valid_python with valid code."""
        assert self.parser.is_valid_python("x = 1")
        assert self.parser.is_valid_python("def foo(): pass")

    def test_is_valid_python_invalid(self):
        """Test is_valid_python with invalid code."""
        assert not self.parser.is_valid_python("def foo(")
        assert not self.parser.is_valid_python("x = 1 +")

    def test_parse_with_sanitize(self):
        """Test parsing with sanitization enabled."""
        code = "x = 1"
        ast_root = self.parser.parse(code)
        assert ast_root is not None

    def test_parse_without_sanitize(self):
        """Test parsing without sanitization."""
        parser = Parser(sanitize=False)
        code = "x = 1"
        ast_root = parser.parse(code)
        assert ast_root is not None

    def test_parse_invalid_syntax(self):
        """Test parsing invalid syntax raises ValueError."""
        with pytest.raises(ValueError):
            self.parser.parse("def foo(")

    def test_parse_empty_code(self):
        """Test parsing empty code raises ValueError."""
        with pytest.raises(ValueError):
            self.parser.parse("")

    def test_sanitize_code_basic(self):
        """Test basic code sanitization."""
        code = "x = 1 + 2"
        sanitized = sanitize_code(code)
        assert sanitized == code

    def test_sanitize_code_with_imports(self):
        """Test sanitization with imports."""
        code = "import os\nx = 1"
        sanitized = sanitize_code(code)
        assert sanitized == code

    def test_sanitize_code_empty(self):
        """Test sanitization of empty code."""
        with pytest.raises(ValueError):
            sanitize_code("")

    def test_parse_multiple_statements(self):
        """Test parsing multiple statements."""
        code = """
x = 1
y = 2
if x > y:
    z = x
else:
    z = y
"""
        ast_root = self.parser.parse(code)
        assert ast_root is not None

    def test_parse_complex_structure(self):
        """Test parsing complex structure with nested elements."""
        code = """
class MyClass:
    def __init__(self, x):
        self.x = x
    
    def method(self, y):
        return self.x + y
"""
        ast_root = self.parser.parse(code)
        assert ast_root is not None

    def test_is_safe_code_safe(self):
        """Test is_safe_code with safe code."""
        assert self.parser.is_safe_code("x = 1")
        assert self.parser.is_safe_code("import sys")

    def test_is_safe_code_unsafe(self):
        """Test is_safe_code with unsafe code."""
        assert not self.parser.is_safe_code("eval('1+1')")
        assert not self.parser.is_safe_code("exec('import os')")

    def test_parse_with_comments(self):
        """Test parsing code with comments."""
        code = """
# This is a comment
x = 1  # inline comment
print(x)  # another comment
"""
        ast_root = self.parser.parse(code)
        assert ast_root is not None

    def test_parse_with_strings(self):
        """Test parsing code with string literals."""
        code = 'x = "hello"\ny = \'world\'\nz = """multi\nline"""'
        ast_root = self.parser.parse(code)
        assert ast_root is not None
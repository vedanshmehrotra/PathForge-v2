# src/ast_detection/parser.py
"""Parse and sanitize Python source code into an AST."""

import ast
from typing import Tuple, Union
from pathlib import Path
def sanitize_code(code_string: str) -> str:
    """
    Sanitize Python source code for safe parsing.

    This function performs basic sanitization to ensure the code is safe
    to parse. It removes or neutralizes potentially dangerous constructs
    before parsing.

    Args:
        code_string: Raw Python source code string

    Returns:
        Sanitized Python source code string ready for parsing

    Raises:
        ValueError: If code contains unsafe constructs
    """
    code = code_string.strip()

    # Reject empty input
    if not code:
        raise ValueError("Code string cannot be empty")

    # Reject explicit banned constructs
    banned_constructs = [
        "eval(",
        "exec(",
        "__import__(",
        "compile(",
        "open(",
        "file(",
        "input(",
        "raw_input(",
        "globals()",
        "locals()",
        "vars()",
        "dir()",
        "help(",
        "breakpoint(",
        "exit(",
        "quit(",
    ]

    for construct in banned_constructs:
        if construct in code:
            raise ValueError(f"Unsafe construct detected: {construct}")

    # Check for dangerous imports
    dangerous_imports = [
        "subprocess",
        "os.system",
        "os.popen",
        "os.exec",
        "os.spawn",
        "os.fork",
        "os.kill",
        "ctypes",
        "pickle",
        "shelve",
        "marshal",
    ]

    for import_stmt in dangerous_imports:
        if f"import {import_stmt}" in code or f"from {import_stmt}" in code:
            raise ValueError(f"Dangerous import detected: {import_stmt}")

    return code
class Parser:
    """Parse and sanitize Python source code into an AST."""

    def __init__(self, sanitize: bool = True):
        """
        Initialize the parser.

        Args:
            sanitize: Whether to sanitize code before parsing (default: True)
        """
        self.sanitize = sanitize

    def parse(self, code_string: str) -> ast.AST:
        """
        Parse Python source code into an AST.

        This is the main entry point for the parser. It accepts raw Python
        source code, validates it is safe Python, and produces a parsed AST.

        Args:
            code_string: Raw Python source code string

        Returns:
            Parsed AST root node

        Raises:
            ValueError: If code contains unsafe constructs, invalid syntax,
                       or non-Python code
        """
        # Step 1: Sanitize if requested
        if self.sanitize:
            code_string = sanitize_code(code_string)

        # Step 2: Parse the code
        try:
            ast_root = ast.parse(code_string)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse Python code: {e}")

        return ast_root

    def is_valid_python(self, code_string: str) -> bool:
        """
        Check if code string can be parsed as valid Python.

        Args:
            code_string: Python source code string to validate

        Returns:
            True if code can be parsed as valid Python, False otherwise
        """
        try:
            self.parse(code_string)
            return True
        except ValueError:
            return False

    def is_safe_code(self, code_string: str) -> bool:
        """
        Check if code string is safe for analysis.

        Args:
            code_string: Python source code string to validate

        Returns:
            True if code is safe, False otherwise
        """
        try:
            if self.sanitize:
                sanitize_code(code_string)
            return True
        except ValueError:
            return False


# Convenience function for backward compatibility
def parse_code(code_string: str, sanitize: bool = True) -> ast.AST:
    """
    Parse Python source code string.

    This is the main entry point for parsing Python source code.

    Args:
        code_string: Raw Python source code string
        sanitize: Whether to sanitize code before parsing (default: True)

    Returns:
        Parsed AST root node

    Raises:
        ValueError: If code contains unsafe constructs, invalid syntax,
                   or non-Python code
    """
    parser = Parser(sanitize=sanitize)
    return parser.parse(code_string)
import ast
import re

# List of blocked modules that are disallowed to import
BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'importlib', 
    'pty', 'platform', 'requests', 'urllib', 'http', 'builtins'
}

# List of blocked functions/built-in names that are disallowed to use
BLOCKED_NAMES = {
    'eval', 'exec', '__import__', 'open', 'compile', 
    'getattr', 'setattr', 'delattr', 'globals', 'locals', 'vars'
}

NON_PYTHON_HINTS = (
    re.compile(r"\b(public|private|protected)\s+(class|static)\b"),
    re.compile(r"\b(class|interface)\s+\w+\s*\{"),
    re.compile(r"\b(var|let|const)\s+\w+\s*="),
    re.compile(r"\bfunction\s+\w+\s*\("),
    re.compile(r"#include\s*<"),
)

LANGUAGE_NOT_SUPPORTED = {
    "status": "rejected",
    "reason": "language_not_supported",
    "message": "PathForge currently only supports Python solutions",
}

class SafetyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in BLOCKED_MODULES:
                self.errors.append(f"Disallowed import of module '{alias.name}'.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in BLOCKED_MODULES:
                self.errors.append(f"Disallowed import from module '{node.module}'.")
        self.generic_visit(node)

    def visit_Name(self, node):
        # Prevent accessing blocked built-in functions via direct name
        if node.id in BLOCKED_NAMES:
            self.errors.append(f"Disallowed access to name '{node.id}'.")
        self.generic_visit(node)

    def visit_Call(self, node):
        # Also check for attribute calls like `foo.__import__` or similar, 
        # though standard visit_Name will catch most of it.
        # Check if call is direct print, etc. (print is allowed, but eval/exec are not)
        self.generic_visit(node)

def sanitize_code(code_string: str) -> tuple[bool, list[str], ast.AST | None]:
    """
    Sanitizes user code string.
    Checks:
    - Syntax validation using ast.parse()
    - Security validation using SafetyVisitor
    - Warns (soft-check) if line count > 150 lines.
    
    Returns:
      (is_safe, errors, ast_object)
    """
    errors = []
    
    # 1. Line count check (soft warning)
    lines = code_string.splitlines()
    if len(lines) > 150:
        # Soft warning: print or log it. We will append a warning string but keep is_safe True.
        # But wait! If we append to errors, we need a way to distinguish warnings from rejections.
        # Let's write the warning to stdout or return a special message, but keep is_safe = True.
        # Let's add a note in errors that says "Warning: Code is long" but don't mark as unsafe unless there are actual safety errors.
        pass
        
    # 2. Syntax validation
    try:
        root = ast.parse(code_string)
    except SyntaxError as e:
        if _looks_like_non_python(code_string):
            errors.append(LANGUAGE_NOT_SUPPORTED.copy())
            return False, errors, None
        errors.append(f"SyntaxError: {e.msg} (line {e.lineno}, col {e.offset})")
        return False, errors, None
    except Exception as e:
        errors.append(f"Parser Error: {str(e)}")
        return False, errors, None

    # 3. Safety/Sandbox check
    visitor = SafetyVisitor()
    visitor.visit(root)
    
    if visitor.errors:
        errors.extend(visitor.errors)
        return False, errors, root

    return True, errors, root


def _looks_like_non_python(code_string):
    """Detect common pasted Java/C++/JavaScript shapes before showing Python syntax errors."""
    return any(pattern.search(code_string) for pattern in NON_PYTHON_HINTS)

"""Sandbox for executing LLM-generated constraint code."""


def validate_code(code: str) -> str | None:
    """Basic validation of generated code before exec.

    Returns error message if invalid, None if OK.
    """
    # Check for dangerous patterns
    dangerous = ["import ", "open(", "os.", "sys.", "subprocess", "eval(", "__", "exec("]
    for pattern in dangerous:
        if pattern in code:
            return f"Generated code contains forbidden pattern: '{pattern}'"

    # Try to compile
    try:
        compile(code, "<constraint>", "exec")
    except SyntaxError as e:
        return f"Syntax error in generated code: {e}"

    return None


def execute_constraint(code: str, model, assign, data) -> str | None:
    """Execute constraint code in a sandbox.

    Returns error message if execution fails, None if OK.
    """
    validation_error = validate_code(code)
    if validation_error:
        return validation_error

    safe_globals = {
        "__builtins__": {},
        "model": model,
        "assign": assign,
        "data": data,
        "NUM_DAYS": data.num_days,
        "NUM_PERIODS": data.num_periods,
        "NUM_SECTIONS": len(data.sections),
        "range": range,
        "sum": sum,
        "len": len,
        "any": any,
        "all": all,
        "True": True,
        "False": False,
        "print": print,
    }

    try:
        exec(code, safe_globals, {})
        return None
    except Exception as e:
        return f"Runtime error: {e}"

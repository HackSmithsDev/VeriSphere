def safe_spreadsheet_value(value: object) -> object:
    if isinstance(value, str):
        first_visible = value.lstrip(" \t\r\n")
        if first_visible.startswith(("=", "+", "-", "@")):
            return f"'{value}"
    return value

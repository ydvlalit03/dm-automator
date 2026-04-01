import re


def matches(comment_text: str, keyword: str) -> bool:
    """Case-insensitive whole-word keyword match in comment text."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return bool(re.search(pattern, comment_text, re.IGNORECASE))

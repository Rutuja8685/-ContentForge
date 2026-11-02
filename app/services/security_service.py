"""Security service – placeholder; fully implemented in Phase 6 & 7."""
import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+now",
    r"act\s+as\s+(if\s+)?",
    r"<<<|>>>",           # delimiter smuggling
    r"\[INST\]|\[/INST\]",
    r"<\|im_start\|>|<\|im_end\|>",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan_for_injection(text: str) -> list[str]:
    """Return list of matched injection patterns (empty = clean)."""
    return [p.pattern for p in _COMPILED if p.search(text)]


def wrap_source(text: str) -> str:
    """Wrap source content in delimiters to prevent prompt injection."""
    return f"<<<SOURCE_START>>>\n{text}\n<<<SOURCE_END>>>"

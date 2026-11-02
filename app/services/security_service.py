"""Prompt-injection warnings and source-delimiter neutralization."""

import re

INJECTION_PATTERNS = [
    ("Ignore-previous-instructions language", r"ignore\s+(all\s+)?previous\s+instructions"),
    ("Disregard-instructions language", r"disregard\s+(all\s+)?(prior|previous)\s+instructions"),
    ("System-prompt reference", r"system\s+prompt"),
    ("Persona override language", r"you\s+are\s+now"),
    ("Role-play override language", r"(roleplay|role-play)\s+as\b"),
    ("Act-as override language", r"\bact\s+as\s+(if\s+)?"),
    ("Prompt delimiter pattern", r"<<<|>>>"),
    ("Instruction-token pattern", r"\[INST\]|\[/INST\]"),
    ("Chat-role token pattern", r"<\|im_start\|>|<\|im_end\|>"),
]

_COMPILED = [
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in INJECTION_PATTERNS
]
SOURCE_END_PATTERN = re.compile(r"</\s*source\s*>", re.IGNORECASE)


def scan_for_injection(text: str) -> list[str]:
    """Return user-readable warnings for suspicious instruction-like text."""
    warnings = [
        f"Potential prompt injection detected: {label}."
        for label, pattern in _COMPILED
        if pattern.search(text)
    ]
    if SOURCE_END_PATTERN.search(text):
        warnings.append(
            "A literal source-closing delimiter was neutralized in the text."
        )
    return warnings


def neutralize_source_delimiters(text: str) -> str:
    """Escape source-closing delimiters while preserving their visible text."""
    return SOURCE_END_PATTERN.sub("&lt;/source&gt;", text)


def wrap_source(text: str) -> str:
    """Wrap source content using delimiters without allowing delimiter closure."""
    safe_text = neutralize_source_delimiters(text)
    return f"<source>\n{safe_text}\n</source>"

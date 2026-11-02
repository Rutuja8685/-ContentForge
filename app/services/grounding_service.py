"""Grounding service – placeholder; fully implemented in Phase 7."""


async def check_grounding(source_text: str, generated_content: dict) -> dict:
    """
    Run a second LLM pass to score source fidelity.
    Returns {"score": float, "flagged_claims": list[str]}.
    Implemented in Phase 7.
    """
    raise NotImplementedError("Grounding check implemented in Phase 7")

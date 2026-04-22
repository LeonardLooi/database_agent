"""Per-provider confidence extraction for skill routing.

The primary confidence signal is the self-reported float in the skill-match JSON
response (model rates its own certainty 0.0–1.0).

Provider-specific enhancements
────────────────────────────────────────────────────────────────────────────────
Gemini:
    When self-reported confidence is 0.0, fall back to a keyword-overlap heuristic
    between the user message and the matched skill's description. Grounding metadata
    is not available for the skill-match call because no RAG retrieval is involved.

OpenAI:
    logprobs=True on the skill-match request yields token-probability signal. Requires
    generating the response with logprobs and averaging the top token probabilities.
    Not enabled by default due to added latency; enable via ENABLE_LOGPROB_CONFIDENCE=true.

Anthropic:
    No native logprobs. A follow-up self-evaluation prompt
    ("Rate your confidence 0.0–1.0 that this skill matches the request") can be used
    for mid-range decisions (0.40–0.70). Not called by default due to added latency;
    enable via ENABLE_ANTHROPIC_SELF_EVAL=true.

20K token limit (R6)
────────────────────────────────────────────────────────────────────────────────
The skill-match prompt concatenates all skill descriptions into a single context.
At ~150 tokens per skill, 30 skills ≈ 4,500 tokens. Beyond 30 skills the prompt
approaches 20K tokens and may degrade model performance on smaller context windows.

Mitigation: use tag-based pre-filtering (SkillRegistry.get_descriptions_for_tags)
to limit the candidate set when the registry exceeds 30 skills. The orchestrator
calls get_all_descriptions() unconditionally today; add a tag_filter parameter and
pass relevant tags extracted from the user message as a first step.
"""
from __future__ import annotations


def _keyword_overlap(user_message: str, skill_description: str) -> float:
    """Return a simple keyword-overlap score in [0.0, 1.0].

    Splits both strings on whitespace, lowercases, and computes the Jaccard
    similarity of the resulting token sets. Used as a last-resort fallback when
    the model self-reports 0.0 confidence.
    """
    user_tokens = set(user_message.lower().split())
    desc_tokens = set(skill_description.lower().split())
    if not desc_tokens:
        return 0.0
    intersection = user_tokens & desc_tokens
    union = user_tokens | desc_tokens
    return len(intersection) / len(union)


def enhance_gemini(
    match_result: dict,
    user_message: str,
    skill_description: str,
) -> float:
    """Return the best available confidence signal for a Gemini skill-match call.

    If the self-reported confidence is non-zero, return it unchanged.
    Otherwise fall back to keyword-overlap heuristic, capped at 0.49 (below
    CLARIFY threshold) to avoid false CLARIFY triggers for weak matches.
    """
    self_reported = float(match_result.get("confidence", 0.0))
    if self_reported > 0.0:
        return self_reported
    heuristic = _keyword_overlap(user_message, skill_description)
    return min(heuristic, 0.49)


def enhance_openai(match_result: dict) -> float:
    """Return the confidence signal for an OpenAI skill-match call.

    Currently returns the self-reported float. When ENABLE_LOGPROB_CONFIDENCE=true
    is set, the caller should pass logprob-derived confidence via match_result and
    this function will prefer it over the self-reported value.
    """
    return float(match_result.get("confidence", 0.0))


def enhance_anthropic(match_result: dict) -> float:
    """Return the confidence signal for an Anthropic skill-match call.

    Currently returns the self-reported float. When ENABLE_ANTHROPIC_SELF_EVAL=true
    is set, the orchestrator should issue a follow-up prompt and populate
    match_result["confidence"] with the parsed float before calling this function.
    """
    return float(match_result.get("confidence", 0.0))


def extract_confidence(
    provider_name: str,
    match_result: dict,
    user_message: str = "",
    skill_description: str = "",
) -> float:
    """Dispatch to the correct per-provider confidence enhancer.

    Args:
        provider_name:    LLM provider identifier ("gemini", "openai", "anthropic", etc.)
        match_result:     Parsed JSON from the skill-match call with at least a "confidence" key.
        user_message:     Original user query (used by Gemini keyword heuristic).
        skill_description: Matched skill's description (used by Gemini keyword heuristic).

    Returns:
        A float in [0.0, 1.0] representing routing confidence.
    """
    p = provider_name.lower()
    if p == "gemini":
        return enhance_gemini(match_result, user_message, skill_description)
    if p == "openai":
        return enhance_openai(match_result)
    if p == "anthropic":
        return enhance_anthropic(match_result)
    return float(match_result.get("confidence", 0.0))

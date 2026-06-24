"""
AI-related functions for transcript analysis with enhanced precision and virality scoring.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
import asyncio
import logging
import re

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from .config import Config, get_config
from .runtime_settings import apply_settings_to_process_env

logger = logging.getLogger(__name__)

IDEAL_CLIP_MIN_SECONDS = 25
IDEAL_CLIP_MAX_SECONDS = 50
MIN_ACCEPTED_CLIP_SECONDS = 15
MAX_ACCEPTED_CLIP_SECONDS = 60
TRANSCRIPT_ANALYSIS_CACHE_VERSION = "thih-scoring-v1"
SUPPORTED_CONTENT_MODES = (
    "sermon",
    "devotional",
    "podcast",
    "teaching",
    "testimony",
    "thih_systems",
    "business_thought_leadership",
)
ContentMode = Literal[
    "sermon",
    "devotional",
    "podcast",
    "teaching",
    "testimony",
    "thih_systems",
    "business_thought_leadership",
]
DEFAULT_CONTENT_MODE: ContentMode = "thih_systems"

TRANSCRIPT_SPAN_RE = re.compile(
    r"^\[(?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?P<text>.*)$"
)


class ViralityAnalysis(BaseModel):
    """Detailed virality breakdown for a segment."""

    hook_score: int = Field(
        default=15,
        description="How strong is the opening hook (0-25)",
        ge=0,
        le=25,
    )
    engagement_score: int = Field(
        default=15,
        description="How engaging/entertaining is the content (0-25)",
        ge=0,
        le=25,
    )
    value_score: int = Field(
        default=15,
        description="Educational/informational value (0-25)",
        ge=0,
        le=25,
    )
    shareability_score: int = Field(
        default=15,
        description="Likelihood of being shared (0-25)",
        ge=0,
        le=25,
    )
    total_score: int = Field(
        default=60,
        description="Combined virality score (0-100)",
        ge=0,
        le=100,
    )
    hook_type: Optional[
        Literal["question", "statement", "statistic", "story", "contrast", "none"]
    ] = Field(
        default="none",
        description="Type of hook: question, statement, statistic, story, contrast, or none",
    )
    virality_reasoning: str = Field(
        default="The model did not provide a detailed virality breakdown.",
        description="Explanation of the virality score",
    )



def _default_virality_analysis() -> ViralityAnalysis:
    return ViralityAnalysis()


class THIHAnalysis(BaseModel):
    """THIH-specific clip quality breakdown."""

    opening_clarity: int = Field(default=8, ge=0, le=10)
    retention_strength: int = Field(default=8, ge=0, le=10)
    service_value: int = Field(default=8, ge=0, le=10)
    stewardship_usefulness: int = Field(default=8, ge=0, le=10)
    canon_fit: int = Field(default=8, ge=0, le=10)
    conviction: int = Field(default=8, ge=0, le=10)
    platform_readiness: int = Field(default=8, ge=0, le=10)
    message_integrity: int = Field(default=8, ge=0, le=10)
    total_score: int = Field(default=64, ge=0, le=80)
    reasoning: str = Field(
        default="The model did not provide a detailed THIH scoring breakdown."
    )

    @model_validator(mode="after")
    def _calculate_total_score(self) -> "THIHAnalysis":
        self.total_score = (
            self.opening_clarity
            + self.retention_strength
            + self.service_value
            + self.stewardship_usefulness
            + self.canon_fit
            + self.conviction
            + self.platform_readiness
            + self.message_integrity
        )
        return self


class TranscriptSegment(BaseModel):
    """Represents a relevant segment of transcript with precise timing and virality analysis."""

    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    text: str = Field(
        validation_alias=AliasChoices("text", "segment"),
        description=(
            "Transcript text taken only from the selected timestamp range. "
            "Keep it verbatim or near-verbatim, and do not paraphrase or merge non-contiguous lines."
        )
    )
    relevance_score: float = Field(
        default=0.75,
        description="Relevance score from 0.0 to 1.0", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        default="Selected by the AI model as a clip candidate.",
        description=(
            "Brief factual explanation of why this exact segment works as a clip. "
            "Base it only on the provided transcript content."
        )
    )
    virality: ViralityAnalysis = Field(
        default_factory=_default_virality_analysis,
        description="Detailed virality score breakdown",
    )
    thih: THIHAnalysis = Field(
        default_factory=THIHAnalysis,
        validation_alias=AliasChoices("thih", "thih_analysis", "thih_scoring"),
        description="THIH-specific score breakdown; primary selection signal.",
    )
    content_mode: ContentMode = Field(
        default=DEFAULT_CONTENT_MODE,
        description="Content mode used to calibrate THIH scoring.",
    )
    recommended_title: Optional[str] = Field(
        default=None, description="Recommended short-form clip title."
    )
    recommended_caption: Optional[str] = Field(
        default=None, description="Recommended social caption."
    )
    recommended_cta: Optional[str] = Field(
        default=None, description="Recommended call to action."
    )
    recommended_hashtags: List[str] = Field(
        default_factory=list, description="Recommended social hashtags."
    )
    platform_fit: List[str] = Field(
        default_factory=lambda: ["shorts", "reels", "tiktok"],
        description="Best platform surfaces for this clip.",
    )
    scripture_reference: Optional[str] = Field(
        default=None, description="Scripture reference when directly applicable."
    )
    content_warning: Optional[str] = Field(
        default=None, description="Content warning when directly applicable."
    )
    @field_validator("recommended_hashtags", mode="before")
    @classmethod
    def _coerce_hashtags(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if isinstance(value, list):
            return [
                tag if str(tag).startswith("#") else f"#{str(tag).strip()}"
                for tag in value
                if str(tag).strip()
            ]
        return value

    @field_validator("platform_fit", mode="before")
    @classmethod
    def _coerce_platform_fit(cls, value: Any) -> Any:
        if value is None:
            return ["shorts", "reels", "tiktok"]
        if isinstance(value, str):
            return [part.strip().lower() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def _fill_recommendation_defaults(self) -> "TranscriptSegment":
        fallback_text = self.text.strip()
        short_text = fallback_text[:77].rstrip() + "..." if len(fallback_text) > 80 else fallback_text
        if not self.recommended_title:
            self.recommended_title = short_text or "THIH Clip Engine Moment"
        if not self.recommended_caption:
            self.recommended_caption = short_text or "The hustle is holy when the work is stewarded well."
        if not self.recommended_cta:
            self.recommended_cta = "Reflect, save, and steward the next step well."
        if not self.recommended_hashtags:
            self.recommended_hashtags = ["#THIH", "#TheHustleIsHoly", "#ClipEngine"]
        if not self.platform_fit:
            self.platform_fit = ["shorts", "reels", "tiktok"]
        return self
    @field_validator("relevance_score", mode="before")
    @classmethod
    def _coerce_percent_relevance_score(cls, value: Any) -> Any:
        if value is None:
            return value
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return value
        if numeric_value > 1 and numeric_value <= 100:
            return numeric_value / 100
        return value


class BRollOpportunity(BaseModel):
    """Identifies an opportunity to insert B-roll footage."""

    timestamp: str = Field(
        default="00:00",
        validation_alias=AliasChoices("timestamp", "segment_start_time", "start_time"),
        description="When to insert B-roll (MM:SS format)",
    )
    duration: float = Field(
        default=3.0,
        description="How long to show B-roll (2-5 seconds)",
        ge=2.0,
        le=5.0,
    )
    search_term: str = Field(
        default="related visual",
        validation_alias=AliasChoices("search_term", "broll", "visual", "query"),
        description="Keyword to search for B-roll footage",
    )
    context: str = Field(
        default="Suggested B-roll opportunity from the model.",
        validation_alias=AliasChoices("context", "description"),
        description="What's being discussed at this point",
    )

    @field_validator("search_term", "context", mode="before")
    @classmethod
    def _coerce_textish_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item is not None)
        return str(value)


class TranscriptAnalysis(BaseModel):
    """Analysis result for transcript segments with virality and B-roll opportunities."""

    most_relevant_segments: List[TranscriptSegment]
    summary: str = Field(description="Brief summary of the video content")
    key_topics: List[str] = Field(description="List of main topics discussed")
    broll_opportunities: Optional[List[BRollOpportunity]] = Field(
        default=None, description="Opportunities to insert B-roll footage"
    )


# Enhanced system prompt with virality scoring and B-roll detection
transcript_analysis_system_prompt = """You are an expert transcript analyst for short-form video editing.

Your job is extraction and ranking, not creative rewriting. You must stay fully grounded in the transcript and choose the best clip candidates that already exist in the source material.

OUTPUT CONTRACT:
- Return valid JSON only. Do not output Markdown, headings, bullets, prose, code fences, explanations, or commentary outside the JSON object.
- The top-level JSON object must include: "most_relevant_segments", "summary", and "key_topics".
- Only include "broll_opportunities" when B-roll was requested.
- Each item in "most_relevant_segments" must include: "start_time", "end_time", "text", "relevance_score", "reasoning", "content_mode", "thih", "virality", "recommended_title", "recommended_caption", "recommended_cta", "recommended_hashtags", and "platform_fit".
- Do not use "segment" as an output field. Use "text".
- "thih" must include: "opening_clarity", "retention_strength", "service_value", "stewardship_usefulness", "canon_fit", "conviction", "platform_readiness", "message_integrity", "total_score", and "reasoning".
- "virality" must include: "hook_score", "engagement_score", "value_score", "shareability_score", "total_score", "hook_type", and "virality_reasoning".
- Include "scripture_reference" when a direct scripture reference is present or clearly applicable; otherwise use null.
- Include "content_warning" only when the selected clip warrants one; otherwise use null.
- Every returned segment must be 15-60 seconds long. Prefer 25-50 seconds.

CORE OBJECTIVES:
1. Identify segments that would be compelling on social media platforms
2. Focus on complete thoughts, insights, or entertaining moments
3. Prioritize content with hooks, emotional moments, or valuable information
4. Each segment should be engaging and worth watching
5. Score each segment by THIH standards first and viral potential second

GROUNDING RULES:
1. Use only the provided transcript lines and timestamps
2. Never invent facts, tone, context, or transitions that are not present
3. Treat this as span selection over a timestamped transcript, not open-ended summarization
4. Each selected segment must map to one contiguous range in the transcript
5. segment.text must match the chosen span closely and must not include content from outside the chosen range
6. Do not stitch together distant moments into one clip
7. If a speaker label appears, use it only if it is part of the spoken content and helps clarity

CONTENT NEUTRALITY RULES:
1. This is clipping software for legitimate editing workflows
2. Do not judge, moralize, or downgrade a segment just because the topic is controversial, sensitive, adult, political, criminal, medical, or otherwise intense
3. Evaluate segments only on clip quality: clarity, self-contained value, hook strength, emotional impact, specificity, and shareability
4. Do not refuse analysis just because the speaker describes risky, offensive, or uncomfortable subject matter
5. Only downgrade a segment when the transcript itself is weak, confusing, repetitive, unusable, or a poor standalone clip

SEGMENT SELECTION CRITERIA:
1. STRONG HOOKS: Attention-grabbing opening lines
2. VALUABLE CONTENT: Tips, insights, interesting facts, stories
3. EMOTIONAL MOMENTS: Excitement, surprise, humor, inspiration
4. COMPLETE THOUGHTS: Self-contained ideas that make sense alone
5. ENTERTAINING: Content people would want to share
6. HIGH SIGNAL: Prefer specific, concrete language over vague discussion
7. LOW FILLER: Avoid greetings, sponsor reads, repeated setup, throat-clearing, and housekeeping unless they are unusually compelling

WHAT A GOOD CLIP FEELS LIKE:
- A viewer should understand and care without the original title, thumbnail, or previous context
- Prefer a complete mini-story or argument: setup, tension or claim, specific detail, and payoff
- Expand a great short moment to nearby contiguous lines when that adds needed setup, stakes, or payoff
- Strong picks include contrarian claims, mistakes or lessons, concrete examples, before/after moments, frameworks, surprising results, emotionally charged reactions, and complete answers to interesting questions
- Bad picks include intros, sponsor or CTA sections, vague setup, contextless quote fragments, repeated points, definitions without payoff, meandering background, and answer fragments that require unseen context

VIRALITY SCORING (0-100 total, from four 0-25 subscores):
For each segment, provide a detailed virality breakdown:

1. HOOK STRENGTH (0-25):
   - 20-25: Immediately grabs attention (surprising fact, bold claim, intriguing question)
   - 15-19: Good opener that creates curiosity
   - 10-14: Decent start but could be stronger
   - 0-9: Weak or no hook

2. ENGAGEMENT (0-25):
   - 20-25: Highly entertaining, emotional, or dramatic
   - 15-19: Interesting and holds attention
   - 10-14: Moderately engaging
   - 0-9: Flat or boring delivery

3. VALUE (0-25):
   - 20-25: Actionable insights, unique knowledge, or transformative ideas
   - 15-19: Useful information most people don't know
   - 10-14: Somewhat informative
   - 0-9: Common knowledge or filler content

4. SHAREABILITY (0-25):
   - 20-25: "I need to send this to someone" content
   - 15-19: Content worth bookmarking
   - 10-14: Nice but not share-worthy
   - 0-9: Generic content

HOOK TYPES to identify:
- "question": Opens with a question that creates curiosity
- "statement": Bold claim or surprising statement
- "statistic": Uses compelling numbers or data
- "story": Starts with narrative/anecdote
- "contrast": Before/after or problem/solution framing
- "none": No clear hook pattern


THIH SCORING (0-80 total, from eight 0-10 subscores):
THIH scoring is the governing ranking signal. Virality is secondary and should never override message integrity, service value, or canon fit.

1. opening_clarity: Whether the first seconds make the idea immediately understandable.
2. retention_strength: Whether the clip sustains attention through tension, payoff, specificity, or emotional momentum.
3. service_value: Whether the clip serves the viewer with truth, usefulness, encouragement, conviction, or practical help.
4. stewardship_usefulness: Whether the clip helps the viewer steward work, faith, attention, resources, relationships, or calling well.
5. canon_fit: Whether the clip fits the stated content mode and, for faith content, respects biblical/theological context.
6. conviction: Whether the clip carries a clear, grounded point of view without hype or manipulation.
7. platform_readiness: Whether the clip can stand alone on short-form platforms with clean boundaries and usable pacing.
8. message_integrity: Whether the selected span preserves the speaker's meaning without distortion or missing context.

Recommended metadata:
- recommended_title should be concise, specific, and grounded in the selected span.
- recommended_caption should be platform-ready and preserve the source message.
- recommended_cta should invite reflection, saving, sharing, or a faithful next step without manipulative language.
- recommended_hashtags should include 3-6 relevant hashtags.
- platform_fit should list any of: shorts, reels, tiktok, linkedin, podcast_clip, youtube.
- scripture_reference should be a direct reference only when present or clearly applicable.
- content_warning should be short and only used when the clip includes sensitive material.
B-ROLL OPPORTUNITIES:
Identify 2-4 moments in each segment where B-roll footage could enhance the video:
- When specific objects, places, or concepts are mentioned
- During explanations that could benefit from visual illustration
- At emotional peaks that could use supporting imagery
- Use simple, searchable keywords (e.g., "coffee shop", "laptop coding", "money stack")

TIMING GUIDELINES:
- Target 25-50 seconds for most clips
- Use 15-24 seconds only when the moment is exceptionally dense, self-contained, and complete
- CRITICAL: start_time MUST be different from end_time (minimum 15 seconds apart)
- Focus on natural content boundaries rather than arbitrary time limits
- Include enough context for the segment to be understandable
- Prefer roughly 30-50 seconds when possible
- Start at the hook or the minimum setup needed to make the hook land, and end after the payoff
- If a highlight is only one good line, expand to include the surrounding setup and payoff rather than returning a tiny fragment
- Stop expanding when the topic drifts, the speaker repeats the same point, or the clip loses momentum

TIMESTAMP REQUIREMENTS - EXTREMELY IMPORTANT:
- Use EXACT timestamps as they appear in the transcript
- Never modify timestamp format (keep MM:SS structure)
- start_time MUST be LESS THAN end_time (start_time < end_time)
- MINIMUM segment duration: 15 seconds (end_time - start_time >= 15 seconds)
- IDEAL segment duration: 25-50 seconds
- Look at transcript ranges like [02:25 - 02:35] and use different start/end times
- NEVER use the same timestamp for both start_time and end_time
- Example: start_time: "02:25", end_time: "02:35" (NOT "02:25" and "02:25")

SCORING AND OUTPUT RULES:
- relevance_score should reflect how well the segment works as a standalone short clip, not just whether the topic is generally important
- Penalize clips that are only quotable but not self-contained, too generic, missing setup, missing payoff, or padded with filler
- virality_reasoning and reasoning should cite what is actually present in the chosen span
- summary and key_topics must also stay grounded in the transcript and should not add outside interpretation

Find 2-5 compelling, distinct clips from different parts of the sermon/video that would work well as standalone clips. Quality over quantity: choose fewer stronger segments over filling a quota, and never repeat the same opening window or overlapping moment. Every selected segment must be accurate, self-contained, have proper time ranges, score high on THIH metrics, and use virality as a secondary signal."""

# Lazy-loaded agent to avoid import-time failures when API keys aren't set
_transcript_agent_cache: dict[tuple[str | None, ...], Agent[None, TranscriptAnalysis]] = {}

SUPPORTED_LLM_PROVIDERS = {"google", "google-gla", "openai", "anthropic", "ollama"}
SECRET_REDACTION_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]+|api[_-]?key\s*[:=]\s*[^\s,;]+|token\s*[:=]\s*[^\s,;]+|bearer\s+[^\s,;]+)"
)
REQUEST_DETAIL_RE = re.compile(r"(?i)\b(request body|payload|messages|prompt)\b.*")
STATUS_CODE_RE = re.compile(r"\b([45]\d{2})\b")
RETRYABLE_ERROR_TERMS = (
    "overload",
    "rate limit",
    "timeout",
    "temporarily unavailable",
    "unavailable",
    "try again",
    "429",
    "500",
    "502",
    "503",
    "504",
)


class AIAnalysisFailure(RuntimeError):
    """Sanitized AI analysis failure safe to persist on tasks."""


def _sanitize_provider_error(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    message = SECRET_REDACTION_RE.sub("[redacted]", message)
    message = REQUEST_DETAIL_RE.sub("request details redacted", message)
    message = " ".join(message.split())
    return message[:220] or "provider error"


def _extract_provider_status_code(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    if status_code is None and getattr(error, "response", None) is not None:
        status_code = getattr(error.response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    match = STATUS_CODE_RE.search(str(error))
    return int(match.group(1)) if match else None


def _is_retryable_provider_error(error: Exception) -> bool:
    status_code = _extract_provider_status_code(error)
    if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
        return True
    sanitized = _sanitize_provider_error(error).lower()
    return any(term in sanitized for term in RETRYABLE_ERROR_TERMS)


def _format_provider_reason(llm_name: str, error: Exception) -> str:
    status_code = _extract_provider_status_code(error)
    reason = _sanitize_provider_error(error)
    if status_code is not None:
        return f"{llm_name} returned status {status_code}: {reason}"
    return f"{llm_name} failed: {reason}"


def _build_ai_analysis_failure_message(
    attempted_models: list[str],
    failures: list[tuple[str, Exception]],
) -> str:
    primary = attempted_models[0] if attempted_models else "not configured"
    fallback_attempts = attempted_models[1:]
    final_model, final_error = failures[-1] if failures else (primary, RuntimeError("unknown provider failure"))
    fallback_text = ", ".join(fallback_attempts) if fallback_attempts else "none configured or usable"
    return (
        "AI analysis failed. "
        f"Primary LLM: {primary}. "
        f"Fallbacks attempted: {fallback_text}. "
        f"Final provider reason: {_format_provider_reason(final_model, final_error)}. "
        "Next action: check LLM provider availability, quotas, API keys, and LLM_FALLBACKS; then resume the task."
    )

def _normalize_content_mode(content_mode: ContentMode | str | None) -> ContentMode:
    if not content_mode:
        return DEFAULT_CONTENT_MODE
    normalized = str(content_mode).strip().lower()
    if normalized in SUPPORTED_CONTENT_MODES:
        return normalized  # type: ignore[return-value]
    return DEFAULT_CONTENT_MODE


def _split_llm_name(model_name: str) -> tuple[str, str | None]:
    if ":" not in model_name:
        return model_name.strip().lower(), None

    provider, provider_model_name = model_name.split(":", 1)
    return provider.strip().lower(), provider_model_name.strip() or None


def _get_missing_llm_key_error(model_name: str, runtime_config: Config) -> Optional[str]:
    """Return a clear configuration error when the selected LLM key is missing."""
    provider, provider_model_name = _split_llm_name(model_name)

    if provider not in SUPPORTED_LLM_PROVIDERS:
        return (
            f"Unsupported LLM provider '{provider}'. "
            "Use google-gla:*, openai:*, anthropic:*, or ollama:*."
        )

    if not provider_model_name:
        return (
            "Selected LLM is missing a model name. "
            "Use the format provider:model, for example ollama:gpt-oss:20b."
        )

    if provider in {"google", "google-gla"} and not runtime_config.google_api_key:
        return (
            "Selected LLM provider is Google, but GOOGLE_API_KEY is not set. "
            "Set GOOGLE_API_KEY or set LLM to openai:* / anthropic:* / ollama:* with the matching API key."
        )

    if provider == "openai" and not runtime_config.openai_api_key:
        return (
            "Selected LLM provider is OpenAI, but OPENAI_API_KEY is not set. "
            "Set OPENAI_API_KEY or choose another provider with a matching API key."
        )

    if provider == "anthropic" and not runtime_config.anthropic_api_key:
        return (
            "Selected LLM provider is Anthropic, but ANTHROPIC_API_KEY is not set. "
            "Set ANTHROPIC_API_KEY or choose another provider with a matching API key."
        )

    if provider == "ollama":
        # Ollama can run locally without an API key. OLLAMA_BASE_URL/OLLAMA_API_KEY
        # are optional and passed through as environment variables.
        return None

    return None


def _build_transcript_model(runtime_config: Config, llm_name: str | None = None) -> Model | str:
    selected_llm = llm_name or runtime_config.llm
    provider, provider_model_name = _split_llm_name(selected_llm)
    if provider != "ollama":
        return selected_llm

    if not provider_model_name:
        raise RuntimeError(
            "Selected LLM provider is Ollama, but no model name was provided. "
            "Use the format ollama:<model>, for example ollama:gpt-oss:20b."
        )

    return OllamaModel(
        provider_model_name,
        provider=OllamaProvider(
            base_url=runtime_config.resolve_ollama_base_url(),
            api_key=runtime_config.ollama_api_key,
        ),
    )


def _get_llm_candidate_names(runtime_config: Config) -> list[str]:
    """Return primary LLM followed by configured fallback LLMs, de-duplicated."""
    candidates = [runtime_config.llm]
    candidates.extend(getattr(runtime_config, "llm_fallbacks", []) or [])

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(normalized)
    return unique_candidates


def _transcript_agent_signature(
    runtime_config: Config,
    llm_name: str,
) -> tuple[str | None, ...]:
    return (
        llm_name,
        runtime_config.openai_api_key,
        runtime_config.google_api_key,
        runtime_config.anthropic_api_key,
        runtime_config.ollama_base_url,
        runtime_config.ollama_api_key,
    )


def _get_or_create_transcript_agent(
    runtime_config: Config,
    llm_name: str,
) -> Agent[None, TranscriptAnalysis]:
    provider, _ = _split_llm_name(llm_name)
    signature = _transcript_agent_signature(runtime_config, llm_name)
    cached_agent = _transcript_agent_cache.get(signature)
    if cached_agent is not None:
        return cached_agent

    config_error = _get_missing_llm_key_error(llm_name, runtime_config)
    if config_error:
        raise RuntimeError(config_error)

    agent = Agent[None, TranscriptAnalysis](
        model=_build_transcript_model(runtime_config, llm_name),
        output_type=TranscriptAnalysis,
        system_prompt=transcript_analysis_system_prompt,
        output_retries=2 if provider == "ollama" else 2,
    )
    _transcript_agent_cache[signature] = agent
    return agent


def get_transcript_agent_candidates() -> list[tuple[str, Agent[None, TranscriptAnalysis]]]:
    """Build usable transcript-analysis agents in primary/fallback order."""
    runtime_config = get_config()
    apply_settings_to_process_env(runtime_config.as_runtime_settings())

    agents: list[tuple[str, Agent[None, TranscriptAnalysis]]] = []
    config_errors: list[str] = []
    for attempt_number, llm_name in enumerate(_get_llm_candidate_names(runtime_config), start=1):
        config_error = _get_missing_llm_key_error(llm_name, runtime_config)
        if config_error:
            config_errors.append(config_error)
            logger.warning(
                "LLM candidate skipped: model=%s attempt=%s reason=%s",
                llm_name,
                attempt_number,
                config_error,
            )
            continue
        agents.append((llm_name, _get_or_create_transcript_agent(runtime_config, llm_name)))

    if not agents:
        raise RuntimeError(
            config_errors[0]
            if config_errors
            else "No usable LLM candidates are configured."
        )

    return agents


def get_transcript_agent() -> Agent[None, TranscriptAnalysis]:
    """Get the primary transcript analysis agent for backward-compatible callers."""
    return get_transcript_agent_candidates()[0][1]


def build_transcript_analysis_prompt(
    transcript: str,
    include_broll: bool = False,
    clip_signals: str | None = None,
    content_mode: ContentMode | str = DEFAULT_CONTENT_MODE,
    selection_instructions: str | None = None,
) -> str:
    """Build the grounded task prompt for transcript analysis."""
    normalized_content_mode = _normalize_content_mode(content_mode)
    supported_modes = ", ".join(SUPPORTED_CONTENT_MODES)
    broll_instruction = ""
    if include_broll:
        broll_instruction = (
            "\n5. Also identify B-roll opportunities for each chosen segment where stock footage could enhance the visual appeal."
        )
    signal_section = ""
    if clip_signals:
        signal_section = (
            "\n\nAdditional deterministic signals from transcript/audio analysis:\n"
            f"{clip_signals}\n\n"
            "Use these as hints only. They should influence ranking, but every final segment "
            "must still be a coherent contiguous transcript range."
        )
    instructions_section = ""
    if selection_instructions and selection_instructions.strip():
        instructions_section = (
            "\n\nTask-level THIH Shorts Factory selection instructions:\n"
            f"{selection_instructions.strip()}\n\n"
            "Use these instructions only when they are consistent with the transcript, "
            "message integrity, and the required JSON schema."
        )

    return f"""Analyze this video transcript and identify the most engaging segments for short-form content.

The transcript is formatted as one line per timestamped span, for example:
[00:12 - 00:21] Spoken text here
[00:21 - 00:35] More spoken text here

Content mode: {normalized_content_mode}
Supported content modes: {supported_modes}

Follow this workflow:
1. Read the transcript as a sequence of timestamped spans.
2. Select only contiguous ranges that already exist in the transcript.
3. Prefer moments with a strong hook, clear payoff, emotional charge, or concrete value.
4. For each chosen segment, use the earliest timestamp in the selected range as start_time and the latest timestamp in the selected range as end_time.{broll_instruction}

Selection target:
- Choose 2-5 segments total.
- Choose distinct clips from different parts of the sermon/video; do not repeat the same opening window, overlapping range, or substantially identical transcript moment.
- Most selected clips should be 25-50 seconds.
- Only choose a 15-24 second clip when it already contains a full setup and payoff.
- If a strong moment is shorter than 25 seconds, first try expanding to nearby contiguous transcript lines that add useful context.
- Skip weak standalone picks: intros, sponsor reads, CTAs, contextless quotes, repeated points, vague setup, and answer fragments that require prior context.
- Before returning a segment, ask whether a viewer would understand and care without seeing the rest of the source video.

Critical accuracy requirements:
- Do not fabricate or embellish content.
- Do not use timestamps that are not present in the transcript.
- Do not merge separate non-contiguous moments into one segment.
- segment.text must reflect only the spoken content inside the selected time range.
- If a span lacks enough context to stand alone, expand to nearby contiguous lines rather than guessing.
- If there is a tradeoff between "viral" and "accurate", choose accuracy.
- Do not reject or penalize a segment simply because of the subject matter; stay content-neutral and assess clip quality only.
{signal_section}
{instructions_section}

JSON-only output requirements:
- Return one valid JSON object and nothing else.
- No Markdown, headings, bullets, code fences, or explanatory text outside JSON.
- Top-level keys: "most_relevant_segments", "summary", "key_topics"{', "broll_opportunities"' if include_broll else ''}.
- Segment keys: "start_time", "end_time", "text", "relevance_score", "reasoning", "content_mode", "thih", "virality", "recommended_title", "recommended_caption", "recommended_cta", "recommended_hashtags", "platform_fit", "scripture_reference", "content_warning".
- THIH scoring keys: "opening_clarity", "retention_strength", "service_value", "stewardship_usefulness", "canon_fit", "conviction", "platform_readiness", "message_integrity", "total_score", "reasoning".
- Virality keys: "hook_score", "engagement_score", "value_score", "shareability_score", "total_score", "hook_type", "virality_reasoning".
- THIH scoring is primary; virality is secondary.
- Do not return segments shorter than {MIN_ACCEPTED_CLIP_SECONDS} seconds or longer than {MAX_ACCEPTED_CLIP_SECONDS} seconds.

Transcript:
{transcript}"""


def _parse_transcript_timestamp_seconds(timestamp: str) -> int:
    """Parse MM:SS or HH:MM:SS transcript timestamps into seconds."""
    parts = [int(part) for part in timestamp.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported timestamp format: {timestamp}")


def _format_transcript_timestamp(seconds: int) -> str:
    """Format seconds as a transcript timestamp."""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _parse_transcript_spans(transcript: str) -> list[dict[str, Any]]:
    """Parse timestamped transcript lines into spans."""
    spans = []
    for line in transcript.splitlines():
        match = TRANSCRIPT_SPAN_RE.match(line.strip())
        if not match:
            continue
        try:
            start_seconds = _parse_transcript_timestamp_seconds(match.group("start"))
            end_seconds = _parse_transcript_timestamp_seconds(match.group("end"))
        except ValueError:
            continue
        if end_seconds <= start_seconds:
            continue
        spans.append(
            {
                "start": start_seconds,
                "end": end_seconds,
                "text": match.group("text").strip(),
            }
        )
    return spans


def _extract_transcript_text(
    transcript_spans: list[dict[str, Any]], start_seconds: int, end_seconds: int
) -> str:
    """Return transcript text overlapping a selected time range."""
    selected_text = [
        span["text"]
        for span in transcript_spans
        if span["text"]
        and span["end"] > start_seconds
        and span["start"] < end_seconds
    ]
    return " ".join(selected_text).strip()


def _choose_repaired_bounds(
    transcript_spans: list[dict[str, Any]], start_seconds: int, end_seconds: int
) -> tuple[int, int] | None:
    """Repair model-selected bounds to the nearest acceptable contiguous range."""
    if not transcript_spans:
        return None

    starts = sorted({span["start"] for span in transcript_spans})
    ends = sorted({span["end"] for span in transcript_spans})
    current_duration = end_seconds - start_seconds

    if current_duration > MAX_ACCEPTED_CLIP_SECONDS:
        target_end = start_seconds + IDEAL_CLIP_MAX_SECONDS
        candidate_ends = [
            candidate
            for candidate in ends
            if start_seconds + MIN_ACCEPTED_CLIP_SECONDS
            <= candidate
            <= min(target_end, end_seconds)
        ]
        if candidate_ends:
            return start_seconds, max(candidate_ends)
        if start_seconds + MIN_ACCEPTED_CLIP_SECONDS <= target_end:
            return start_seconds, target_end
        return None

    if current_duration < MIN_ACCEPTED_CLIP_SECONDS:
        candidate_ranges: list[tuple[int, int, int]] = []
        for candidate_start in starts:
            if candidate_start > start_seconds:
                continue
            for candidate_end in ends:
                if candidate_end < end_seconds:
                    continue
                duration = candidate_end - candidate_start
                if MIN_ACCEPTED_CLIP_SECONDS <= duration <= MAX_ACCEPTED_CLIP_SECONDS:
                    extra_context = (start_seconds - candidate_start) + (
                        candidate_end - end_seconds
                    )
                    ideal_penalty = 0
                    if duration < IDEAL_CLIP_MIN_SECONDS:
                        ideal_penalty = IDEAL_CLIP_MIN_SECONDS - duration
                    elif duration > IDEAL_CLIP_MAX_SECONDS:
                        ideal_penalty = duration - IDEAL_CLIP_MAX_SECONDS
                    candidate_ranges.append(
                        (ideal_penalty * 1000 + extra_context, candidate_start, candidate_end)
                    )
        if candidate_ranges:
            _, repaired_start, repaired_end = min(candidate_ranges)
            return repaired_start, repaired_end

    return None


def _repair_segment_bounds(
    segment: TranscriptSegment,
    transcript_spans: list[dict[str, Any]],
    start_seconds: int,
    end_seconds: int,
) -> tuple[int, int] | None:
    """Adjust near-miss model ranges to usable transcript-aligned bounds."""
    repaired_bounds = _choose_repaired_bounds(
        transcript_spans,
        start_seconds,
        end_seconds,
    )
    if not repaired_bounds:
        return None

    repaired_start, repaired_end = repaired_bounds
    segment.start_time = _format_transcript_timestamp(repaired_start)
    segment.end_time = _format_transcript_timestamp(repaired_end)
    repaired_text = _extract_transcript_text(
        transcript_spans,
        repaired_start,
        repaired_end,
    )
    if repaired_text:
        segment.text = repaired_text
    logger.info(
        "Repaired segment duration: %s-%s -> %s-%s",
        _format_transcript_timestamp(start_seconds),
        _format_transcript_timestamp(end_seconds),
        segment.start_time,
        segment.end_time,
    )
    return repaired_start, repaired_end


async def get_most_relevant_parts_by_transcript(
    transcript: str,
    include_broll: bool = False,
    clip_signals: str | None = None,
    content_mode: ContentMode | str = DEFAULT_CONTENT_MODE,
    selection_instructions: str | None = None,
) -> TranscriptAnalysis:
    """Get the most relevant parts of a transcript with virality scoring and optional B-roll detection."""
    logger.info(
        f"Starting AI analysis of transcript ({len(transcript)} chars), include_broll={include_broll}"
    )

    try:
        prompt = build_transcript_analysis_prompt(
            transcript=transcript,
            include_broll=include_broll,
            clip_signals=clip_signals,
            content_mode=content_mode,
            selection_instructions=selection_instructions,
        )
        failures: list[tuple[str, Exception]] = []
        candidates = get_transcript_agent_candidates()
        attempted_models = [llm_name for llm_name, _ in candidates]
        for attempt_number, (llm_name, agent) in enumerate(candidates, start=1):
            logger.info(
                "LLM candidate attempt %s/%s: model=%s",
                attempt_number,
                len(candidates),
                llm_name,
            )
            try:
                result = await agent.run(prompt)
                analysis = result.output
                if attempt_number > 1:
                    logger.info(
                        "LLM fallback selected: model=%s attempt=%s",
                        llm_name,
                        attempt_number,
                    )
                break
            except Exception as candidate_error:
                failures.append((llm_name, candidate_error))
                logger.warning(
                    "LLM candidate failed: model=%s attempt=%s retryable=%s reason=%s",
                    llm_name,
                    attempt_number,
                    _is_retryable_provider_error(candidate_error),
                    _format_provider_reason(llm_name, candidate_error),
                )
        else:
            raise AIAnalysisFailure(
                _build_ai_analysis_failure_message(attempted_models, failures)
            )
        logger.info(
            f"AI analysis found {len(analysis.most_relevant_segments)} segments"
        )

        # Validation with virality data handling
        validated_segments = []
        transcript_spans = _parse_transcript_spans(transcript)
        for segment in analysis.most_relevant_segments:
            # Validate text content
            if not segment.text.strip() or len(segment.text.split()) < 3:
                logger.warning(
                    f"Skipping segment with insufficient content: '{segment.text[:50]}...'"
                )
                continue

            # Validate timestamps - CRITICAL: start and end must be different
            if segment.start_time == segment.end_time:
                logger.warning(
                    f"Skipping segment with identical start/end times: {segment.start_time}"
                )
                continue

            # Parse timestamps to validate duration
            try:
                start_seconds = _parse_transcript_timestamp_seconds(
                    segment.start_time
                )
                end_seconds = _parse_transcript_timestamp_seconds(segment.end_time)

                duration = end_seconds - start_seconds

                if duration < MIN_ACCEPTED_CLIP_SECONDS or duration > MAX_ACCEPTED_CLIP_SECONDS:
                    repaired_bounds = _repair_segment_bounds(
                        segment,
                        transcript_spans,
                        start_seconds,
                        end_seconds,
                    )
                    if repaired_bounds:
                        start_seconds, end_seconds = repaired_bounds
                        duration = end_seconds - start_seconds

                if duration <= 0:
                    logger.warning(
                        f"Skipping segment with invalid duration: {segment.start_time} to {segment.end_time} = {duration}s"
                    )
                    continue

                if duration < MIN_ACCEPTED_CLIP_SECONDS:
                    logger.warning(
                        f"Skipping segment too short: {duration}s (min {MIN_ACCEPTED_CLIP_SECONDS}s required)"
                    )
                    continue

                if duration > MAX_ACCEPTED_CLIP_SECONDS:
                    logger.warning(
                        f"Skipping segment too long: {duration}s (max {MAX_ACCEPTED_CLIP_SECONDS}s allowed)"
                    )
                    continue

                # Validate virality scores
                if segment.virality:
                    # Ensure total score is sum of subscores
                    calculated_total = (
                        segment.virality.hook_score
                        + segment.virality.engagement_score
                        + segment.virality.value_score
                        + segment.virality.shareability_score
                    )
                    if segment.virality.total_score != calculated_total:
                        logger.warning(
                            f"Correcting virality total: {segment.virality.total_score} -> {calculated_total}"
                        )
                        segment.virality.total_score = calculated_total

                validated_segments.append(segment)
                virality_info = (
                    f", virality={segment.virality.total_score}"
                    if segment.virality
                    else ""
                )
                logger.info(
                    f"Validated segment: {segment.start_time}-{segment.end_time} ({duration}s), thih={segment.thih.total_score if segment.thih else 'N/A'}{virality_info}"
                )

            except (ValueError, IndexError) as e:
                logger.warning(
                    f"Skipping segment with invalid timestamp format: {segment.start_time}-{segment.end_time}: {e}"
                )
                continue

        # Sort by THIH score first; virality remains a secondary signal.
        validated_segments.sort(
            key=lambda x: (
                x.thih.total_score if x.thih else 0,
                x.virality.total_score if x.virality else 0,
                x.relevance_score,
            ),
            reverse=True,
        )

        final_analysis = TranscriptAnalysis(
            most_relevant_segments=validated_segments,
            summary=analysis.summary,
            key_topics=analysis.key_topics,
            broll_opportunities=analysis.broll_opportunities if include_broll else None,
        )

        logger.info(f"Selected {len(validated_segments)} segments for processing")
        if validated_segments:
            top = validated_segments[0]
            logger.info(
                f"Top segment - relevance: {top.relevance_score:.2f}, thih: {top.thih.total_score if top.thih else 'N/A'}, virality: {top.virality.total_score if top.virality else 'N/A'}"
            )

        return final_analysis

    except Exception as e:
        logger.error(f"Error in transcript analysis: {e}")
        raise RuntimeError(f"Transcript analysis failed: {str(e)}") from e


def get_most_relevant_parts_sync(transcript: str) -> TranscriptAnalysis:
    """Synchronous wrapper for the async function."""
    return asyncio.run(get_most_relevant_parts_by_transcript(transcript))











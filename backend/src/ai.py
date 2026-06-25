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
    hook_sentence: str = Field(default="", description="Exact first hook sentence used as the clip opening.")
    key_point: str = Field(default="", description="Specific key point captured by the clip.")
    start_reason: str = Field(default="", description="Why this start boundary was selected.")
    end_reason: str = Field(default="", description="Why this end boundary completes the thought.")
    moment_type: str = Field(default="", description="Editorial sermon moment type.")
    why_selected: str = Field(default="", description="Evidence-grounded reason this candidate was selected.")
    why_this_is_not_intro: str = Field(default="", description="Why this is not merely intro/setup content.")
    why_this_is_complete_thought: str = Field(default="", description="Why the clip is self-contained.")
    suggested_title: Optional[str] = Field(default=None, description="Model-proposed title alias.")
    rejection_risks: List[str] = Field(default_factory=list, description="Potential editorial rejection risks.")
    hook_score_breakdown: Dict[str, int] = Field(default_factory=dict)
    ending_score_breakdown: Dict[str, int] = Field(default_factory=dict)
    publishability_score: int = Field(default=0, ge=0, le=100)
    publishability_verdict: str = Field(default="")
    clip_intelligence: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("rejection_risks", mode="before")
    @classmethod
    def _coerce_rejection_risks(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

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
            self.recommended_title = self.suggested_title or short_text or "THIH Clip Engine Moment"
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
    candidate_review: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-render editorial audit of raw, accepted, rejected, and shifted candidates.",
    )


# Enhanced system prompt with virality scoring and B-roll detection
transcript_analysis_system_prompt = """You are an expert transcript analyst for short-form video editing.

Your job is extraction and ranking, not creative rewriting. You must stay fully grounded in the transcript and choose the best clip candidates that already exist in the source material.

OUTPUT CONTRACT:
- Return valid JSON only. Do not output Markdown, headings, bullets, prose, code fences, explanations, or commentary outside the JSON object.
- The top-level JSON object must include: "most_relevant_segments", "summary", and "key_topics".
- Only include "broll_opportunities" when B-roll was requested.
- Each item in "most_relevant_segments" must include: "start_time", "end_time", "text", "relevance_score", "reasoning", "content_mode", "thih", "virality", "hook_sentence", "key_point", "start_reason", "end_reason", "moment_type", "why_selected", "why_this_is_not_intro", "why_this_is_complete_thought", "suggested_title", "recommended_title", "recommended_caption", "recommended_cta", "recommended_hashtags", "platform_fit", and "rejection_risks".
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

Required editorial evidence for each candidate:
- hook_sentence must be the exact first strong sentence viewers hear after trimming.
- key_point must name the concrete point captured by the selected span.
- start_reason must explain why the start boundary is the hook or minimum needed setup.
- end_reason must explain why the end boundary lands a complete thought.
- moment_type must be one of: Strong Opening Conviction, Scripture Explanation, Practical Application, Repentance / Heart-Check, Memorable Quote, Leadership / Work / Stewardship, Prayer or Invitation.
- why_selected must cite transcript evidence, not generic claims like "this is engaging."
- why_this_is_not_intro must prove the candidate is not just welcome/setup/branding/context.
- why_this_is_complete_thought must explain the setup, point, and payoff inside the span.
- rejection_risks should list any risk such as intro setup, weak hook, incomplete ending, duplicate idea, or missing context.

Recommended metadata:
- suggested_title and recommended_title should be concise, specific, and grounded in the selected span.
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
- Reject generic intros unless the intro sentence itself is a strong hook; avoid starts like "today," "in this video," "welcome," "we are talking about," or repeated branding/context
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
- Segment keys: "start_time", "end_time", "text", "relevance_score", "reasoning", "content_mode", "thih", "virality", "hook_sentence", "key_point", "start_reason", "end_reason", "moment_type", "why_selected", "why_this_is_not_intro", "why_this_is_complete_thought", "suggested_title", "recommended_title", "recommended_caption", "recommended_cta", "recommended_hashtags", "platform_fit", "scripture_reference", "content_warning", "rejection_risks".
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



GENERIC_INTRO_RE = re.compile(
    r"(?i)^\s*(welcome|hey|hello|today\b|in this video|we are talking about|"
    r"this message is about|before we start|let'?s talk about|i want to talk)\b"
)
GENERIC_REASON_RE = re.compile(
    r"(?i)^\s*(good clip|great clip|interesting|important|engaging|viral|selected by the ai|"
    r"this is a good|this is an important)\b\.?\s*$"
)
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
MOMENT_TYPES = {
    "Strong Opening Conviction",
    "Scripture Explanation",
    "Practical Application",
    "Repentance / Heart-Check",
    "Memorable Quote",
    "Leadership / Work / Stewardship",
    "Prayer or Invitation",
}


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_RE.findall(text or "") if sentence.strip()]


def _first_sentence(text: str) -> str:
    parts = _sentences(text)
    return parts[0] if parts else (text or "").strip()


def _final_sentence(text: str) -> str:
    parts = _sentences(text)
    return parts[-1] if parts else (text or "").strip()


def _normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _text_similarity(left: str, right: str) -> float:
    left_words = set(_normalize_words(left))
    right_words = set(_normalize_words(right))
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / max(1, len(left_words | right_words))


def _find_sentence_span(transcript_spans: list[dict[str, Any]], sentence: str) -> tuple[int, int] | None:
    sentence_words = set(_normalize_words(sentence))
    if not sentence_words:
        return None
    best: tuple[float, int, int] | None = None
    for span in transcript_spans:
        span_words = set(_normalize_words(span.get("text", "")))
        if not span_words:
            continue
        overlap = len(sentence_words & span_words) / max(1, len(sentence_words))
        if overlap >= 0.55 and (best is None or overlap > best[0]):
            best = (overlap, int(span["start"]), int(span["end"]))
    if best:
        return best[1], best[2]
    return None


def _score_hook_sentence(sentence: str) -> dict[str, int]:
    words = _normalize_words(sentence)
    text = (sentence or "").strip().lower()
    directness = 2 if len(words) >= 5 and not GENERIC_INTRO_RE.search(text) else 0
    tension_terms = {"cannot", "stop", "never", "but", "not", "without", "breaking", "repent", "wrong", "cost"}
    tension = 2 if any(word in tension_terms for word in words) else 0
    clarity = 2 if 6 <= len(words) <= 24 else 1 if len(words) >= 4 else 0
    specificity = 2 if any(len(word) >= 8 for word in words) or any(char.isdigit() for char in text) else 1 if len(set(words)) >= 5 else 0
    standalone = 2 if directness and clarity and not text.startswith(("and ", "but ", "so ", "because ", "that ", "this ")) else 0
    return {
        "directness": directness,
        "tension": tension,
        "clarity": clarity,
        "specificity": specificity,
        "first_sentence_strength": min(2, directness + tension),
        "standalone_feed_strength": standalone,
    }


def _score_ending_sentence(sentence: str) -> dict[str, int]:
    text = (sentence or "").strip().lower()
    words = _normalize_words(sentence)
    lands = 2 if any(word in words for word in ["therefore", "begins", "remember", "choose", "pray", "amen", "faithful", "wisdom", "purpose"]) else 1
    complete = 0 if text.endswith(("and", "but", "because", "so", "to")) else 2
    conviction = 2 if any(word in words for word in ["must", "cannot", "will", "faithful", "conviction", "truth", "repent", "wisdom"]) else 1
    avoids_drift = 0 if text.startswith(("now ", "next ", "another thing")) else 2
    return {
        "lands": lands,
        "complete_thought": complete,
        "conviction_or_invitation": conviction,
        "avoids_trailing_topic": avoids_drift,
    }


def _is_generic_reason(value: str) -> bool:
    return not value or len(_normalize_words(value)) < 7 or bool(GENERIC_REASON_RE.search(value))


def _has_mid_thought_risk(segment: TranscriptSegment, final_sentence: str) -> bool:
    final_text = (final_sentence or segment.text or "").strip()
    if final_text.endswith((",", ";", ":")):
        return True
    risk_text = " ".join(segment.rejection_risks or []).lower()
    return any(
        marker in risk_text
        for marker in (
            "mid-thought",
            "mid thought",
            "trailing phrase",
            "unfinished",
            "incomplete ending",
            "ends mid",
        )
    )


def _clean_hook_text(sentence: str) -> str:
    return re.sub(r"^speaker\s+[a-z0-9]+:\s*", "", (sentence or "").strip(), flags=re.IGNORECASE).strip()


def _is_weak_setup_hook(sentence: str) -> bool:
    lowered = _clean_hook_text(sentence).lower()
    return lowered.startswith((
        "many remember",
        "some of you remember",
        "i remember",
        "back in",
        "in the late",
        "there was a time",
        "set apart in",
        "this is an interesting",
        "this is a background",
        "here is some background",
        "let me give you some background",
        "a little background",
    ))


def _is_context_dependent_hook(sentence: str) -> bool:
    lowered = _clean_hook_text(sentence).lower()
    return lowered.startswith(("that is how", "this is how", "that is why", "this is why", "that means", "this means"))


def _ending_only_sets_up_next_idea(segment: TranscriptSegment) -> bool:
    ending_claim = f"{segment.end_reason} {segment.why_this_is_complete_thought}".lower()
    return any(
        marker in ending_claim
        for marker in (
            "tees up",
            "tee up",
            "sets up",
            "points toward",
            "before the longer",
            "before the next",
            "without needing the whole resolution",
            "problem setup",
        )
    )


def _calculate_publishability_score(
    segment: TranscriptSegment,
    hook_total: int,
    ending_total: int,
    intro_shifted: bool,
) -> tuple[int, dict[str, int], str]:
    hook_score = round((hook_total / 12) * 20)
    key_point_score = 15 if len(_normalize_words(segment.key_point)) >= 6 else 8 if segment.key_point else 0
    complete_thought_score = round((ending_total / 8) * 15)
    first_sentence = _first_sentence(segment.text)
    intro_risk_score = 5 if GENERIC_INTRO_RE.search(first_sentence) else 8 if intro_shifted else 10
    ending_score = round((ending_total / 8) * 10)
    moment_type_fit = 10 if segment.moment_type in MOMENT_TYPES else 0
    platform_fit = 10 if segment.platform_fit else 5
    duplicate_risk = 10
    sermon_integrity_score = segment.thih.message_integrity if segment.thih else 8
    score_breakdown = {
        "hook_score": hook_score,
        "key_point_score": key_point_score,
        "complete_thought_score": complete_thought_score,
        "intro_risk_score": intro_risk_score,
        "ending_score": ending_score,
        "moment_type_fit": moment_type_fit,
        "platform_fit": platform_fit,
        "duplicate_risk": duplicate_risk,
        "sermon_integrity_score": sermon_integrity_score,
    }
    total = max(0, min(100, sum(score_breakdown.values())))
    verdict = "publishable" if total >= 70 else "borderline" if total >= 55 else "reject"
    return total, score_breakdown, verdict


def _build_candidate_audit(
    segment: TranscriptSegment,
    *,
    candidate_id: str,
    decision: str,
    rejection_reason: str | None = None,
    shift_reason: str | None = None,
) -> dict[str, Any]:
    audit = dict(segment.clip_intelligence or {})
    audit.update(
        {
            "candidate_id": candidate_id,
            "decision": decision,
            "raw_start": audit.get("raw_start_time", segment.start_time),
            "raw_end": audit.get("raw_end_time", segment.end_time),
            "normalized_start": segment.start_time,
            "normalized_end": segment.end_time,
            "first_sentence": audit.get("exact_first_sentence", _first_sentence(segment.text)),
            "final_sentence": audit.get("exact_final_sentence", _final_sentence(segment.text)),
            "hook_score": sum(segment.hook_score_breakdown.values()) if segment.hook_score_breakdown else 0,
            "intro_risk": 1 if GENERIC_INTRO_RE.search(_first_sentence(segment.text)) else 0,
            "key_point": segment.key_point,
            "rejection_reason": rejection_reason,
            "shift_reason": shift_reason,
            "publishability_score": segment.publishability_score,
            "hook_sentence": segment.hook_sentence,
            "moment_type": segment.moment_type,
            "start_reason": segment.start_reason,
            "end_reason": segment.end_reason,
            "transcript_evidence": segment.text,
        }
    )
    return audit


def _is_duplicate_candidate(
    segment: TranscriptSegment,
    start_seconds: int,
    end_seconds: int,
    accepted: list[tuple[TranscriptSegment, int, int]],
) -> bool:
    for other, other_start, other_end in accepted:
        if abs(start_seconds - other_start) <= 5:
            return True
        overlap = max(0, min(end_seconds, other_end) - max(start_seconds, other_start))
        shorter = max(1, min(end_seconds - start_seconds, other_end - other_start))
        if overlap / shorter > 0.5:
            return True
        if _text_similarity(segment.key_point or segment.text, other.key_point or other.text) >= 0.72:
            return True
    return False


def _apply_clip_intelligence_gate(
    segment: TranscriptSegment,
    transcript_spans: list[dict[str, Any]],
    start_seconds: int,
    end_seconds: int,
) -> tuple[TranscriptSegment | None, int, int, str | None, dict[str, Any]]:
    raw_start_time = segment.start_time
    raw_end_time = segment.end_time
    text = segment.text.strip()
    hook_sentence = (segment.hook_sentence or _first_sentence(text)).strip()
    first_sentence = _first_sentence(text)
    final_sentence = _final_sentence(text)
    intro_shifted = False

    if GENERIC_INTRO_RE.search(first_sentence) and hook_sentence and hook_sentence != first_sentence:
        hook_span = _find_sentence_span(transcript_spans, hook_sentence)
        if hook_span and hook_span[0] > start_seconds and end_seconds - hook_span[0] >= MIN_ACCEPTED_CLIP_SECONDS:
            start_seconds = hook_span[0]
            segment.start_time = _format_transcript_timestamp(start_seconds)
            repaired_text = _extract_transcript_text(transcript_spans, start_seconds, end_seconds)
            if repaired_text:
                segment.text = repaired_text
                text = repaired_text
                first_sentence = _first_sentence(text)
                final_sentence = _final_sentence(text)
            intro_shifted = True

    segment.hook_sentence = hook_sentence or first_sentence
    if not segment.key_point:
        segment.key_point = segment.hook_sentence if len(_normalize_words(segment.hook_sentence)) >= 6 else ""
    if not segment.moment_type or segment.moment_type not in MOMENT_TYPES:
        segment.moment_type = _infer_moment_type(segment.text)

    hook_scores = _score_hook_sentence(segment.hook_sentence or first_sentence)
    ending_scores = _score_ending_sentence(final_sentence)
    hook_total = sum(hook_scores.values())
    ending_total = sum(ending_scores.values())
    rejection_reasons: list[str] = []

    if GENERIC_INTRO_RE.search(first_sentence) and not intro_shifted:
        rejection_reasons.append("starts with generic intro/setup language")
    if _is_weak_setup_hook(segment.hook_sentence or first_sentence):
        rejection_reasons.append("hook is weak setup rather than feed-ready tension")
    if _is_context_dependent_hook(segment.hook_sentence or first_sentence):
        rejection_reasons.append("hook is not standalone without previous context")
    if not segment.key_point or len(_normalize_words(segment.key_point)) < 4:
        rejection_reasons.append("lacks a clear key point")
    if hook_total < 7:
        rejection_reasons.append("first 3 seconds do not contain a strong hook")
    if ending_total < 5:
        rejection_reasons.append("ending does not land as a complete thought")
    if _has_mid_thought_risk(segment, final_sentence):
        rejection_reasons.append("candidate ends mid-thought or with a trailing phrase")
    if _is_generic_reason(segment.why_selected or segment.reasoning):
        rejection_reasons.append("selection reason is generic or empty")
    if not segment.hook_sentence:
        rejection_reasons.append("hook_sentence evidence is missing")
    if not segment.start_reason or _is_generic_reason(segment.start_reason):
        rejection_reasons.append("start_reason evidence is missing or generic")
    if not segment.end_reason or _is_generic_reason(segment.end_reason):
        rejection_reasons.append("end_reason evidence is missing or generic")
    if not segment.why_selected or _is_generic_reason(segment.why_selected):
        rejection_reasons.append("why_selected evidence is missing or generic")
    if not text or len(_normalize_words(text)) < 6:
        rejection_reasons.append("transcript_evidence is missing")
    if not segment.why_this_is_not_intro:
        rejection_reasons.append("why_this_is_not_intro evidence is missing")
    if not segment.why_this_is_complete_thought:
        rejection_reasons.append("complete thought evidence is missing")
    if _ending_only_sets_up_next_idea(segment):
        rejection_reasons.append("ending only sets up the next idea instead of landing the thought")

    publishability_score, publishability_breakdown, publishability_verdict = _calculate_publishability_score(
        segment,
        hook_total,
        ending_total,
        intro_shifted,
    )
    if publishability_verdict == "reject":
        rejection_reasons.append("THIH publishability score is below acceptance threshold")

    audit = {
        "raw_start_time": raw_start_time,
        "raw_end_time": raw_end_time,
        "normalized_start_time": segment.start_time,
        "normalized_end_time": segment.end_time,
        "exact_first_sentence": first_sentence,
        "exact_final_sentence": final_sentence,
        "hook_sentence": segment.hook_sentence,
        "hook_reason": segment.start_reason or f"Hook score {hook_total}/12 from transcript evidence.",
        "key_point_captured": segment.key_point,
        "moment_type": segment.moment_type,
        "why_selected": segment.why_selected or segment.reasoning,
        "why_not_rejected": segment.why_this_is_not_intro or "Passed deterministic intro, hook, completeness, and duplicate gates.",
        "score_breakdown": {
            "hook": hook_scores,
            "ending": ending_scores,
            "thih_total": segment.thih.total_score if segment.thih else 0,
            "virality_total": segment.virality.total_score if segment.virality else 0,
            "publishability": publishability_breakdown,
        },
        "publishability_score": publishability_score,
        "publishability_verdict": publishability_verdict,
        "transcript_evidence_used": text,
        "intro_shifted": intro_shifted,
        "rejection_risks": segment.rejection_risks,
    }
    segment.hook_score_breakdown = hook_scores
    segment.ending_score_breakdown = ending_scores
    segment.publishability_score = publishability_score
    segment.publishability_verdict = publishability_verdict
    segment.clip_intelligence = audit
    if segment.thih:
        segment.thih.reasoning = f"{segment.thih.reasoning} Hook evidence: {segment.hook_sentence} Key point: {segment.key_point}".strip()

    if rejection_reasons:
        logger.info(
            "Clip Intelligence Audit rejected: raw=%s-%s normalized=%s-%s reasons=%s evidence=%s",
            raw_start_time,
            raw_end_time,
            segment.start_time,
            segment.end_time,
            rejection_reasons,
            text[:240],
        )
        return None, start_seconds, end_seconds, "; ".join(rejection_reasons), audit

    logger.info(
        "Clip Intelligence Audit accepted: raw=%s-%s normalized=%s-%s hook=%s key_point=%s moment_type=%s why_selected=%s scores=%s evidence=%s",
        raw_start_time,
        raw_end_time,
        segment.start_time,
        segment.end_time,
        segment.hook_sentence,
        segment.key_point,
        segment.moment_type,
        audit["why_selected"],
        audit["score_breakdown"],
        text[:240],
    )
    return segment, start_seconds, end_seconds, None, audit


def _infer_moment_type(text: str) -> str:
    lowered = (text or "").lower()
    if any(term in lowered for term in ["romans", "scripture", "verse", "bible", "god says"]):
        return "Scripture Explanation"
    if any(term in lowered for term in ["repent", "heart", "conviction", "turn from"]):
        return "Repentance / Heart-Check"
    if any(term in lowered for term in ["work", "steward", "calling", "leadership", "business"]):
        return "Leadership / Work / Stewardship"
    if any(term in lowered for term in ["pray", "prayer", "invitation", "amen"]):
        return "Prayer or Invitation"
    if any(term in lowered for term in ["do this", "practice", "step", "apply"]):
        return "Practical Application"
    if len(_sentences(text)) <= 2:
        return "Memorable Quote"
    return "Strong Opening Conviction"


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
        accepted_ranges: list[tuple[TranscriptSegment, int, int]] = []
        accepted_candidate_audits: list[dict[str, Any]] = []
        rejected_candidate_audits: list[dict[str, Any]] = []
        transcript_spans = _parse_transcript_spans(transcript)
        for candidate_index, segment in enumerate(analysis.most_relevant_segments, start=1):
            candidate_id = f"candidate-{candidate_index}"
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

                gated_segment, start_seconds, end_seconds, rejection_reason, gate_audit = _apply_clip_intelligence_gate(
                    segment,
                    transcript_spans,
                    start_seconds,
                    end_seconds,
                )
                if gated_segment is None:
                    logger.info(
                        "Skipping segment after clip intelligence gate: %s",
                        rejection_reason,
                    )
                    rejected_candidate_audits.append(
                        _build_candidate_audit(
                            segment,
                            candidate_id=candidate_id,
                            decision="rejected",
                            rejection_reason=rejection_reason,
                            shift_reason="shifted past intro" if gate_audit.get("intro_shifted") else None,
                        )
                    )
                    continue
                segment = gated_segment
                duration = end_seconds - start_seconds
                if _is_duplicate_candidate(segment, start_seconds, end_seconds, accepted_ranges):
                    logger.info(
                        "Skipping duplicate clip candidate after intelligence gate: %s-%s key_point=%s",
                        segment.start_time,
                        segment.end_time,
                        segment.key_point,
                    )
                    rejected_candidate_audits.append(
                        _build_candidate_audit(
                            segment,
                            candidate_id=candidate_id,
                            decision="rejected",
                            rejection_reason="duplicate idea or overlapping timestamp range",
                            shift_reason="shifted past intro" if gate_audit.get("intro_shifted") else None,
                        )
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

                accepted_ranges.append((segment, start_seconds, end_seconds))
                validated_segments.append(segment)
                accepted_candidate_audits.append(
                    _build_candidate_audit(
                        segment,
                        candidate_id=candidate_id,
                        decision="shifted" if gate_audit.get("intro_shifted") else "accepted",
                        shift_reason="shifted past intro to first strong hook sentence" if gate_audit.get("intro_shifted") else None,
                    )
                )
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

        candidate_review = {
            "raw_count": len(analysis.most_relevant_segments),
            "accepted_count": len(accepted_candidate_audits),
            "rejected_count": len(rejected_candidate_audits),
            "accepted_candidates": accepted_candidate_audits,
            "rejected_candidates": rejected_candidate_audits,
        }

        final_analysis = TranscriptAnalysis(
            most_relevant_segments=validated_segments,
            summary=analysis.summary,
            key_topics=analysis.key_topics,
            broll_opportunities=analysis.broll_opportunities if include_broll else None,
            candidate_review=candidate_review,
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












import pytest
from types import SimpleNamespace

from pydantic_ai.models.ollama import OllamaModel

from src import ai

from src.ai import (
    IDEAL_CLIP_MAX_SECONDS,
    IDEAL_CLIP_MIN_SECONDS,
    MIN_ACCEPTED_CLIP_SECONDS,
    TranscriptSegment,
    SUPPORTED_CONTENT_MODES,
    _build_transcript_model,
    _choose_repaired_bounds,
    _extract_transcript_text,
    _format_transcript_timestamp,
    _get_missing_llm_key_error,
    _parse_transcript_spans,
    _parse_transcript_timestamp_seconds,
    build_transcript_analysis_prompt,
    transcript_analysis_system_prompt,
)


def test_system_prompt_enforces_grounding_rules():
    assert "extraction and ranking, not creative rewriting" in (
        transcript_analysis_system_prompt
    )
    assert "Never invent facts, tone, context, or transitions" in (
        transcript_analysis_system_prompt
    )
    assert "Each selected segment must map to one contiguous range" in (
        transcript_analysis_system_prompt
    )
    assert "Do not judge, moralize, or downgrade a segment" in (
        transcript_analysis_system_prompt
    )
    assert f"{IDEAL_CLIP_MIN_SECONDS}-{IDEAL_CLIP_MAX_SECONDS} seconds" in (
        transcript_analysis_system_prompt
    )
    assert "Bad picks include intros" in transcript_analysis_system_prompt
    assert "Return valid JSON only" in transcript_analysis_system_prompt
    assert "Do not use \"segment\" as an output field. Use \"text\"." in (
        transcript_analysis_system_prompt
    )


def test_build_transcript_analysis_prompt_requires_transcript_fidelity():
    prompt = build_transcript_analysis_prompt(
        transcript="[00:12 - 00:21] A strong opening line"
    )

    assert "Do not fabricate or embellish content." in prompt
    assert "Do not merge separate non-contiguous moments into one segment." in prompt
    assert "If there is a tradeoff between \"viral\" and \"accurate\", choose accuracy." in prompt
    assert "Do not reject or penalize a segment simply because of the subject matter" in prompt
    assert f"Most selected clips should be {IDEAL_CLIP_MIN_SECONDS}-{IDEAL_CLIP_MAX_SECONDS} seconds." in prompt
    assert "viewer would understand and care without seeing the rest" in prompt
    assert "distinct clips from different parts" in prompt
    assert "Return one valid JSON object and nothing else." in prompt
    assert "No Markdown, headings, bullets, code fences" in prompt
    assert "[00:12 - 00:21] A strong opening line" in prompt


def test_build_transcript_analysis_prompt_mentions_broll_only_when_enabled():
    without_broll = build_transcript_analysis_prompt(
        transcript="[00:12 - 00:21] A strong opening line"
    )
    with_broll = build_transcript_analysis_prompt(
        transcript="[00:12 - 00:21] A strong opening line",
        include_broll=True,
    )

    assert "B-roll opportunities" not in without_broll
    assert "B-roll opportunities" in with_broll


def test_ollama_llm_builds_native_ollama_model():
    runtime_config = SimpleNamespace(
        llm="ollama:gpt-oss:20b",
        ollama_api_key=None,
        resolve_ollama_base_url=lambda: "http://ollama.example/v1",
    )

    model = _build_transcript_model(runtime_config)

    assert isinstance(model, OllamaModel)
    assert model.model_name == "gpt-oss:20b"
    assert model.base_url == "http://ollama.example/v1/"


def test_parse_transcript_timestamp_supports_minute_and_hour_formats():
    assert _parse_transcript_timestamp_seconds("02:35") == 155
    assert _parse_transcript_timestamp_seconds("01:02:35") == 3755
    assert _format_transcript_timestamp(155) == "02:35"
    assert _format_transcript_timestamp(3755) == "01:02:35"
    assert MIN_ACCEPTED_CLIP_SECONDS == 15


def test_transcript_span_helpers_repair_near_miss_durations():
    spans = _parse_transcript_spans(
        "\n".join(
            [
                "[00:00 - 00:10] Setup",
                "[00:10 - 00:24] Short highlight",
                "[00:24 - 00:36] Payoff",
                "[00:36 - 01:20] Too much background",
            ]
        )
    )

    assert _extract_transcript_text(spans, 10, 36) == "Short highlight Payoff"
    assert _choose_repaired_bounds(spans, 10, 24) == (10, 36)
    assert _choose_repaired_bounds(spans, 0, 80) == (0, 36)


def test_transcript_segment_normalizes_percent_relevance_score():
    segment = TranscriptSegment(
        start_time="00:00",
        end_time="00:30",
        text="A complete standalone moment with useful context.",
        relevance_score=100,
    )

    assert segment.relevance_score == 1.0


def test_llm_validation_rejects_unsupported_or_incomplete_model_names():
    runtime_config = SimpleNamespace(
        google_api_key=None,
        openai_api_key=None,
        anthropic_api_key=None,
    )

    assert "Unsupported LLM provider" in _get_missing_llm_key_error(
        "local:model", runtime_config
    )
    assert "missing a model name" in _get_missing_llm_key_error(
        "ollama:", runtime_config
    )
    assert _get_missing_llm_key_error("ollama:gpt-oss:20b", runtime_config) is None


def test_system_prompt_includes_thih_scoring_contract():
    assert "THIH SCORING" in transcript_analysis_system_prompt
    assert "opening_clarity" in transcript_analysis_system_prompt
    assert "message_integrity" in transcript_analysis_system_prompt
    assert "recommended_title" in transcript_analysis_system_prompt
    assert "scripture_reference" in transcript_analysis_system_prompt
    assert "virality is secondary" in transcript_analysis_system_prompt.lower()


def test_build_transcript_analysis_prompt_accepts_content_modes():
    prompt = build_transcript_analysis_prompt(
        transcript="[00:12 - 00:42] A strong opening line about stewardship",
        content_mode="sermon",
    )

    assert "Content mode: sermon" in prompt
    assert "supported content modes" in prompt.lower()
    for mode in SUPPORTED_CONTENT_MODES:
        assert mode in prompt
    assert "THIH scoring" in prompt
    assert "recommended_hashtags" in prompt
@pytest.mark.asyncio
async def test_transcript_analysis_uses_fallback_agent_when_primary_fails(monkeypatch):
    calls = []

    class FakeAgent:
        def __init__(self, name, should_fail=False):
            self.name = name
            self.should_fail = should_fail

        async def run(self, prompt):
            calls.append(self.name)
            if self.should_fail:
                raise RuntimeError("provider overloaded")
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:00",
                            end_time="00:30",
                            text="You cannot build faithful work on distracted attention. That is why the next obedient step has to begin with focus.",
                            relevance_score=0.91,
                            hook_sentence="You cannot build faithful work on distracted attention.",
                            key_point="Faithful work requires focused attention and an obedient next step.",
                            start_reason="Start on the direct warning because it is the first standalone hook.",
                            end_reason="End after the obedient next step sentence completes the application.",
                            moment_type="Leadership / Work / Stewardship",
                            why_selected="The span gives a direct warning about distracted attention and lands with an obedient next step.",
                            why_this_is_not_intro="It opens with the core warning rather than setup language.",
                            why_this_is_complete_thought="It includes the warning, the reason it matters, and the application.",
                        )
                    ],
                    summary="Fallback succeeded",
                    key_topics=["fallback"],
                )
            )

    monkeypatch.setattr(
        ai,
        "get_transcript_agent_candidates",
        lambda: [
            ("google-gla:primary", FakeAgent("primary", should_fail=True)),
            ("openai:fallback", FakeAgent("fallback")),
        ],
    )

    result = await ai.get_most_relevant_parts_by_transcript(
        "[00:00 - 00:30] A complete standalone moment with useful context for the viewer."
    )

    assert calls == ["primary", "fallback"]
    assert result.summary == "Fallback succeeded"
    assert len(result.most_relevant_segments) == 1
@pytest.mark.asyncio
async def test_transcript_analysis_failure_message_is_sanitized_and_actionable(monkeypatch):
    class FailingAgent:
        async def run(self, prompt):
            error = RuntimeError("503 overloaded while using sk-secret-token with request body payload")
            error.status_code = 503
            raise error

    monkeypatch.setattr(
        ai,
        "get_transcript_agent_candidates",
        lambda: [
            ("google-gla:primary", FailingAgent()),
            ("openai:fallback", FailingAgent()),
        ],
    )

    with pytest.raises(RuntimeError) as exc_info:
        await ai.get_most_relevant_parts_by_transcript(
            "[00:00 - 00:15] You cannot build faithful work on distracted attention.\n[00:15 - 00:30] That is why the next obedient step has to begin with focus."
        )

    message = str(exc_info.value)
    assert "Primary LLM: google-gla:primary" in message
    assert "Fallbacks attempted: openai:fallback" in message
    assert "Final provider reason: openai:fallback returned status 503" in message
    assert "Next action:" in message
    assert "sk-secret-token" not in message
    assert "request body payload" not in message


def test_build_transcript_analysis_prompt_includes_shorts_factory_instructions():
    prompt = build_transcript_analysis_prompt(
        transcript="[00:08 - 00:37] Steward the work with clarity and conviction.",
        content_mode="sermon",
        selection_instructions="Prioritize Romans 12:2 moments with practical application.",
    )

    assert "Task-level THIH Shorts Factory selection instructions" in prompt
    assert "Prioritize Romans 12:2 moments with practical application." in prompt
    assert "message integrity" in prompt


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_weak_intro_and_generic_reason(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:00",
                            end_time="00:30",
                            text="Welcome today we are talking about the message and what this video is about.",
                            relevance_score=0.9,
                            reasoning="Good clip.",
                            key_point="",
                            hook_sentence="Welcome today we are talking about the message.",
                        )
                    ],
                    summary="Intro",
                    key_topics=["intro"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "[00:00 - 00:30] Welcome today we are talking about the message and what this video is about."
    )

    assert result.most_relevant_segments == []


@pytest.mark.asyncio
async def test_clip_intelligence_shifts_repeated_intro_to_first_strong_sentence(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:00",
                            end_time="00:42",
                            text=(
                                "Today we are talking about Romans 12. "
                                "Do not be conformed to this world. "
                                "The clearest proof of transformation is what you stop copying. "
                                "That is where faithful work begins."
                            ),
                            relevance_score=0.95,
                            reasoning="Selected because the span moves from Romans 12 into a concrete transformation claim and faithful work payoff.",
                            hook_sentence="The clearest proof of transformation is what you stop copying.",
                            key_point="Transformation is seen in what a believer refuses to copy.",
                            start_reason="Start at the first strong standalone conviction after setup.",
                            end_reason="End after the faithful work payoff completes the thought.",
                            moment_type="Strong Opening Conviction",
                            why_selected="It contains a direct conviction, a clear Romans 12 application, and a complete payoff about faithful work.",
                            why_this_is_not_intro="The selected hook is the transformation claim, not the setup sentence.",
                            why_this_is_complete_thought="The clip states the principle and lands with where faithful work begins.",
                            rejection_risks=["brief scripture setup before hook"],
                        )
                    ],
                    summary="Romans 12 application",
                    key_topics=["Romans 12"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "\n".join(
            [
                "[00:00 - 00:08] Today we are talking about Romans 12.",
                "[00:08 - 00:18] Do not be conformed to this world.",
                "[00:18 - 00:32] The clearest proof of transformation is what you stop copying.",
                "[00:32 - 00:42] That is where faithful work begins.",
            ]
        )
    )

    assert len(result.most_relevant_segments) == 1
    segment = result.most_relevant_segments[0]
    assert segment.start_time == "00:18"
    assert segment.hook_sentence == "The clearest proof of transformation is what you stop copying."
    assert segment.clip_intelligence["intro_shifted"] is True
    assert segment.clip_intelligence["raw_start_time"] == "00:00"


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_duplicate_ideas_and_allows_fewer_clips(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            first = ai.TranscriptSegment(
                start_time="00:20",
                end_time="00:50",
                text="You cannot steward your calling while copying the pattern that is breaking your attention.",
                relevance_score=0.95,
                reasoning="Selected because it gives a direct stewardship warning tied to attention and calling.",
                hook_sentence="You cannot steward your calling while copying the pattern that is breaking your attention.",
                key_point="Calling requires refusing attention-breaking patterns.",
                why_selected="It is a direct, specific, standalone warning with a complete stewardship point.",
                start_reason="Start on the direct stewardship warning because it is already a standalone hook.",
                end_reason="End after the attention-breaking pattern sentence completes the warning.",
                why_this_is_not_intro="It opens with the core claim rather than setup.",
                why_this_is_complete_thought="The sentence contains the warning and the reason it matters.",
                moment_type="Leadership / Work / Stewardship",
            )
            duplicate = first.model_copy(update={"start_time": "00:23", "end_time": "00:53"})
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[first, duplicate],
                    summary="Stewardship",
                    key_topics=["calling"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "\n".join(
            [
                "[00:20 - 00:35] You cannot steward your calling while copying the pattern that is breaking your attention.",
                "[00:35 - 00:50] That is not discipline, that is drift with a schedule.",
                "[00:50 - 01:05] You cannot steward your calling while copying the pattern that is breaking your attention.",
            ]
        )
    )

    assert len(result.most_relevant_segments) == 1
    assert result.most_relevant_segments[0].moment_type == "Leadership / Work / Stewardship"


@pytest.mark.asyncio
async def test_clip_intelligence_returns_candidate_review_with_rejection_reasons(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            weak_intro = ai.TranscriptSegment(
                start_time="00:00",
                end_time="00:30",
                text="Welcome today we are talking about the message and what this video is about.",
                relevance_score=0.8,
                reasoning="Good clip.",
                hook_sentence="Welcome today we are talking about the message.",
            )
            strong = ai.TranscriptSegment(
                start_time="00:30",
                end_time="01:00",
                text=(
                    "You cannot follow Jesus while copying the anxiety that is discipling everyone else. "
                    "Faithful work begins when your attention belongs to God again."
                ),
                relevance_score=0.95,
                reasoning="Selected because the transcript gives a direct discipleship warning and a faithful work landing point.",
                hook_sentence="You cannot follow Jesus while copying the anxiety that is discipling everyone else.",
                key_point="Discipleship changes what shapes a believer's attention.",
                start_reason="Start on the first direct warning, which is already the hook.",
                end_reason="End after the faithful work sentence lands the application.",
                moment_type="Practical Application",
                why_selected="The span contains a direct warning about copied anxiety and lands with attention belonging to God.",
                why_this_is_not_intro="It opens with the core warning, not welcome or setup language.",
                why_this_is_complete_thought="It states the warning, why it matters, and the faithful work application.",
            )
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[weak_intro, strong],
                    summary="Discipleship and attention",
                    key_topics=["discipleship"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "\n".join(
            [
                "[00:00 - 00:30] Welcome today we are talking about the message and what this video is about.",
                "[00:30 - 00:45] You cannot follow Jesus while copying the anxiety that is discipling everyone else.",
                "[00:45 - 01:00] Faithful work begins when your attention belongs to God again.",
            ]
        )
    )

    assert len(result.most_relevant_segments) == 1
    assert result.candidate_review["raw_count"] == 2
    assert len(result.candidate_review["accepted_candidates"]) == 1
    assert len(result.candidate_review["rejected_candidates"]) == 1
    rejected = result.candidate_review["rejected_candidates"][0]
    assert rejected["decision"] == "rejected"
    assert "intro" in rejected["rejection_reason"]
    accepted = result.candidate_review["accepted_candidates"][0]
    assert accepted["decision"] == "accepted"
    assert accepted["publishability_score"] > 0


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_missing_required_evidence(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:10",
                            end_time="00:40",
                            text="You cannot build a faithful life on distracted attention. The fruit of your work follows the focus of your worship.",
                            relevance_score=0.9,
                            reasoning="Selected because the transcript links distracted attention with faithful work and worship.",
                            hook_sentence="You cannot build a faithful life on distracted attention.",
                            key_point="Faithful work requires focused worship-shaped attention.",
                            moment_type="Leadership / Work / Stewardship",
                            why_selected="The transcript gives a direct warning and a specific worship-shaped application.",
                            why_this_is_not_intro="It opens on the warning rather than setup.",
                            why_this_is_complete_thought="It contains the warning and the application.",
                        )
                    ],
                    summary="Attention",
                    key_topics=["attention"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "\n".join(
            [
                "[00:10 - 00:25] You cannot build a faithful life on distracted attention.",
                "[00:25 - 00:40] The fruit of your work follows the focus of your worship.",
            ]
        )
    )

    assert result.most_relevant_segments == []
    assert "start_reason" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_trailing_mid_thought_risk(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:00",
                            end_time="00:31",
                            text=(
                                "When this command is first, everything downstream stabilizes. "
                                "Does he actually rank first in your decisions, your loyalties, your love,"
                            ),
                            relevance_score=0.95,
                            reasoning="Selected because it gives a direct priority claim and a diagnostic heart-check.",
                            hook_sentence="When this command is first, everything downstream stabilizes.",
                            key_point="Putting God first stabilizes life and exposes whether he ranks first in decisions and love.",
                            start_reason="Start on the direct priority claim because it is a standalone hook.",
                            end_reason="End after the diagnostic heart-question is stated.",
                            moment_type="Strong Opening Conviction",
                            why_selected="The span moves from a clear priority claim to a specific heart-check about decisions and love.",
                            why_this_is_not_intro="It opens with the core conviction rather than welcome or setup.",
                            why_this_is_complete_thought="It states the priority claim and applies it to a heart-check.",
                            rejection_risks=["Clip ends mid-thought/trailing phrase."],
                        )
                    ],
                    summary="Priority",
                    key_topics=["God first"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "\n".join(
            [
                "[00:00 - 00:15] When this command is first, everything downstream stabilizes.",
                "[00:15 - 00:31] Does he actually rank first in your decisions, your loyalties, your love,",
            ]
        )
    )

    assert result.most_relevant_segments == []
    assert "mid-thought" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_weak_nostalgia_setup_hook(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:00",
                            end_time="00:45",
                            text="Many remember the late 1990s. WWJD became a bracelet, a trend, then a brand.",
                            relevance_score=0.92,
                            reasoning="Selected because it introduces the WWJD cultural trend and its branding payoff.",
                            hook_sentence="Many remember the late 1990s.",
                            key_point="WWJD became a sincere trend and brand that shaped Christian culture.",
                            start_reason="Starts at the vivid narrative hook that needs no context.",
                            end_reason="Ends after the trend then brand payoff before the longer thesis expansion.",
                            moment_type="Strong Opening Conviction",
                            why_selected="The span introduces the WWJD cultural trend and lands with the brand payoff.",
                            why_this_is_not_intro="It begins the story rather than greeting the audience.",
                            why_this_is_complete_thought="It states the cultural memory and the branding payoff.",
                        )
                    ],
                    summary="WWJD",
                    key_topics=["WWJD"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "[00:00 - 00:45] Many remember the late 1990s. WWJD became a bracelet, a trend, then a brand."
    )

    assert result.most_relevant_segments == []
    assert "weak setup" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_ending_that_only_sets_up_next_idea(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="02:15",
                            end_time="02:55",
                            text="At work, his team dreaded his emails. He wore Christian language, but the Spirit pressed in.",
                            relevance_score=0.93,
                            reasoning="Selected because it creates workplace tension and moves toward conviction.",
                            hook_sentence="At work, his team dreaded his emails.",
                            key_point="Religious signaling can coexist with unloving leadership until conviction breaks through.",
                            start_reason="Start on the workplace tension because it creates immediate conflict.",
                            end_reason="Ends at the turn, which tees up conviction without needing the whole resolution.",
                            moment_type="Leadership / Work / Stewardship",
                            why_selected="The span contrasts Christian language with damaging workplace leadership.",
                            why_this_is_not_intro="It opens with conflict, not setup language.",
                            why_this_is_complete_thought="It completes the problem setup and points toward conviction.",
                        )
                    ],
                    summary="Workplace conviction",
                    key_topics=["leadership"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "[02:15 - 02:55] At work, his team dreaded his emails. He wore Christian language, but the Spirit pressed in."
    )

    assert result.most_relevant_segments == []
    assert "next idea" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_title_like_sermon_setup_hook(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:01",
                            end_time="00:50",
                            text="Set apart in a blended culture. Conviction erodes slowly through small adjustments.",
                            relevance_score=0.94,
                            reasoning="Selected because it names the sermon theme and explains quiet erosion.",
                            hook_sentence="Set apart in a blended culture.",
                            key_point="Conviction erodes quietly through small cultural adjustments.",
                            start_reason="Starts at the first line that names the theme.",
                            end_reason="Ends after the summary that nothing dramatic happened, just erosion.",
                            moment_type="Strong Opening Conviction",
                            why_selected="The span names the blended culture theme and explains quiet erosion.",
                            why_this_is_not_intro="It begins with the theme rather than greeting language.",
                            why_this_is_complete_thought="It states the theme and summarizes erosion.",
                        )
                    ],
                    summary="Romans 12",
                    key_topics=["Romans 12"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "[00:01 - 00:50] Set apart in a blended culture. Conviction erodes slowly through small adjustments."
    )

    assert result.most_relevant_segments == []
    assert "weak setup" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]


@pytest.mark.asyncio
async def test_clip_intelligence_rejects_context_dependent_that_hook(monkeypatch):
    class FakeAgent:
        async def run(self, prompt):
            return SimpleNamespace(
                output=ai.TranscriptAnalysis(
                    most_relevant_segments=[
                        ai.TranscriptSegment(
                            start_time="00:50",
                            end_time="01:40",
                            text="That is how a blended culture works. Romans 12:2 commands us not to be conformed.",
                            relevance_score=0.94,
                            reasoning="Selected because it explains blended culture and quotes Romans 12.",
                            hook_sentence="That is how a blended culture works.",
                            key_point="Romans 12:2 commands believers not to conform to a blended culture.",
                            start_reason="Starts at the line that summarizes the blended culture mechanism.",
                            end_reason="Ends after the Romans 12 command completes the thought.",
                            moment_type="Scripture Explanation",
                            why_selected="The span connects blended culture to the Romans 12 command.",
                            why_this_is_not_intro="It begins with the mechanism rather than greeting language.",
                            why_this_is_complete_thought="It names the mechanism and gives the Scripture command.",
                        )
                    ],
                    summary="Romans 12",
                    key_topics=["Romans 12"],
                )
            )

    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fake:model", FakeAgent())])

    result = await ai.get_most_relevant_parts_by_transcript(
        "[00:50 - 01:40] That is how a blended culture works. Romans 12:2 commands us not to be conformed."
    )

    assert result.most_relevant_segments == []
    assert "standalone" in result.candidate_review["rejected_candidates"][0]["rejection_reason"]

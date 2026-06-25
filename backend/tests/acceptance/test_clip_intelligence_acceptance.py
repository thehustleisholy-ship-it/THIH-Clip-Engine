from pathlib import Path
from types import SimpleNamespace

import pytest

from src import ai
from src.services.video_service import VideoService


SERMON_TRANSCRIPT = "\n".join(
    [
        "[00:00 - 00:06] Welcome everyone, today we are talking about Romans 12 and blended culture.",
        "[00:06 - 00:15] You cannot follow Jesus while copying the world that is discipling your attention.",
        "[00:15 - 00:30] Romans 12 calls that conformity, and the first act of mercy is to refuse the mold.",
        "[00:30 - 00:38] This is an interesting background thought with no clear point yet.",
        "[00:38 - 00:58] The scripture refuses to let us call cultural comfort wisdom when God calls us to transformation.",
        "[00:58 - 01:15] Paul says do not be conformed to this world, but be transformed by the renewal of your mind.",
        "[01:15 - 01:35] Name the pressure that is shaping you before it becomes your pattern.",
        "[01:35 - 01:55] If approval is discipling you, decide today what obedience will cost and take the first faithful step.",
        "[01:55 - 02:10] Conviction erodes when you keep feeding the same fear and calling it normal.",
        "[02:10 - 02:28] Cut one stream of formation and replace it with truth before tomorrow morning.",
        "[02:28 - 02:44] The real test is not whether you liked the sermon but whether you will obey when",
        "[02:44 - 03:00] Name the pressure that is shaping you before it becomes your pattern.",
        "[03:00 - 03:20] If approval is discipling you, decide today what obedience will cost and take the first faithful step.",
    ]
)


class FixtureAgent:
    async def run(self, prompt):
        shifted_intro = ai.TranscriptSegment(
            start_time="00:00",
            end_time="00:30",
            text=(
                "Welcome everyone, today we are talking about Romans 12 and blended culture. "
                "You cannot follow Jesus while copying the world that is discipling your attention. "
                "Romans 12 calls that conformity, and the first act of mercy is to refuse the mold."
            ),
            relevance_score=0.95,
            reasoning="Selected because it shifts from setup into a direct Romans 12 conviction about copied attention.",
            hook_sentence="You cannot follow Jesus while copying the world that is discipling your attention.",
            key_point="Following Jesus requires refusing the world's mold over attention.",
            start_reason="Shift past welcome/setup to the first direct standalone conviction.",
            end_reason="End after Romans 12 names conformity and the refusal of the mold.",
            moment_type="Strong Opening Conviction",
            why_selected="The span contains a direct hook, Romans 12 support, and a complete refusal-of-conformity payoff.",
            why_this_is_not_intro="The accepted start is the conviction sentence, not the welcome or topic setup.",
            why_this_is_complete_thought="It states the warning, names conformity, and lands with refusing the mold.",
        )
        weak_hook = ai.TranscriptSegment(
            start_time="00:30",
            end_time="00:58",
            text=(
                "This is an interesting background thought with no clear point yet. "
                "The scripture refuses to let us call cultural comfort wisdom when God calls us to transformation."
            ),
            relevance_score=0.7,
            reasoning="Selected because it attempts to bridge background into the Scripture claim.",
            hook_sentence="This is an interesting background thought with no clear point yet.",
            key_point="The sermon is moving from background into cultural transformation.",
            start_reason="Start where the speaker attempts to introduce the background idea.",
            end_reason="End after the transformation claim completes the setup thought.",
            moment_type="Scripture Explanation",
            why_selected="The span contains a transition into the Romans 12 transformation claim, but the opening is intentionally weak.",
            why_this_is_not_intro="It is not a welcome, but it still opens with generic setup language.",
            why_this_is_complete_thought="It transitions from background into the transformation claim.",
        )
        scripture = ai.TranscriptSegment(
            start_time="00:38",
            end_time="01:15",
            text=(
                "The scripture refuses to let us call cultural comfort wisdom when God calls us to transformation. "
                "Paul says do not be conformed to this world, but be transformed by the renewal of your mind."
            ),
            relevance_score=0.96,
            reasoning="Selected because it explains Romans 12 with a clear contrast between cultural comfort and transformation.",
            hook_sentence="The scripture refuses to let us call cultural comfort wisdom when God calls us to transformation.",
            key_point="Romans 12 requires transformation rather than calling cultural comfort wisdom.",
            start_reason="Start on the interpretive Scripture claim because it is direct and standalone.",
            end_reason="End after the Romans 12 command is quoted as the complete scriptural basis.",
            moment_type="Scripture Explanation",
            why_selected="The span gives a direct Scripture hook, names the cultural error, and quotes the transformation command.",
            why_this_is_not_intro="It opens with the biblical claim instead of setup language.",
            why_this_is_complete_thought="It states the claim and completes it with the Romans 12 command.",
        )
        application = ai.TranscriptSegment(
            start_time="01:15",
            end_time="01:55",
            text=(
                "Name the pressure that is shaping you before it becomes your pattern. "
                "If approval is discipling you, decide today what obedience will cost and take the first faithful step."
            ),
            relevance_score=0.98,
            reasoning="Selected because it gives a direct practical application with a concrete obedience step.",
            hook_sentence="Name the pressure that is shaping you before it becomes your pattern.",
            key_point="Identify the pressure shaping you and choose one costly faithful step today.",
            start_reason="Start on the direct imperative because it is immediately actionable and standalone.",
            end_reason="End after the concrete obedience step, completing the application.",
            moment_type="Practical Application",
            why_selected="The span gives an imperative, a specific pressure example, and a same-day obedience step.",
            why_this_is_not_intro="It starts with the action command rather than context setup.",
            why_this_is_complete_thought="It includes diagnosis, cost, and the first faithful action.",
        )
        incomplete = ai.TranscriptSegment(
            start_time="02:28",
            end_time="02:44",
            text="The real test is not whether you liked the sermon but whether you will obey when",
            relevance_score=0.9,
            reasoning="Selected because it challenges listeners about obedience.",
            hook_sentence="The real test is not whether you liked the sermon but whether you will obey when",
            key_point="The real test is obedience, not liking the sermon.",
            start_reason="Start on the direct heart-check.",
            end_reason="End at the obedience challenge.",
            moment_type="Repentance / Heart-Check",
            why_selected="The line challenges listeners about obedience after hearing the sermon.",
            why_this_is_not_intro="It is a heart-check, not setup.",
            why_this_is_complete_thought="It names the test of obedience.",
            rejection_risks=["ends mid-thought"],
        )
        duplicate = application.model_copy(update={"start_time": "02:44", "end_time": "03:20"})
        return SimpleNamespace(
            output=ai.TranscriptAnalysis(
                most_relevant_segments=[shifted_intro, weak_hook, scripture, application, incomplete, duplicate],
                summary="Romans 12 sermon fixture about resisting cultural conformity.",
                key_topics=["Romans 12", "conformity", "practical obedience"],
            )
        )


@pytest.mark.asyncio
async def test_clip_intelligence_acceptance_fixture_analysis_only(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "get_transcript_agent_candidates", lambda: [("fixture:model", FixtureAgent())])
    source_path = tmp_path / "fixture.mp4"
    source_path.write_bytes(b"not a real video; analysis-only uses cached transcript")
    monkeypatch.setattr(VideoService, "resolve_local_video_path", staticmethod(lambda _url: source_path))
    monkeypatch.setattr(VideoService, "_get_file_duration", staticmethod(lambda _path: 180.0))

    result = await VideoService.process_video_complete(
        url="upload://fixture.mp4",
        source_type="video_url",
        processing_mode="fast",
        output_format="original",
        add_subtitles=False,
        cached_transcript=SERMON_TRANSCRIPT,
        content_mode="sermon",
        selection_instructions="Fixture acceptance: enforce THIH Shorts Factory gate before rendering.",
        analysis_only=True,
    )

    review = result["candidate_review"]
    accepted = review["accepted_candidates"]
    rejected = review["rejected_candidates"]
    accepted_by_id = {candidate["candidate_id"]: candidate for candidate in accepted}
    rejected_reasons = " ".join(str(candidate.get("rejection_reason")) for candidate in rejected)

    assert result["analysis_only"] is True
    assert result["segments_to_render"] == []
    assert len(result["segments"]) < 5
    assert len(accepted) == 3
    assert len(rejected) == 3

    assert accepted_by_id["candidate-1"]["decision"] == "shifted"
    assert accepted_by_id["candidate-1"]["normalized_start"] == "00:06"
    assert "first 3 seconds" in rejected_reasons or "weak hook" in rejected_reasons or "weak setup" in rejected_reasons
    assert "mid-thought" in rejected_reasons
    assert "duplicate" in rejected_reasons

    for candidate in accepted:
        assert candidate["hook_sentence"]
        assert candidate["key_point"]
        assert candidate["start_reason"]
        assert candidate["end_reason"]
        assert candidate["why_selected"]
        assert candidate["transcript_evidence"]
        assert candidate["publishability_score"] > 0




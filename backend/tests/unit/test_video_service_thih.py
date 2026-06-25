from src.services.video_service import build_segment_json, deduplicate_clip_segments
from src.ai import TranscriptSegment, THIHAnalysis, ViralityAnalysis


def test_build_segment_json_preserves_legacy_and_thih_fields_from_model():
    segment = TranscriptSegment(
        start_time="00:00",
        end_time="00:35",
        text="Romans twelve gives a clear call to renewed work.",
        relevance_score=0.93,
        reasoning="Complete thought with payoff.",
        content_mode="devotional",
        virality=ViralityAnalysis(
            hook_score=20,
            engagement_score=18,
            value_score=21,
            shareability_score=17,
            total_score=0,
            hook_type="statement",
        ),
        thih=THIHAnalysis(
            opening_clarity=9,
            retention_strength=8,
            service_value=9,
            stewardship_usefulness=10,
            canon_fit=9,
            conviction=8,
            platform_readiness=7,
            message_integrity=10,
        ),
        recommended_title="Set Apart Without Arrogance",
        recommended_caption="Built on purpose. Driven by faith.",
        recommended_cta="Save this before the workday.",
        recommended_hashtags=["#THIH", "#Romans12"],
        platform_fit=["shorts", "reels"],
        scripture_reference="Romans 12:2",
        content_warning="Mentions pride.",
    )

    payload = build_segment_json(segment)

    assert payload["virality_score"] == 76
    assert payload["hook_score"] == 20
    assert payload["thih_score"] == 70
    assert payload["thih"]["message_integrity"] == 10
    assert payload["content_mode"] == "devotional"
    assert payload["recommended_title"] == "Set Apart Without Arrogance"
    assert payload["recommended_caption"] == "Built on purpose. Driven by faith."
    assert payload["recommended_cta"] == "Save this before the workday."
    assert payload["recommended_hashtags"] == ["#THIH", "#Romans12"]
    assert payload["platform_fit"] == ["shorts", "reels"]
    assert payload["scripture_reference"] == "Romans 12:2"
    assert payload["content_warning"] == "Mentions pride."


def test_build_segment_json_preserves_thih_fields_from_cached_dict():
    payload = build_segment_json(
        {
            "start_time": "00:00",
            "end_time": "00:30",
            "text": "A cached clip.",
            "relevance_score": 0.8,
            "reasoning": "Cached reasoning.",
            "virality": {"total_score": 65, "hook_score": 15},
            "thih": {"total_score": 72, "opening_clarity": 9},
            "content_mode": "podcast",
            "recommended_title": "Cached title",
            "recommended_caption": "Cached caption",
            "recommended_cta": "Cached CTA",
            "recommended_hashtags": ["#Cached"],
            "platform_fit": ["linkedin"],
            "scripture_reference": None,
            "content_warning": None,
        }
    )

    assert payload["virality_score"] == 65
    assert payload["hook_score"] == 15
    assert payload["thih_score"] == 72
    assert payload["thih"]["opening_clarity"] == 9
    assert payload["content_mode"] == "podcast"
    assert payload["recommended_title"] == "Cached title"

def test_deduplicate_clip_segments_removes_near_start_duplicates_and_keeps_best_score():
    segments = [
        {
            "start_time": "00:00",
            "end_time": "00:52",
            "text": "The same opening sermon moment about stewardship and obedience.",
            "relevance_score": 0.7,
            "thih_score": 62,
            "virality_score": 40,
        },
        {
            "start_time": "00:03",
            "end_time": "00:55",
            "text": "The same opening sermon moment about stewardship and obedience.",
            "relevance_score": 0.95,
            "thih_score": 80,
            "virality_score": 60,
        },
        {
            "start_time": "03:00",
            "end_time": "03:42",
            "text": "A different later moment about renewed thinking and service.",
            "relevance_score": 0.82,
            "thih_score": 74,
            "virality_score": 50,
        },
    ]

    unique = deduplicate_clip_segments(segments)

    assert [segment["start_time"] for segment in unique] == ["00:03", "03:00"]
    assert unique[0]["relevance_score"] == 0.95


def test_deduplicate_clip_segments_removes_heavy_overlap_even_with_different_text():
    segments = [
        {
            "start_time": "01:00",
            "end_time": "01:50",
            "text": "First phrasing of a clip candidate with strong context.",
            "relevance_score": 0.6,
            "thih_score": 60,
            "virality_score": 45,
        },
        {
            "start_time": "01:20",
            "end_time": "02:05",
            "text": "Another phrasing from the same overlapping sermon window.",
            "relevance_score": 0.9,
            "thih_score": 82,
            "virality_score": 70,
        },
        {
            "start_time": "04:00",
            "end_time": "04:40",
            "text": "A genuinely separate clip candidate from later in the video.",
            "relevance_score": 0.75,
            "thih_score": 70,
            "virality_score": 48,
        },
    ]

    unique = deduplicate_clip_segments(segments)

    assert [segment["start_time"] for segment in unique] == ["01:20", "04:00"]


def test_build_segment_json_persists_clip_intelligence_inside_thih_json():
    segment = TranscriptSegment(
        start_time="00:18",
        end_time="00:42",
        text="The clearest proof of transformation is what you stop copying. That is where faithful work begins.",
        relevance_score=0.94,
        reasoning="Selected because the transcript gives a concrete transformation claim and faithful work payoff.",
        hook_sentence="The clearest proof of transformation is what you stop copying.",
        key_point="Transformation is shown by what you refuse to copy.",
        start_reason="Start on the first standalone hook sentence.",
        end_reason="End after the faithful work payoff.",
        moment_type="Strong Opening Conviction",
        why_selected="The span has a direct hook, specific key point, and complete payoff.",
        why_this_is_not_intro="It starts with the core transformation claim, not setup.",
        why_this_is_complete_thought="It states the principle and lands the application.",
        rejection_risks=["none"],
        hook_score_breakdown={"directness": 2, "tension": 2},
        ending_score_breakdown={"complete_thought": 2},
        clip_intelligence={"intro_shifted": True, "raw_start_time": "00:00"},
    )

    payload = build_segment_json(segment)

    assert payload["thih"]["hook_sentence"] == "The clearest proof of transformation is what you stop copying."
    assert payload["thih"]["key_point"] == "Transformation is shown by what you refuse to copy."
    assert payload["thih"]["moment_type"] == "Strong Opening Conviction"
    assert payload["thih"]["clip_intelligence"]["intro_shifted"] is True
    assert payload["thih"]["hook_score_breakdown"]["directness"] == 2

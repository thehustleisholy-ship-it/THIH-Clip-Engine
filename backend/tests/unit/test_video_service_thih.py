from src.services.video_service import build_segment_json
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
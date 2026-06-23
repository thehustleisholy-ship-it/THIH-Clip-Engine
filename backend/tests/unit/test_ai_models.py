from src.ai import TranscriptAnalysis


def test_transcript_segment_accepts_minimal_local_llm_shape():
    analysis = TranscriptAnalysis.model_validate(
        {
            "most_relevant_segments": [
                {
                    "start_time": "00:00",
                    "end_time": "00:15",
                    "segment": "This is a standalone clip candidate from a local model.",
                }
            ],
            "summary": "A short summary.",
            "key_topics": ["local model output"],
        }
    )

    segment = analysis.most_relevant_segments[0]

    assert segment.text == "This is a standalone clip candidate from a local model."
    assert segment.relevance_score == 0.75
    assert segment.reasoning == "Selected by the AI model as a clip candidate."
    assert segment.virality.total_score == 60


def test_transcript_analysis_accepts_local_llm_broll_shape():
    analysis = TranscriptAnalysis.model_validate(
        {
            "most_relevant_segments": [
                {
                    "start_time": "00:00",
                    "end_time": "00:15",
                    "text": "This clip has enough words to pass the text validation.",
                }
            ],
            "summary": "A short summary.",
            "key_topics": ["local model output"],
            "broll_opportunities": [
                {
                    "segment_start_time": "00:00",
                    "segment_end_time": "00:15",
                    "broll": ["programming tutorial channels", "AI comparison graphic"],
                }
            ],
        }
    )

    broll = analysis.broll_opportunities[0]

    assert broll.timestamp == "00:00"
    assert broll.duration == 3.0
    assert broll.search_term == "programming tutorial channels, AI comparison graphic"


def test_transcript_segment_adds_default_thih_scoring_and_metadata():
    analysis = TranscriptAnalysis.model_validate(
        {
            "most_relevant_segments": [
                {
                    "start_time": "00:00",
                    "end_time": "00:25",
                    "text": "Be transformed by renewing your mind in the middle of real work.",
                }
            ],
            "summary": "A short summary.",
            "key_topics": ["renewal"],
        }
    )

    segment = analysis.most_relevant_segments[0]

    assert segment.content_mode == "thih_systems"
    assert segment.thih.total_score == 64
    assert segment.thih.opening_clarity == 8
    assert segment.thih.message_integrity == 8
    assert segment.recommended_title == "Be transformed by renewing your mind in the middle of real work."
    assert segment.recommended_caption == "Be transformed by renewing your mind in the middle of real work."
    assert segment.recommended_cta == "Reflect, save, and steward the next step well."
    assert segment.recommended_hashtags == ["#THIH", "#TheHustleIsHoly", "#ClipEngine"]
    assert segment.platform_fit == ["shorts", "reels", "tiktok"]
    assert segment.scripture_reference is None
    assert segment.content_warning is None


def test_transcript_segment_accepts_explicit_thih_scoring_metadata_and_content_mode():
    segment = TranscriptAnalysis.model_validate(
        {
            "most_relevant_segments": [
                {
                    "start_time": "00:00",
                    "end_time": "00:30",
                    "text": "Romans twelve says do not conform, and the clip explains faithful work.",
                    "content_mode": "sermon",
                    "thih": {
                        "opening_clarity": 9,
                        "retention_strength": 7,
                        "service_value": 8,
                        "stewardship_usefulness": 10,
                        "canon_fit": 9,
                        "conviction": 8,
                        "platform_readiness": 7,
                        "message_integrity": 10,
                        "total_score": 1,
                        "reasoning": "Faithful, clear, and useful.",
                    },
                    "recommended_title": "Set Apart Without Arrogance",
                    "recommended_caption": "The work is holy when stewarded well.",
                    "recommended_cta": "Save this for Monday morning.",
                    "recommended_hashtags": ["THIH", "Romans12", "FaithAndWork"],
                    "platform_fit": ["shorts", "linkedin"],
                    "scripture_reference": "Romans 12:2",
                    "content_warning": "Mentions pride.",
                }
            ],
            "summary": "A short summary.",
            "key_topics": ["faith and work"],
        }
    ).most_relevant_segments[0]

    assert segment.content_mode == "sermon"
    assert segment.thih.total_score == 68
    assert segment.thih.reasoning == "Faithful, clear, and useful."
    assert segment.recommended_hashtags == ["#THIH", "#Romans12", "#FaithAndWork"]
    assert segment.platform_fit == ["shorts", "linkedin"]
    assert segment.scripture_reference == "Romans 12:2"
    assert segment.content_warning == "Mentions pride."
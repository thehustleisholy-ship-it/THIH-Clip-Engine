ALTER TABLE generated_clips
    ADD COLUMN IF NOT EXISTS thih_score INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS thih_json TEXT,
    ADD COLUMN IF NOT EXISTS content_mode VARCHAR(50),
    ADD COLUMN IF NOT EXISTS recommended_title TEXT,
    ADD COLUMN IF NOT EXISTS recommended_caption TEXT,
    ADD COLUMN IF NOT EXISTS recommended_cta TEXT,
    ADD COLUMN IF NOT EXISTS recommended_hashtags_json TEXT,
    ADD COLUMN IF NOT EXISTS platform_fit_json TEXT,
    ADD COLUMN IF NOT EXISTS scripture_reference VARCHAR(255),
    ADD COLUMN IF NOT EXISTS content_warning TEXT;

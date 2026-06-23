"""
Clip repository - handles all database operations for generated clips.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text as sa_text
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


def _decode_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _row_value(row: Any, name: str, default: Any = None) -> Any:
    return getattr(row, name, default)


def _clip_thih_fields(row: Any) -> Dict[str, Any]:
    return {
        "thih_score": _row_value(row, "thih_score", 0) or 0,
        "thih": _decode_json(_row_value(row, "thih_json"), {}),
        "content_mode": _row_value(row, "content_mode"),
        "recommended_title": _row_value(row, "recommended_title"),
        "recommended_caption": _row_value(row, "recommended_caption"),
        "recommended_cta": _row_value(row, "recommended_cta"),
        "recommended_hashtags": _decode_json(_row_value(row, "recommended_hashtags_json"), []),
        "platform_fit": _decode_json(_row_value(row, "platform_fit_json"), []),
        "scripture_reference": _row_value(row, "scripture_reference"),
        "content_warning": _row_value(row, "content_warning"),
    }


class ClipRepository:
    """Repository for clip-related database operations."""

    @staticmethod
    async def create_clip(
        db: AsyncSession,
        task_id: str,
        filename: str,
        file_path: str,
        start_time: str,
        end_time: str,
        duration: float,
        text: str,
        relevance_score: float,
        reasoning: str,
        clip_order: int,
        virality_score: int = 0,
        hook_score: int = 0,
        engagement_score: int = 0,
        value_score: int = 0,
        shareability_score: int = 0,
        hook_type: Optional[str] = None,
        thih_score: int = 0,
        thih: Optional[Dict[str, Any]] = None,
        content_mode: Optional[str] = None,
        recommended_title: Optional[str] = None,
        recommended_caption: Optional[str] = None,
        recommended_cta: Optional[str] = None,
        recommended_hashtags: Optional[List[str]] = None,
        platform_fit: Optional[List[str]] = None,
        scripture_reference: Optional[str] = None,
        content_warning: Optional[str] = None,
    ) -> str:
        """Create a new clip record and return its ID."""
        try:
            result = await db.execute(
                sa_text("""
                    INSERT INTO generated_clips
                    (task_id, filename, file_path, start_time, end_time, duration,
                     text, relevance_score, reasoning, clip_order,
                     virality_score, hook_score, engagement_score, value_score, shareability_score, hook_type,
                     thih_score, thih_json, content_mode, recommended_title, recommended_caption, recommended_cta,
                     recommended_hashtags_json, platform_fit_json, scripture_reference, content_warning,
                     created_at)
                    VALUES
                    (:task_id, :filename, :file_path, :start_time, :end_time, :duration,
                     :text, :relevance_score, :reasoning, :clip_order,
                     :virality_score, :hook_score, :engagement_score, :value_score, :shareability_score, :hook_type,
                     :thih_score, :thih_json, :content_mode, :recommended_title, :recommended_caption, :recommended_cta,
                     :recommended_hashtags_json, :platform_fit_json, :scripture_reference, :content_warning,
                     NOW())
                    RETURNING id
                """),
                {
                    "task_id": task_id,
                    "filename": filename,
                    "file_path": file_path,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "text": text,
                    "relevance_score": relevance_score,
                    "reasoning": reasoning,
                    "clip_order": clip_order,
                    "virality_score": virality_score,
                    "hook_score": hook_score,
                    "engagement_score": engagement_score,
                    "value_score": value_score,
                    "shareability_score": shareability_score,
                    "hook_type": hook_type,
                    "thih_score": thih_score,
                    "thih_json": json.dumps(thih or {}),
                    "content_mode": content_mode,
                    "recommended_title": recommended_title,
                    "recommended_caption": recommended_caption,
                    "recommended_cta": recommended_cta,
                    "recommended_hashtags_json": json.dumps(recommended_hashtags or []),
                    "platform_fit_json": json.dumps(platform_fit or []),
                    "scripture_reference": scripture_reference,
                    "content_warning": content_warning,
                },
            )
        except Exception:
            await db.rollback()
            result = await db.execute(
                sa_text("""
                    INSERT INTO generated_clips
                    (task_id, filename, file_path, start_time, end_time, duration,
                     text, relevance_score, reasoning, clip_order, created_at)
                    VALUES
                    (:task_id, :filename, :file_path, :start_time, :end_time, :duration,
                     :text, :relevance_score, :reasoning, :clip_order, NOW())
                    RETURNING id
                """),
                {
                    "task_id": task_id,
                    "filename": filename,
                    "file_path": file_path,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "text": text,
                    "relevance_score": relevance_score,
                    "reasoning": reasoning,
                    "clip_order": clip_order,
                },
            )
        clip_id = result.scalar()
        if not clip_id:
            raise RuntimeError("Failed to create clip: no ID returned")
        logger.debug(f"Created clip {clip_id} for task {task_id}")
        return str(clip_id)

    @staticmethod
    async def get_clips_by_task(db: AsyncSession, task_id: str) -> List[Dict[str, Any]]:
        """Get all clips for a specific task, ordered by clip_order."""
        try:
            result = await db.execute(
                sa_text("""
                    SELECT id, filename, file_path, start_time, end_time, duration,
                           text, relevance_score, reasoning, clip_order, created_at,
                           virality_score, hook_score, engagement_score, value_score, shareability_score, hook_type,
                           thih_score, thih_json, content_mode, recommended_title, recommended_caption, recommended_cta,
                           recommended_hashtags_json, platform_fit_json, scripture_reference, content_warning
                    FROM generated_clips
                    WHERE task_id = :task_id
                    ORDER BY clip_order ASC
                """),
                {"task_id": task_id},
            )
        except Exception:
            await db.rollback()
            result = await db.execute(
                sa_text("""
                    SELECT id, filename, file_path, start_time, end_time, duration,
                           text, relevance_score, reasoning, clip_order, created_at
                    FROM generated_clips
                    WHERE task_id = :task_id
                    ORDER BY clip_order ASC
                """),
                {"task_id": task_id},
            )

        clips = []
        for row in result.fetchall():
            clips.append(
                {
                    "id": row.id,
                    "filename": row.filename,
                    "file_path": row.file_path,
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "duration": row.duration,
                    "text": row.text,
                    "relevance_score": row.relevance_score,
                    "reasoning": row.reasoning,
                    "clip_order": row.clip_order,
                    "created_at": row.created_at.isoformat(),
                    "video_url": f"/tasks/{task_id}/clips/{row.id}/file",
                    "virality_score": _row_value(row, "virality_score", 0) or 0,
                    "hook_score": _row_value(row, "hook_score", 0) or 0,
                    "engagement_score": _row_value(row, "engagement_score", 0) or 0,
                    "value_score": _row_value(row, "value_score", 0) or 0,
                    "shareability_score": _row_value(row, "shareability_score", 0) or 0,
                    "hook_type": _row_value(row, "hook_type"),
                    **_clip_thih_fields(row),
                }
            )

        return clips

    @staticmethod
    async def get_clips_count(db: AsyncSession, task_id: str) -> int:
        """Get the count of clips for a task."""
        result = await db.execute(
            sa_text(
                "SELECT COUNT(*) as count FROM generated_clips WHERE task_id = :task_id"
            ),
            {"task_id": task_id},
        )
        return result.scalar()

    @staticmethod
    async def delete_clips_by_task(db: AsyncSession, task_id: str) -> int:
        """Delete all clips for a task. Returns count of deleted clips."""
        result = await db.execute(
            sa_text("DELETE FROM generated_clips WHERE task_id = :task_id"),
            {"task_id": task_id},
        )
        await db.commit()
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} clips for task {task_id}")
        return deleted_count

    @staticmethod
    async def delete_clip(db: AsyncSession, clip_id: str) -> None:
        """Delete a single clip by ID."""
        await db.execute(
            sa_text("DELETE FROM generated_clips WHERE id = :clip_id"),
            {"clip_id": clip_id},
        )
        await db.commit()
        logger.info(f"Deleted clip {clip_id}")

    @staticmethod
    async def get_clip_by_id(
        db: AsyncSession, clip_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get one clip by ID."""
        try:
            result = await db.execute(
                sa_text(
                    """
                    SELECT id, task_id, filename, file_path, start_time, end_time, duration,
                           text, relevance_score, reasoning, clip_order,
                           virality_score, hook_score, engagement_score, value_score, shareability_score, hook_type,
                           thih_score, thih_json, content_mode, recommended_title, recommended_caption, recommended_cta,
                           recommended_hashtags_json, platform_fit_json, scripture_reference, content_warning,
                           created_at
                    FROM generated_clips
                    WHERE id = :clip_id
                    """
                ),
                {"clip_id": clip_id},
            )
        except Exception:
            await db.rollback()
            result = await db.execute(
                sa_text(
                    """
                    SELECT id, task_id, filename, file_path, start_time, end_time, duration,
                           text, relevance_score, reasoning, clip_order, created_at
                    FROM generated_clips
                    WHERE id = :clip_id
                    """
                ),
                {"clip_id": clip_id},
            )
        row = result.fetchone()
        if not row:
            return None

        return {
            "id": row.id,
            "task_id": row.task_id,
            "filename": row.filename,
            "file_path": row.file_path,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "duration": row.duration,
            "text": row.text,
            "relevance_score": row.relevance_score,
            "reasoning": row.reasoning,
            "clip_order": row.clip_order,
            "virality_score": _row_value(row, "virality_score", 0) or 0,
            "hook_score": _row_value(row, "hook_score", 0) or 0,
            "engagement_score": _row_value(row, "engagement_score", 0) or 0,
            "value_score": _row_value(row, "value_score", 0) or 0,
            "shareability_score": _row_value(row, "shareability_score", 0) or 0,
            "hook_type": _row_value(row, "hook_type"),
            "created_at": row.created_at.isoformat(),
            "video_url": f"/tasks/{row.task_id}/clips/{row.id}/file",
            **_clip_thih_fields(row),
        }

    @staticmethod
    async def update_clip(
        db: AsyncSession,
        clip_id: str,
        filename: str,
        file_path: str,
        start_time: str,
        end_time: str,
        duration: float,
        text: str,
    ) -> None:
        """Update core clip metadata and file path."""
        await db.execute(
            sa_text(
                """
                UPDATE generated_clips
                SET filename = :filename,
                    file_path = :file_path,
                    start_time = :start_time,
                    end_time = :end_time,
                    duration = :duration,
                    text = :text,
                    updated_at = NOW()
                WHERE id = :clip_id
                """
            ),
            {
                "clip_id": clip_id,
                "filename": filename,
                "file_path": file_path,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "text": text,
            },
        )
        await db.commit()

    @staticmethod
    async def reorder_task_clips(db: AsyncSession, task_id: str) -> None:
        """Normalize clip_order sequence after edits."""
        result = await db.execute(
            sa_text(
                "SELECT id FROM generated_clips WHERE task_id = :task_id ORDER BY clip_order ASC, created_at ASC"
            ),
            {"task_id": task_id},
        )
        clip_ids = [row.id for row in result.fetchall()]
        for idx, cid in enumerate(clip_ids, start=1):
            await db.execute(
                sa_text(
                    "UPDATE generated_clips SET clip_order = :clip_order, updated_at = NOW() WHERE id = :clip_id"
                ),
                {"clip_order": idx, "clip_id": cid},
            )
        await db.commit()



"""
Echoes Data Pipeline — SQLite Staging Store

The SQLite database serves as the checkpoint system for the entire pipeline.
Every scraped item gets a row with a ``status`` field tracking its progress
through: raw → heuristic_pass → classified_retrospective → tagged → indexed.

If the pipeline crashes at any stage, restarting picks up where it left off
by querying items that haven't yet reached the next status.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from config.logging_config import get_logger
from storage.models import (
    ClassificationResult,
    PipelineStatus,
    ScrapedItem,
    StoryMetadata,
)

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# SQL Statements
# ──────────────────────────────────────────────

CREATE_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL DEFAULT 'reddit',
    subreddit       TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    reddit_id       TEXT NOT NULL,
    author_hash     TEXT NOT NULL,
    title           TEXT,
    text            TEXT NOT NULL,
    content_hash    TEXT NOT NULL UNIQUE,
    score           INTEGER DEFAULT 0,
    url             TEXT,
    parent_id       TEXT,
    parent_title    TEXT,
    created_utc     TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'raw',
    heuristic_score REAL,
    classification  TEXT,
    classification_raw TEXT,
    -- Metadata fields (populated by tagger)
    decision_type       TEXT,
    decision_subcategory TEXT,
    outcome_sentiment   TEXT,
    time_elapsed_months INTEGER,
    emotional_richness  INTEGER,
    outcome_clarity     INTEGER,
    key_themes          TEXT,  -- JSON array stored as text
    hindsight_insight   TEXT,
    -- Tracking
    updated_at      TEXT
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_content_hash ON items(content_hash);
CREATE INDEX IF NOT EXISTS idx_items_subreddit ON items(subreddit);
CREATE INDEX IF NOT EXISTS idx_items_reddit_id ON items(reddit_id);
"""

CREATE_SCRAPE_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS scrape_state (
    subreddit   TEXT NOT NULL,
    query       TEXT NOT NULL,
    last_scraped_utc TEXT,
    items_scraped    INTEGER DEFAULT 0,
    PRIMARY KEY (subreddit, query)
);
"""


class SQLiteStore:
    """SQLite-based staging storage for the Echoes pipeline.

    Handles CRUD operations, deduplication checks, status transitions,
    and scrape-state tracking for incremental runs.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Connection management ──

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection with WAL mode and row_factory set."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._connection() as conn:
            conn.executescript(CREATE_ITEMS_TABLE)
            conn.executescript(CREATE_INDEXES)
            conn.executescript(CREATE_SCRAPE_STATE_TABLE)
        logger.info("SQLite database initialized at %s", self.db_path)

    # ── Deduplication ──

    def content_hash_exists(self, content_hash: str) -> bool:
        """Check if a content hash already exists in the database.

        Args:
            content_hash: SHA-256 hash of the normalized text.

        Returns:
            True if the hash is already stored.
        """
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM items WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return row is not None

    def bulk_check_hashes(self, hashes: list[str]) -> set[str]:
        """Return the subset of hashes that already exist in the DB.

        Args:
            hashes: List of content hashes to check.

        Returns:
            Set of hashes that are already stored.
        """
        if not hashes:
            return set()
        with self._connection() as conn:
            placeholders = ",".join("?" for _ in hashes)
            rows = conn.execute(
                f"SELECT content_hash FROM items WHERE content_hash IN ({placeholders})",
                hashes,
            ).fetchall()
            return {row["content_hash"] for row in rows}

    # ── Insert ──

    def insert_item(self, item: ScrapedItem) -> bool:
        """Insert a scraped item into the database.

        Uses INSERT OR IGNORE to silently skip duplicates (on content_hash).

        Args:
            item: The scraped item to store.

        Returns:
            True if the item was inserted, False if it was a duplicate.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO items
                    (id, source, subreddit, content_type, reddit_id, author_hash,
                     title, text, content_hash, score, url, parent_id, parent_title,
                     created_utc, scraped_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.source,
                    item.subreddit,
                    item.content_type.value,
                    item.reddit_id,
                    item.author_hash,
                    item.title,
                    item.text,
                    item.content_hash,
                    item.score,
                    item.url,
                    item.parent_id,
                    item.parent_title,
                    item.created_utc.isoformat(),
                    item.scraped_at.isoformat(),
                    item.status.value,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return cursor.rowcount > 0

    def insert_items_bulk(self, items: list[ScrapedItem]) -> tuple[int, int]:
        """Insert multiple items in a single transaction.

        Args:
            items: List of scraped items.

        Returns:
            Tuple of (inserted_count, duplicate_count).
        """
        inserted = 0
        duplicates = 0
        with self._connection() as conn:
            for item in items:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO items
                        (id, source, subreddit, content_type, reddit_id, author_hash,
                         title, text, content_hash, score, url, parent_id, parent_title,
                         created_utc, scraped_at, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.source,
                        item.subreddit,
                        item.content_type.value,
                        item.reddit_id,
                        item.author_hash,
                        item.title,
                        item.text,
                        item.content_hash,
                        item.score,
                        item.url,
                        item.parent_id,
                        item.parent_title,
                        item.created_utc.isoformat(),
                        item.scraped_at.isoformat(),
                        item.status.value,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    duplicates += 1
        return inserted, duplicates

    # ── Query by status ──

    def get_items_by_status(
        self,
        status: PipelineStatus,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Retrieve items with a specific pipeline status.

        Args:
            status: The status to filter by.
            limit: Maximum number of items to return (None = all).

        Returns:
            List of row dicts.
        """
        query = "SELECT * FROM items WHERE status = ? ORDER BY scraped_at ASC"
        params: list = [status.value]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_by_status(self) -> dict[str, int]:
        """Return a count of items grouped by status.

        Returns:
            Dict mapping status string to count.
        """
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM items GROUP BY status"
            ).fetchall()
            return {row["status"]: row["cnt"] for row in rows}

    # ── Status updates ──

    def update_status(
        self,
        item_id: str,
        status: PipelineStatus,
        **extra_fields,
    ) -> None:
        """Update the status of a single item, with optional extra fields.

        Args:
            item_id: The item's UUID.
            status: New pipeline status.
            **extra_fields: Additional column=value pairs to set.
        """
        sets = ["status = ?", "updated_at = ?"]
        params: list = [status.value, datetime.now(timezone.utc).isoformat()]

        for col, val in extra_fields.items():
            sets.append(f"{col} = ?")
            if isinstance(val, (list, dict)):
                params.append(json.dumps(val))
            else:
                params.append(val)

        params.append(item_id)
        sql = f"UPDATE items SET {', '.join(sets)} WHERE id = ?"

        with self._connection() as conn:
            conn.execute(sql, params)

    def update_heuristic_result(
        self, item_id: str, passed: bool, score: float
    ) -> None:
        """Record the result of heuristic filtering.

        Args:
            item_id: The item's UUID.
            passed: Whether the item passed the heuristic filter.
            score: The heuristic confidence score.
        """
        status = (
            PipelineStatus.HEURISTIC_PASS if passed
            else PipelineStatus.REJECTED_HEURISTIC
        )
        self.update_status(item_id, status, heuristic_score=score)

    def update_classification(
        self,
        item_id: str,
        result: ClassificationResult,
        raw_response: Optional[str] = None,
    ) -> None:
        """Record the LLM classification result.

        Args:
            item_id: The item's UUID.
            result: Classification category.
            raw_response: Raw LLM response string for debugging.
        """
        status_map = {
            ClassificationResult.RETROSPECTIVE: PipelineStatus.CLASSIFIED_RETROSPECTIVE,
            ClassificationResult.NOT_RETROSPECTIVE: PipelineStatus.REJECTED_LLM,
            ClassificationResult.AMBIGUOUS: PipelineStatus.NEEDS_REVIEW,
        }
        self.update_status(
            item_id,
            status_map[result],
            classification=result.value,
            classification_raw=raw_response,
        )

    def update_metadata(self, item_id: str, metadata: StoryMetadata) -> None:
        """Store extracted metadata and advance status to 'tagged'.

        Args:
            item_id: The item's UUID.
            metadata: Extracted story metadata.
        """
        self.update_status(
            item_id,
            PipelineStatus.TAGGED,
            decision_type=metadata.decision_type.value,
            decision_subcategory=metadata.decision_subcategory,
            outcome_sentiment=metadata.outcome_sentiment.value,
            time_elapsed_months=metadata.time_elapsed_months,
            emotional_richness=metadata.emotional_richness,
            outcome_clarity=1 if metadata.outcome_clarity else 0,
            key_themes=json.dumps(metadata.key_themes),
            hindsight_insight=metadata.hindsight_insight,
        )

    def mark_indexed(self, item_id: str) -> None:
        """Mark an item as indexed in the vector store.

        Args:
            item_id: The item's UUID.
        """
        self.update_status(item_id, PipelineStatus.INDEXED)

    def mark_failed(self, item_id: str) -> None:
        """Mark an item as failed.

        Args:
            item_id: The item's UUID.
        """
        self.update_status(item_id, PipelineStatus.FAILED)

    # ── Scrape state (for incremental runs) ──

    def get_last_scraped(self, subreddit: str, query: str) -> Optional[str]:
        """Get the last scraped UTC timestamp for a subreddit+query pair.

        Args:
            subreddit: The subreddit name.
            query: The search query string.

        Returns:
            ISO timestamp string or None if never scraped.
        """
        with self._connection() as conn:
            row = conn.execute(
                "SELECT last_scraped_utc FROM scrape_state WHERE subreddit = ? AND query = ?",
                (subreddit, query),
            ).fetchone()
            return row["last_scraped_utc"] if row else None

    def update_scrape_state(
        self, subreddit: str, query: str, last_utc: str, count: int
    ) -> None:
        """Update the scrape state after a successful scrape run.

        Args:
            subreddit: The subreddit name.
            query: The search query string.
            last_utc: ISO timestamp of the most recent item scraped.
            count: Number of items scraped in this run.
        """
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO scrape_state (subreddit, query, last_scraped_utc, items_scraped)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subreddit, query) DO UPDATE SET
                    last_scraped_utc = excluded.last_scraped_utc,
                    items_scraped = scrape_state.items_scraped + excluded.items_scraped
                """,
                (subreddit, query, last_utc, count),
            )

    # ── Statistics ──

    def get_total_count(self) -> int:
        """Return total number of items in the database."""
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM items").fetchone()
            return row["cnt"]

    def get_item_by_id(self, item_id: str) -> Optional[dict]:
        """Retrieve a single item by its UUID.

        Args:
            item_id: The item's UUID.

        Returns:
            Row dict or None.
        """
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
            return dict(row) if row else None

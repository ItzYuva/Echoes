"""
Tests for web archive search tool.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config.agent_config import AgentSettings
from agent.tools.search_utils import (
    extract_links_from_html,
    extract_story_text_from_html,
)
from agent.tools.web_search import WebSearchTool


# ── Content Extraction ─────────────────────────────────────────────

class TestExtractStoryText:
    def test_extracts_from_selector(self):
        html = """
        <html><body>
            <article class="story-content">
                <p>Five years ago I made a decision that changed everything.</p>
                <p>Looking back now, I realize how much I've grown since then.</p>
                <p>The fear was real but the outcome exceeded my expectations.</p>
            </article>
        </body></html>
        """
        text = extract_story_text_from_html(html, ".story-content", min_length=50)
        assert text is not None
        assert "Five years ago" in text
        assert "grown since then" in text

    def test_returns_none_for_short_content(self):
        html = "<html><body><p>Short.</p></body></html>"
        text = extract_story_text_from_html(html, "p", min_length=150)
        assert text is None

    def test_fallback_to_paragraphs(self):
        html = """
        <html><body>
            <p>This is a long enough paragraph that contains meaningful content about life decisions and retrospective reflections on choices made years ago.</p>
            <p>Another paragraph with more content about looking back on decisions.</p>
        </body></html>
        """
        text = extract_story_text_from_html(html, ".nonexistent", min_length=50)
        assert text is not None
        assert "long enough paragraph" in text

    def test_removes_script_and_style(self):
        html = """
        <html><body>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <p>This is the actual content about my decision to leave my career behind and start fresh, a choice I made five years ago.</p>
        </body></html>
        """
        text = extract_story_text_from_html(html, "p", min_length=50)
        assert text is not None
        assert "var x" not in text
        assert "color: red" not in text
        assert "actual content" in text


class TestExtractLinks:
    def test_extracts_absolute_links(self):
        html = '<html><body><a href="https://example.com/story1">Story</a></body></html>'
        links = extract_links_from_html(html, "a", "https://example.com")
        assert "https://example.com/story1" in links

    def test_resolves_relative_links(self):
        html = '<html><body><a href="/stories/123">Story</a></body></html>'
        links = extract_links_from_html(html, "a", "https://example.com")
        assert "https://example.com/stories/123" in links

    def test_skips_hash_links(self):
        html = '<html><body><a href="#section">Jump</a></body></html>'
        links = extract_links_from_html(html, "a", "https://example.com")
        assert len(links) == 0

    def test_skips_javascript_links(self):
        html = '<html><body><a href="javascript:void(0)">Click</a></body></html>'
        links = extract_links_from_html(html, "a", "https://example.com")
        assert len(links) == 0

    def test_deduplicates(self):
        html = """
        <html><body>
            <a href="/story1">Story</a>
            <a href="/story1">Same Story</a>
        </body></html>
        """
        links = extract_links_from_html(html, "a", "https://example.com")
        assert len(links) == 1


# ── Web Search Tool ────────────────────────────────────────────────

class TestWebSearchTool:
    def test_filter_sources_by_type(self):
        tool = WebSearchTool(AgentSettings())
        filtered = tool._filter_sources(["oral_history"])
        assert all(
            config.get("type") == "oral_history"
            for config in filtered.values()
        )

    def test_filter_sources_none_returns_all(self):
        tool = WebSearchTool(AgentSettings())
        filtered = tool._filter_sources(None)
        assert len(filtered) > 0

    def test_source_failure_tracking(self):
        tool = WebSearchTool(AgentSettings())
        tool.settings.source_failure_threshold = 3

        # Not disabled yet
        assert not tool._is_source_disabled("test_source")

        # Record failures
        tool._mark_source_failure("test_source")
        tool._mark_source_failure("test_source")
        assert not tool._is_source_disabled("test_source")

        tool._mark_source_failure("test_source")
        assert tool._is_source_disabled("test_source")

        # Success resets
        tool._mark_source_success("test_source")
        assert not tool._is_source_disabled("test_source")

    @pytest.mark.asyncio
    async def test_search_handles_source_failure(self):
        tool = WebSearchTool(AgentSettings())

        # Mock httpx to fail
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = ""
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await tool.search("test query", max_results=5)
            # Should return empty, not crash
            assert isinstance(results, list)

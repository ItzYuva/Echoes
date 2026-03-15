"""
Tests for Reddit live search tool.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config.agent_config import AgentSettings
from agent.tools.reddit_search import RedditSearchTool
from agent.tools.search_utils import build_reddit_search_queries, extract_key_terms


# ── Search Query Construction ──────────────────────────────────────

class TestExtractKeyTerms:
    def test_basic_extraction(self):
        terms = extract_key_terms("I'm thinking about leaving my job to start a business")
        assert "leaving" in terms
        assert "job" in terms
        assert "start" in terms
        assert "business" in terms

    def test_stop_words_removed(self):
        terms = extract_key_terms("I am going to the store")
        assert "going" in terms
        assert "store" in terms
        assert "the" not in terms
        assert "am" not in terms

    def test_empty_input(self):
        terms = extract_key_terms("")
        assert terms == []

    def test_deduplication(self):
        terms = extract_key_terms("career career career change")
        assert terms.count("career") == 1


class TestBuildRedditSearchQueries:
    def test_generates_queries(self):
        modifiers = ["looking back", "years later", "hindsight"]
        queries = build_reddit_search_queries(
            "leaving tenured professorship", modifiers, max_queries=3
        )
        assert len(queries) <= 3
        assert all(isinstance(q, str) for q in queries)

    def test_includes_retrospective_modifiers(self):
        modifiers = ["looking back", "years later"]
        queries = build_reddit_search_queries("career change", modifiers)
        assert any("looking back" in q for q in queries)

    def test_respects_max_queries(self):
        modifiers = ["a", "b", "c", "d", "e"]
        queries = build_reddit_search_queries("test query", modifiers, max_queries=2)
        assert len(queries) <= 2


# ── Reddit JSON Parsing ────────────────────────────────────────────

class TestRedditJsonParsing:
    def setup_method(self):
        self.tool = RedditSearchTool(AgentSettings())

    def test_parse_valid_response(self):
        data = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "I left my job 5 years ago",
                            "selftext": "Looking back, it was the best decision I ever made. " * 10,
                            "permalink": "/r/careerguidance/comments/abc123/test/",
                            "score": 42,
                            "created_utc": 1700000000,
                            "num_comments": 15,
                        }
                    }
                ]
            }
        }
        results = self.tool._parse_json_results(data, "careerguidance")
        assert len(results) == 1
        assert results[0]["reddit_id"] == "abc123"
        assert results[0]["source"] == "reddit_live"
        assert results[0]["subreddit"] == "r/careerguidance"
        assert results[0]["score"] == 42

    def test_skip_short_posts(self):
        data = {
            "data": {
                "children": [
                    {"data": {"id": "short1", "selftext": "too short", "title": ""}}
                ]
            }
        }
        results = self.tool._parse_json_results(data, "test")
        assert len(results) == 0

    def test_skip_deleted_posts(self):
        data = {
            "data": {
                "children": [
                    {"data": {"id": "del1", "selftext": "[removed]", "title": "test"}}
                ]
            }
        }
        results = self.tool._parse_json_results(data, "test")
        assert len(results) == 0

    def test_unexpected_structure(self):
        results = self.tool._parse_json_results({"unexpected": True}, "test")
        assert results == []

    def test_empty_children(self):
        data = {"data": {"children": []}}
        results = self.tool._parse_json_results(data, "test")
        assert results == []

    def test_combines_title_and_body(self):
        data = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "t1",
                            "title": "My career change story",
                            "selftext": "Five years ago I left my job. " * 20,
                            "permalink": "/r/test/t1/",
                            "score": 10,
                            "created_utc": 0,
                            "num_comments": 0,
                        }
                    }
                ]
            }
        }
        results = self.tool._parse_json_results(data, "test")
        assert "My career change story" in results[0]["text"]


# ── Rate Limiting ───────────────────────────────────────────────────

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_non_200_returns_empty(self):
        tool = RedditSearchTool(AgentSettings())

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await tool._search_json("test", "askreddit", "all")
            assert results == []

    @pytest.mark.asyncio
    async def test_429_returns_empty(self):
        tool = RedditSearchTool(AgentSettings())

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await tool._search_json("test", "askreddit", "all")
            assert results == []


# ── Subreddit Routing ───────────────────────────────────────────────

class TestSubredditRouting:
    def test_career_routing(self):
        tool = RedditSearchTool(AgentSettings())
        subs = tool.get_subreddits_for_decision("career")
        assert "careerguidance" in subs
        assert "ExperiencedDevs" in subs

    def test_relationship_routing(self):
        tool = RedditSearchTool(AgentSettings())
        subs = tool.get_subreddits_for_decision("relationship")
        assert "relationships" in subs

    def test_unknown_type_fallback(self):
        tool = RedditSearchTool(AgentSettings())
        subs = tool.get_subreddits_for_decision("unknown_type")
        assert "AskReddit" in subs

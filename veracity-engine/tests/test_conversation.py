"""
Unit tests for Conversation Management (STORY-020).

TDD Specifications:
1. Conversation Creation: Create conversation sessions with unique IDs
2. Query Addition: Add queries with results to conversations
3. Context Retrieval: Get recent queries for context-aware follow-ups
4. Conversation Listing: List all conversations with metadata
5. Context-Aware Queries: Build enhanced queries from conversation history
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestConversationCreation:
    """Tests for creating conversation sessions."""

    def test_create_conversation_returns_session_id(self):
        """Should create a conversation and return a valid session ID."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                session_id = mgr.create_conversation("test_project")

                # Should return a UUID
                assert session_id is not None
                assert len(session_id) == 36  # UUID format
                assert '-' in session_id

                # Should execute Cypher query
                mock_session.run.assert_called_once()
                call_args = mock_session.run.call_args
                assert "CREATE (c:Conversation" in call_args[0][0]
                assert call_args[1]["project_name"] == "test_project"

    def test_create_conversation_stores_metadata(self):
        """Should store conversation metadata in Neo4j."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                session_id = mgr.create_conversation("my_project")

                # Verify Cypher query includes required fields
                call_args = mock_session.run.call_args
                cypher = call_args[0][0]
                params = call_args[1]

                assert "id: $session_id" in cypher
                assert "project: $project_name" in cypher
                assert "started_at: $timestamp" in cypher
                assert params["project_name"] == "my_project"

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config


class TestQueryAddition:
    """Tests for adding queries to conversations."""

    def test_add_query_links_to_conversation(self):
        """Should add query and link it to conversation."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                results = self._mock_results()
                query_id = mgr.add_query_to_conversation(
                    "session-123",
                    "What are the main components?",
                    results
                )

                assert query_id is not None
                assert len(query_id) == 36  # UUID format

                # Should create query node and link it
                call_args = mock_session.run.call_args_list[0]
                cypher = call_args[0][0]
                params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
                assert "CREATE (q:Query" in cypher
                assert "CREATE (c)-[:HAD_QUERY]->(q)" in cypher
                assert params["query_text"] == "What are the main components?"
                assert params["session_id"] == "session-123"

    def test_add_query_links_evidence(self):
        """Should link query to evidence nodes."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                results = self._mock_results_with_evidence()
                mgr.add_query_to_conversation("session-123", "test query", results)

                # Should call run multiple times (query + evidence links)
                assert mock_session.run.call_count >= 2

                # Check evidence linking query
                evidence_calls = [c for c in mock_session.run.call_args_list[1:]
                                  if "RETURNED" in str(c)]
                assert len(evidence_calls) > 0

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config

    @staticmethod
    def _mock_results():
        """Create mock query results."""
        return {
            "context_veracity": {
                "confidence_score": 85.0
            },
            "code_truth": [],
            "doc_claims": []
        }

    @staticmethod
    def _mock_results_with_evidence():
        """Create mock query results with evidence."""
        return {
            "context_veracity": {
                "confidence_score": 85.0
            },
            "code_truth": [
                {"id": "node-1", "name": "Component1"},
                {"id": "node-2", "name": "Component2"}
            ],
            "doc_claims": []
        }


class TestContextRetrieval:
    """Tests for retrieving conversation context."""

    def test_get_conversation_context_returns_queries(self):
        """Should retrieve recent queries from conversation."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()

                # Mock query results
                mock_result.__iter__.return_value = [
                    {
                        "id": "query-1",
                        "text": "First query",
                        "timestamp": "2024-01-01T10:00:00",
                        "confidence_score": 85.0,
                        "evidence_count": 5
                    },
                    {
                        "id": "query-2",
                        "text": "Second query",
                        "timestamp": "2024-01-01T10:05:00",
                        "confidence_score": 90.0,
                        "evidence_count": 3
                    }
                ]

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                context = mgr.get_conversation_context("session-123", limit=5)

                # Should return queries in chronological order
                assert len(context) == 2
                assert context[0]["text"] == "Second query"  # Reversed to chronological
                assert context[1]["text"] == "First query"

    def test_get_conversation_context_respects_limit(self):
        """Should respect the limit parameter."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                mgr.get_conversation_context("session-123", limit=3)

                # Should pass limit to Cypher query
                call_args = mock_session.run.call_args
                assert call_args[1]["limit"] == 3

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config


class TestConversationMetadata:
    """Tests for conversation metadata operations."""

    def test_get_conversation_metadata_returns_info(self):
        """Should return conversation metadata."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()

                mock_result.single.return_value = {
                    "id": "session-123",
                    "project": "test_project",
                    "started_at": "2024-01-01T10:00:00",
                    "last_activity": "2024-01-01T11:00:00",
                    "query_count": 5
                }

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                metadata = mgr.get_conversation_metadata("session-123")

                assert metadata is not None
                assert metadata["id"] == "session-123"
                assert metadata["project"] == "test_project"
                assert metadata["query_count"] == 5

    def test_get_conversation_metadata_returns_none_if_not_found(self):
        """Should return None if conversation not found."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()

                mock_result.single.return_value = None

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                metadata = mgr.get_conversation_metadata("nonexistent")

                assert metadata is None

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config


class TestContextAwareQueries:
    """Tests for building context-aware queries."""

    def test_build_context_aware_query_includes_history(self):
        """Should include previous queries in context prefix."""
        from core.conversation import build_context_aware_query

        context = [
            {"text": "What are the main components?"},
            {"text": "How do they interact?"},
            {"text": "What are the dependencies?"}
        ]

        enhanced = build_context_aware_query("Are there any circular dependencies?", context)

        assert "Previous queries in this conversation:" in enhanced
        assert "What are the main components?" in enhanced
        assert "How do they interact?" in enhanced
        assert "What are the dependencies?" in enhanced
        assert "Current query: Are there any circular dependencies?" in enhanced

    def test_build_context_aware_query_limits_history(self):
        """Should only include last 3 queries in context."""
        from core.conversation import build_context_aware_query

        context = [
            {"text": "Query 1"},
            {"text": "Query 2"},
            {"text": "Query 3"},
            {"text": "Query 4"},
            {"text": "Query 5"}
        ]

        enhanced = build_context_aware_query("New query", context)

        # Should only include last 3
        assert "Query 3" in enhanced
        assert "Query 4" in enhanced
        assert "Query 5" in enhanced
        assert "Query 1" not in enhanced
        assert "Query 2" not in enhanced

    def test_build_context_aware_query_with_no_context(self):
        """Should return original query if no context."""
        from core.conversation import build_context_aware_query

        enhanced = build_context_aware_query("My query", [])
        assert enhanced == "My query"


class TestConversationListing:
    """Tests for listing conversations."""

    def test_list_conversations_returns_all(self):
        """Should list all conversations when no filter."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()

                mock_result.__iter__.return_value = [
                    {
                        "id": "session-1",
                        "project": "project1",
                        "started_at": "2024-01-01T10:00:00",
                        "last_activity": "2024-01-01T11:00:00",
                        "query_count": 3
                    },
                    {
                        "id": "session-2",
                        "project": "project2",
                        "started_at": "2024-01-02T10:00:00",
                        "last_activity": "2024-01-02T11:00:00",
                        "query_count": 5
                    }
                ]

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                conversations = mgr.list_conversations()

                assert len(conversations) == 2
                assert conversations[0]["id"] == "session-1"
                assert conversations[1]["id"] == "session-2"

    def test_list_conversations_filters_by_project(self):
        """Should filter conversations by project name."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()
                mock_result.__iter__.return_value = []

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                mgr.list_conversations("specific_project")

                # Should pass project filter to Cypher query
                call_args = mock_session.run.call_args
                cypher = call_args[0][0]
                params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
                assert "project: $project_name" in cypher
                assert params["project_name"] == "specific_project"

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config


class TestConversationDeletion:
    """Tests for deleting conversations."""

    def test_delete_conversation_removes_data(self):
        """Should delete conversation and associated queries."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()
                mock_result.single.return_value = {"deleted": 1}

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                deleted = mgr.delete_conversation("session-123")

                assert deleted is True

                # Should execute DETACH DELETE
                call_args = mock_session.run.call_args
                cypher = call_args[0][0]
                assert "DETACH DELETE" in cypher

    def test_delete_conversation_returns_false_if_not_found(self):
        """Should return False if conversation not found."""
        from core.conversation import ConversationManager

        with patch('core.conversation.get_config') as mock_config:
            mock_config.return_value = self._mock_config()

            with patch('core.conversation.GraphDatabase') as mock_db:
                mock_driver = MagicMock()
                mock_session = MagicMock()
                mock_result = MagicMock()
                mock_result.single.return_value = {"deleted": 0}

                mock_session.run.return_value = mock_result
                mock_db.driver.return_value = mock_driver
                mock_driver.session.return_value.__enter__.return_value = mock_session

                mgr = ConversationManager()
                deleted = mgr.delete_conversation("nonexistent")

                assert deleted is False

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config

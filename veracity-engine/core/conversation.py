"""
Conversation Management for Multi-Turn Queries (STORY-020).

This module provides conversation context storage in Neo4j for maintaining
query history and enabling context-aware follow-up questions.

Usage:
    from core.conversation import ConversationManager

    # Create a new conversation
    mgr = ConversationManager()
    session_id = mgr.create_conversation(project_name="myproject")

    # Add queries to conversation
    mgr.add_query_to_conversation(session_id, "What are the main components?", results)

    # Get conversation context for follow-up
    context = mgr.get_conversation_context(session_id, limit=5)
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from core.config import get_config, VeracityConfig

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation history in Neo4j.

    Stores conversations as a graph structure:
        (:Conversation {id, project, started_at})
          -[:HAD_QUERY]->(:Query {text, timestamp, query_id})
            -[:RETURNED]->(evidence nodes)

    This enables:
    - Multi-turn queries with context
    - Query history tracking
    - Evidence provenance
    """

    def __init__(self, config: Optional[VeracityConfig] = None):
        """
        Initialize conversation manager.

        Args:
            config: Optional configuration. Uses singleton if not provided.
        """
        self.config = config or get_config()
        self._driver: Optional[Any] = None

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            password = self.config.neo4j.password.get_secret_value()
            self._driver = GraphDatabase.driver(
                self.config.neo4j.uri,
                auth=(self.config.neo4j.user, password)
            )
        return self._driver

    def close(self):
        """Close Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def create_conversation(self, project_name: str) -> str:
        """
        Create a new conversation session.

        Args:
            project_name: Project this conversation belongs to

        Returns:
            session_id: Unique conversation identifier (UUID)
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        driver = self._get_driver()
        with driver.session() as session:
            session.run("""
                CREATE (c:Conversation {
                    id: $session_id,
                    project: $project_name,
                    started_at: $timestamp,
                    last_activity: $timestamp
                })
            """, session_id=session_id, project_name=project_name, timestamp=timestamp)

        logger.info(f"Created conversation {session_id} for project {project_name}")
        return session_id

    def add_query_to_conversation(
        self,
        session_id: str,
        query_text: str,
        results: Dict[str, Any]
    ) -> str:
        """
        Add a query and its results to a conversation.

        Args:
            session_id: Conversation session ID
            query_text: The query text
            results: Query results (evidence packet from ask_codebase.py)

        Returns:
            query_id: Unique query identifier (UUID)
        """
        query_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        driver = self._get_driver()
        with driver.session() as session:
            # Create query node and link to conversation
            confidence_score = results.get("context_veracity", {}).get("confidence_score", 0)
            session.run("""
                MATCH (c:Conversation {id: $session_id})
                CREATE (q:Query {
                    id: $query_id,
                    text: $query_text,
                    timestamp: $timestamp,
                    confidence_score: $confidence_score
                })
                CREATE (c)-[:HAD_QUERY]->(q)
                SET c.last_activity = $timestamp
            """, {
                "session_id": session_id,
                "query_id": query_id,
                "query_text": query_text,
                "timestamp": timestamp,
                "confidence_score": confidence_score
            })

            # Link query to evidence nodes (code_truth)
            code_evidence = results.get("code_truth", [])
            for evidence in code_evidence[:10]:  # Limit to top 10 evidence items
                evidence_id = evidence.get("id")
                if evidence_id:
                    try:
                        session.run("""
                            MATCH (q:Query {id: $query_id})
                            MATCH (n {uid: $evidence_id})
                            MERGE (q)-[:RETURNED]->(n)
                        """, query_id=query_id, evidence_id=evidence_id)
                    except Exception as e:
                        # Evidence node might not exist - log and continue
                        logger.debug(f"Could not link evidence {evidence_id}: {e}")

        logger.info(f"Added query {query_id} to conversation {session_id}")
        return query_id

    def get_conversation_context(
        self,
        session_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent queries from a conversation for context.

        Args:
            session_id: Conversation session ID
            limit: Maximum number of recent queries to return (default: 5)

        Returns:
            List of query dictionaries with:
                - id: Query ID
                - text: Query text
                - timestamp: When query was made
                - confidence_score: Veracity confidence
                - evidence_count: Number of evidence items returned
        """
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Conversation {id: $session_id})-[:HAD_QUERY]->(q:Query)
                OPTIONAL MATCH (q)-[:RETURNED]->(evidence)
                WITH q, count(evidence) as evidence_count
                RETURN q.id as id,
                       q.text as text,
                       q.timestamp as timestamp,
                       q.confidence_score as confidence_score,
                       evidence_count
                ORDER BY q.timestamp DESC
                LIMIT $limit
            """, session_id=session_id, limit=limit)

            queries = []
            for record in result:
                queries.append({
                    "id": record["id"],
                    "text": record["text"],
                    "timestamp": record["timestamp"],
                    "confidence_score": record["confidence_score"],
                    "evidence_count": record["evidence_count"]
                })

            # Reverse to get chronological order (oldest first)
            queries.reverse()

            logger.debug(f"Retrieved {len(queries)} queries from conversation {session_id}")
            return queries

    def get_conversation_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a conversation.

        Args:
            session_id: Conversation session ID

        Returns:
            Dictionary with conversation metadata, or None if not found:
                - id: Conversation ID
                - project: Project name
                - started_at: When conversation started
                - last_activity: Most recent query timestamp
                - query_count: Total number of queries
        """
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Conversation {id: $session_id})
                OPTIONAL MATCH (c)-[:HAD_QUERY]->(q:Query)
                WITH c, count(q) as query_count
                RETURN c.id as id,
                       c.project as project,
                       c.started_at as started_at,
                       c.last_activity as last_activity,
                       query_count
            """, session_id=session_id)

            record = result.single()
            if not record:
                return None

            return {
                "id": record["id"],
                "project": record["project"],
                "started_at": record["started_at"],
                "last_activity": record["last_activity"],
                "query_count": record["query_count"]
            }

    def list_conversations(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all conversations, optionally filtered by project.

        Args:
            project_name: Optional project filter

        Returns:
            List of conversation metadata dictionaries
        """
        driver = self._get_driver()
        with driver.session() as session:
            if project_name:
                query = """
                    MATCH (c:Conversation {project: $project_name})
                    OPTIONAL MATCH (c)-[:HAD_QUERY]->(q:Query)
                    WITH c, count(q) as query_count
                    RETURN c.id as id,
                           c.project as project,
                           c.started_at as started_at,
                           c.last_activity as last_activity,
                           query_count
                    ORDER BY c.last_activity DESC
                """
                params = {"project_name": project_name}
            else:
                query = """
                    MATCH (c:Conversation)
                    OPTIONAL MATCH (c)-[:HAD_QUERY]->(q:Query)
                    WITH c, count(q) as query_count
                    RETURN c.id as id,
                           c.project as project,
                           c.started_at as started_at,
                           c.last_activity as last_activity,
                           query_count
                    ORDER BY c.last_activity DESC
                """
                params = {}

            result = session.run(query, params)

            conversations = []
            for record in result:
                conversations.append({
                    "id": record["id"],
                    "project": record["project"],
                    "started_at": record["started_at"],
                    "last_activity": record["last_activity"],
                    "query_count": record["query_count"]
                })

            return conversations

    def delete_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation and all its queries.

        Args:
            session_id: Conversation session ID

        Returns:
            True if conversation was deleted, False if not found
        """
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Conversation {id: $session_id})
                OPTIONAL MATCH (c)-[:HAD_QUERY]->(q:Query)
                DETACH DELETE c, q
                RETURN count(c) as deleted
            """, session_id=session_id)

            record = result.single()
            deleted = record["deleted"] > 0

            if deleted:
                logger.info(f"Deleted conversation {session_id}")
            else:
                logger.warning(f"Conversation {session_id} not found for deletion")

            return deleted


def build_context_aware_query(
    original_query: str,
    conversation_context: List[Dict[str, Any]]
) -> str:
    """
    Build a context-aware query by incorporating conversation history.

    Args:
        original_query: The current user query
        conversation_context: Recent queries from get_conversation_context()

    Returns:
        Enhanced query string with context
    """
    if not conversation_context:
        return original_query

    # Extract recent query texts
    previous_queries = [q["text"] for q in conversation_context[-3:]]  # Last 3 queries

    # Build context prefix
    context_prefix = "Previous queries in this conversation:\n"
    for i, prev_query in enumerate(previous_queries, 1):
        context_prefix += f"{i}. {prev_query}\n"

    context_prefix += f"\nCurrent query: {original_query}"

    return context_prefix

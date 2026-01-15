"""
Query Metrics Tracking for Self-Learning System.

Stores and retrieves query performance metrics in Neo4j for ML-based tuning.
All metrics are stored deterministically with timestamp precision.

Node Schema:
    :QueryMetric {
        query_id: str (unique)
        project: str
        timestamp: datetime
        execution_time_ms: float
        result_count: int
        confidence_score: float
        vector_score_avg: float (optional)
        keyword_score_avg: float (optional)
        evidence_count: int
        user_feedback: str (optional: 'useful' | 'not_useful' | 'partial')
        feedback_timestamp: datetime (optional)
    }

Relationships:
    (:VeracityReport)-[:HAS_METRICS]->(:QueryMetric)
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, Session

from core.config import get_config

logger = logging.getLogger(__name__)


class QueryMetrics:
    """
    Query metrics tracking system.

    Stores query execution metrics in Neo4j for analysis and ML-based tuning.
    """

    def __init__(self, neo4j_uri: Optional[str] = None,
                 neo4j_user: Optional[str] = None,
                 neo4j_password: Optional[str] = None):
        """
        Initialize query metrics tracker.

        Args:
            neo4j_uri: Neo4j connection URI (optional, uses config if not provided)
            neo4j_user: Neo4j username (optional, uses config if not provided)
            neo4j_password: Neo4j password (optional, uses config if not provided)
        """
        config = get_config()

        self.neo4j_uri = neo4j_uri or config.neo4j.uri
        self.neo4j_user = neo4j_user or config.neo4j.user

        # Handle SecretStr from config
        if neo4j_password:
            self.neo4j_password = neo4j_password
        else:
            password = config.neo4j.password
            self.neo4j_password = password.get_secret_value() if hasattr(password, 'get_secret_value') else str(password)

        self.driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )

        # Create constraints on first init
        self._create_constraints()

    def _create_constraints(self) -> None:
        """Create Neo4j constraints for QueryMetric nodes."""
        with self.driver.session() as session:
            try:
                session.run("""
                    CREATE CONSTRAINT query_metric_id IF NOT EXISTS
                    FOR (m:QueryMetric)
                    REQUIRE m.query_id IS UNIQUE
                """)
                logger.debug("QueryMetric constraints created/verified")
            except Exception as e:
                logger.warning(f"Failed to create QueryMetric constraints: {e}")

    def track_query(
        self,
        query_id: str,
        project: str,
        execution_time_ms: float,
        result_count: int,
        confidence_score: float,
        vector_score_avg: Optional[float] = None,
        keyword_score_avg: Optional[float] = None,
        evidence_count: int = 0
    ) -> bool:
        """
        Record query execution metrics.

        Args:
            query_id: Unique query identifier (from VeracityReport)
            project: Project name
            execution_time_ms: Query execution time in milliseconds
            result_count: Number of results returned
            confidence_score: Veracity confidence score (0-100)
            vector_score_avg: Average vector similarity score (optional)
            keyword_score_avg: Average keyword match score (optional)
            evidence_count: Number of evidence items returned

        Returns:
            True if tracking successful, False otherwise
        """
        with self.driver.session() as session:
            try:
                result = session.run("""
                    MERGE (m:QueryMetric {query_id: $query_id})
                    SET m.project = $project,
                        m.timestamp = datetime($timestamp),
                        m.execution_time_ms = $execution_time_ms,
                        m.result_count = $result_count,
                        m.confidence_score = $confidence_score,
                        m.vector_score_avg = $vector_score_avg,
                        m.keyword_score_avg = $keyword_score_avg,
                        m.evidence_count = $evidence_count

                    // Link to VeracityReport if it exists
                    WITH m
                    OPTIONAL MATCH (r:VeracityReport {query_id: $query_id})
                    FOREACH (_ IN CASE WHEN r IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (r)-[:HAS_METRICS]->(m)
                    )

                    RETURN m.query_id as id
                """, {
                    "query_id": query_id,
                    "project": project,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": execution_time_ms,
                    "result_count": result_count,
                    "confidence_score": confidence_score,
                    "vector_score_avg": vector_score_avg,
                    "keyword_score_avg": keyword_score_avg,
                    "evidence_count": evidence_count
                })

                record = result.single()
                if record:
                    logger.info(f"Query metrics tracked: query_id={query_id}, confidence={confidence_score:.1f}%")
                    return True
                else:
                    logger.error(f"Failed to track metrics for query_id={query_id}")
                    return False

            except Exception as e:
                logger.error(f"Error tracking query metrics: {e}", exc_info=True)
                return False

    def update_feedback(self, query_id: str, rating: str) -> bool:
        """
        Update query metric with user feedback.

        This links the Feedback node to the QueryMetric for ML analysis.

        Args:
            query_id: Query identifier
            rating: User rating ('useful' | 'not_useful' | 'partial')

        Returns:
            True if update successful, False otherwise
        """
        with self.driver.session() as session:
            try:
                result = session.run("""
                    MATCH (m:QueryMetric {query_id: $query_id})
                    SET m.user_feedback = $rating,
                        m.feedback_timestamp = datetime($timestamp)
                    RETURN m.query_id as id
                """, {
                    "query_id": query_id,
                    "rating": rating,
                    "timestamp": datetime.now().isoformat()
                })

                record = result.single()
                if record:
                    logger.info(f"Feedback updated for query_id={query_id}, rating={rating}")
                    return True
                else:
                    logger.warning(f"QueryMetric not found for feedback update: query_id={query_id}")
                    return False

            except Exception as e:
                logger.error(f"Error updating feedback: {e}", exc_info=True)
                return False

    def get_metrics(
        self,
        time_window_hours: int = 24,
        project: Optional[str] = None,
        min_confidence: Optional[float] = None,
        has_feedback: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve query metrics within a time window.

        Args:
            time_window_hours: Number of hours to look back (default: 24)
            project: Filter by project name (optional)
            min_confidence: Minimum confidence score filter (optional)
            has_feedback: Filter for queries with/without feedback (optional)

        Returns:
            List of metric records as dictionaries
        """
        with self.driver.session() as session:
            try:
                # Build dynamic query based on filters
                filters = []
                if project:
                    filters.append("m.project = $project")
                if min_confidence is not None:
                    filters.append("m.confidence_score >= $min_confidence")
                if has_feedback is not None:
                    if has_feedback:
                        filters.append("m.user_feedback IS NOT NULL")
                    else:
                        filters.append("m.user_feedback IS NULL")

                where_clause = " AND ".join(filters) if filters else "true"

                query = f"""
                    MATCH (m:QueryMetric)
                    WHERE m.timestamp >= datetime($cutoff_time)
                      AND {where_clause}
                    RETURN m.query_id as query_id,
                           m.project as project,
                           m.timestamp as timestamp,
                           m.execution_time_ms as execution_time_ms,
                           m.result_count as result_count,
                           m.confidence_score as confidence_score,
                           m.vector_score_avg as vector_score_avg,
                           m.keyword_score_avg as keyword_score_avg,
                           m.evidence_count as evidence_count,
                           m.user_feedback as user_feedback,
                           m.feedback_timestamp as feedback_timestamp
                    ORDER BY m.timestamp DESC
                """

                cutoff = datetime.now() - timedelta(hours=time_window_hours)

                result = session.run(query, {
                    "cutoff_time": cutoff.isoformat(),
                    "project": project,
                    "min_confidence": min_confidence
                })

                metrics = []
                for record in result:
                    metric = dict(record)
                    # Convert Neo4j DateTime to ISO string
                    if metric.get('timestamp'):
                        metric['timestamp'] = str(metric['timestamp'])
                    if metric.get('feedback_timestamp'):
                        metric['feedback_timestamp'] = str(metric['feedback_timestamp'])
                    metrics.append(metric)

                logger.debug(f"Retrieved {len(metrics)} metrics (time_window={time_window_hours}h, project={project})")
                return metrics

            except Exception as e:
                logger.error(f"Error retrieving metrics: {e}", exc_info=True)
                return []

    def get_feedback_stats(self, time_window_hours: int = 24, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated feedback statistics.

        Args:
            time_window_hours: Number of hours to look back
            project: Filter by project name (optional)

        Returns:
            Dictionary with feedback statistics:
                - total_queries: Total number of queries
                - queries_with_feedback: Number of queries with feedback
                - useful_count: Number of 'useful' ratings
                - not_useful_count: Number of 'not_useful' ratings
                - partial_count: Number of 'partial' ratings
                - avg_confidence_useful: Average confidence for useful queries
                - avg_confidence_not_useful: Average confidence for not useful queries
        """
        with self.driver.session() as session:
            try:
                cutoff = datetime.now() - timedelta(hours=time_window_hours)

                project_filter = "AND m.project = $project" if project else ""

                result = session.run(f"""
                    MATCH (m:QueryMetric)
                    WHERE m.timestamp >= datetime($cutoff_time)
                      {project_filter}

                    RETURN
                        count(m) as total_queries,
                        count(m.user_feedback) as queries_with_feedback,
                        sum(CASE WHEN m.user_feedback = 'useful' THEN 1 ELSE 0 END) as useful_count,
                        sum(CASE WHEN m.user_feedback = 'not_useful' THEN 1 ELSE 0 END) as not_useful_count,
                        sum(CASE WHEN m.user_feedback = 'partial' THEN 1 ELSE 0 END) as partial_count,
                        avg(CASE WHEN m.user_feedback = 'useful' THEN m.confidence_score ELSE null END) as avg_confidence_useful,
                        avg(CASE WHEN m.user_feedback = 'not_useful' THEN m.confidence_score ELSE null END) as avg_confidence_not_useful
                """, {
                    "cutoff_time": cutoff.isoformat(),
                    "project": project
                })

                record = result.single()
                if record:
                    stats = dict(record)
                    # Convert None to 0 for counts
                    for key in ['total_queries', 'queries_with_feedback', 'useful_count', 'not_useful_count', 'partial_count']:
                        if stats[key] is None:
                            stats[key] = 0

                    logger.debug(f"Feedback stats: {stats['queries_with_feedback']}/{stats['total_queries']} with feedback")
                    return stats
                else:
                    return {
                        "total_queries": 0,
                        "queries_with_feedback": 0,
                        "useful_count": 0,
                        "not_useful_count": 0,
                        "partial_count": 0,
                        "avg_confidence_useful": None,
                        "avg_confidence_not_useful": None
                    }

            except Exception as e:
                logger.error(f"Error retrieving feedback stats: {e}", exc_info=True)
                return {}

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.debug("QueryMetrics driver closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

"""
Git Analyzer for Dev Context Tracking - STORY-010

Analyzes Git commits for semantic relationships to work items.
Provides confidence scoring for automatic commit-to-work-item linking.
"""

import re
import subprocess
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
import structlog

logger = structlog.get_logger(__name__)


class GitAnalysisError(Exception):
    """Raised when Git analysis operations fail"""
    pass


class GitAnalyzer:
    """
    Analyzes Git commits for semantic relationships to work items.

    Provides:
    - Semantic similarity analysis between commit messages and work item descriptions
    - Conventional commit type detection (feat, fix, chore, docs, etc.)
    - File change pattern analysis
    - Confidence scoring for automatic linking decisions
    """

    def __init__(self, git_repo_path: Optional[str] = None):
        """
        Initialize GitAnalyzer.

        Args:
            git_repo_path: Path to git repository (defaults to current working directory)
        """
        self.git_repo_path = git_repo_path or "."

        # Conventional commit type patterns
        self.CONVENTIONAL_COMMIT_PATTERN = re.compile(
            r'^(feat|fix|refactor|chore|docs|test|style|perf|ci|build)(\(.+\))?!?:\s*(.+)',
            re.IGNORECASE
        )

        # Work type mapping from conventional commits
        self.COMMIT_TYPE_MAPPING = {
            "feat": "feature",
            "fix": "bug",
            "refactor": "refactor",
            "chore": "chore",
            "docs": "docs",
            "test": "chore",
            "style": "chore",
            "perf": "enhancement",
            "ci": "chore",
            "build": "chore"
        }

        # Priority keywords
        self.PRIORITY_KEYWORDS = {
            "critical": ["critical", "urgent", "hotfix", "emergency"],
            "high": ["high", "important", "major", "bug", "fix", "error", "fail"],
            "medium": ["medium", "feature", "enhancement", "improve"],
            "low": ["low", "minor", "cleanup", "refactor", "style", "docs"]
        }

    def analyze_commit_work_relation(self, commit: Dict[str, Any],
                                   work_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze relationship between a commit and existing work items.

        Uses semantic similarity, conventional commit parsing, and file pattern analysis
        to determine the best work item match and confidence score.

        Args:
            commit: Commit dictionary with commit_hash, message, author, etc.
            work_items: List of existing work items to match against

        Returns:
            Analysis dictionary with:
            - confidence: float (0.0-1.0)
            - commit_type: string
            - reasons: list of match reasons
            - best_match: work item UID or None
            - semantic_scores: dict of UID -> score mappings
        """
        try:
            # Get full commit message from git if not provided
            commit_message = commit.get("message") or self._get_commit_message(commit["commit_hash"])

            # Parse conventional commit format
            commit_type, scope, description = self._parse_conventional_commit(commit_message)

            # Calculate semantic similarity scores for each work item
            semantic_scores = {}
            best_match = None
            best_score = 0.0
            reasons = []

            for work_item in work_items:
                score = self._calculate_semantic_similarity(
                    commit_message, description, work_item
                )
                semantic_scores[work_item["uid"]] = score

                if score > best_score:
                    best_score = score
                    best_match = work_item["uid"]

            # Boost confidence based on matching factors
            confidence_boost = 0.0

            # Conventional commit type match
            if commit_type and best_match:
                best_work_item = next(
                    (wi for wi in work_items if wi["uid"] == best_match), None
                )
                if best_work_item and self._work_types_match(commit_type, best_work_item.get("work_type")):
                    confidence_boost += 0.2
                    reasons.append(f"Commit type '{commit_type}' matches work type")

            # Exact keyword matches
            keyword_matches = self._find_keyword_matches(commit_message, work_items)
            if keyword_matches:
                confidence_boost += min(0.3, len(keyword_matches) * 0.1)
                reasons.extend([f"Keyword match: {kw}" for kw in keyword_matches[:3]])

            # Priority keyword alignment
            commit_priority = self._infer_priority_from_message(commit_message)
            if best_match:
                best_work_item = next(
                    (wi for wi in work_items if wi["uid"] == best_match), None
                )
                if best_work_item and commit_priority == best_work_item.get("priority"):
                    confidence_boost += 0.1
                    reasons.append(f"Priority alignment: {commit_priority}")

            # Final confidence calculation
            final_confidence = min(1.0, best_score + confidence_boost)

            # Add base reasoning
            if best_score > 0.6:
                reasons.insert(0, f"High semantic similarity ({best_score:.2f})")
            elif best_score > 0.3:
                reasons.insert(0, f"Moderate semantic similarity ({best_score:.2f})")
            else:
                reasons.insert(0, f"Low semantic similarity ({best_score:.2f})")

            # Add commit type to reasons
            if commit_type:
                reasons.append(f"Conventional commit type: {commit_type}")

            return {
                "confidence": round(final_confidence, 3),
                "commit_type": commit_type or "unknown",
                "scope": scope,
                "description": description,
                "reasons": reasons,
                "best_match": best_match if final_confidence > 0.1 else None,
                "semantic_scores": semantic_scores,
                "raw_similarity": best_score,
                "confidence_boost": confidence_boost
            }

        except Exception as e:
            logger.error(f"Failed to analyze commit {commit.get('commit_hash', 'unknown')}: {e}")
            raise GitAnalysisError(f"Commit analysis failed: {str(e)}")

    def _get_commit_message(self, commit_hash: str) -> str:
        """Get full commit message from git repository."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B", commit_hash],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get commit message for {commit_hash}: {e}")
            return ""

    def _parse_conventional_commit(self, message: str) -> tuple[Optional[str], Optional[str], str]:
        """
        Parse conventional commit message format.

        Returns:
            (commit_type, scope, description) tuple
        """
        match = self.CONVENTIONAL_COMMIT_PATTERN.match(message)
        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2).strip("()") if match.group(2) else None
            description = match.group(3).strip()
            return commit_type, scope, description

        return None, None, message.strip()

    def _calculate_semantic_similarity(self, full_message: str, description: str,
                                     work_item: Dict[str, Any]) -> float:
        """
        Calculate semantic similarity between commit and work item.

        Uses multiple signals:
        - Title similarity
        - Description similarity
        - Keyword overlap
        """
        work_title = work_item.get("title", "").lower()
        work_desc = work_item.get("description", "").lower()

        commit_text = f"{description} {full_message}".lower()

        # Title similarity (weighted higher)
        title_sim = SequenceMatcher(None, commit_text, work_title).ratio()

        # Description similarity
        desc_sim = SequenceMatcher(None, commit_text, work_desc).ratio()

        # Combined work item text similarity
        work_text = f"{work_title} {work_desc}"
        combined_sim = SequenceMatcher(None, commit_text, work_text).ratio()

        # Weighted average: title=40%, description=30%, combined=30%
        similarity = (title_sim * 0.4) + (desc_sim * 0.3) + (combined_sim * 0.3)

        return similarity

    def _find_keyword_matches(self, message: str, work_items: List[Dict[str, Any]]) -> List[str]:
        """Find exact keyword matches between commit message and work items."""
        message_lower = message.lower()
        matches = []

        for work_item in work_items:
            title_words = set(work_item.get("title", "").lower().split())
            desc_words = set(work_item.get("description", "").lower().split())

            # Filter out common words
            significant_words = {
                w for w in (title_words | desc_words)
                if len(w) > 3 and w not in {"with", "from", "that", "this", "will", "should"}
            }

            for word in significant_words:
                if word in message_lower and word not in matches:
                    matches.append(word)
                    if len(matches) >= 5:  # Limit matches
                        break

        return matches

    def _work_types_match(self, commit_type: str, work_type: str) -> bool:
        """Check if conventional commit type matches work item type."""
        if not commit_type or not work_type:
            return False

        mapped_type = self.COMMIT_TYPE_MAPPING.get(commit_type.lower())
        return mapped_type == work_type.lower()

    def _infer_priority_from_message(self, message: str) -> str:
        """Infer priority from commit message keywords."""
        message_lower = message.lower()

        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return priority

        return "medium"  # Default priority
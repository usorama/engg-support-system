#!/usr/bin/env python3
"""
Agent Coordination Safety Hook
Implements mitigations for Priority 1 agent coordination risks:
1. Task boundary confusion detection
2. Knowledge inconsistency prevention
3. Communication protocol validation
4. Cross-agent validation patterns
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import re
from typing import Dict, List, Optional, Set

class AgentCoordinationSafety:
    def __init__(self):
        self.project_root = Path.cwd()
        self.coordination_log = self.project_root / '.ai' / 'coordination_log.json'
        self.task_registry = self.project_root / '.ai' / 'task_registry.json'
        self.context_hashes = self.project_root / '.ai' / 'context_hashes.json'
        self.max_concurrent_agents = 3  # Limit based on research recommendations

        # Initialize files if they don't exist
        for log_file in [self.coordination_log, self.task_registry, self.context_hashes]:
            if not log_file.exists():
                log_file.parent.mkdir(parents=True, exist_ok=True)
                self.write_json(log_file, {})

    def write_json(self, filepath: Path, data: dict):
        """Write JSON data with error handling"""
        try:
            with filepath.open('w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not write to {filepath}: {e}", file=sys.stderr)

    def read_json(self, filepath: Path) -> dict:
        """Read JSON data with error handling"""
        try:
            if filepath.exists():
                with filepath.open('r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return {}

    def generate_task_id(self, task_description: str) -> str:
        """Generate unique task ID from description hash"""
        return hashlib.md5(task_description.encode()).hexdigest()[:8]

    def detect_task_boundary_confusion(self, action: str, context: dict) -> Dict[str, any]:
        """
        Detect overlapping or unclear task boundaries
        Risk: Task Boundary Confusion (Priority 1)
        """
        task_registry = self.read_json(self.task_registry)
        current_time = datetime.now().isoformat()

        # Extract task characteristics
        task_description = context.get('input', action)
        task_id = self.generate_task_id(task_description)

        # Check for overlapping tasks
        overlapping_tasks = []
        for existing_id, task_info in task_registry.items():
            if existing_id == task_id:
                continue

            # Check if task is still active (within last 30 minutes)
            task_time = datetime.fromisoformat(task_info.get('timestamp', '2000-01-01'))
            if datetime.now() - task_time < timedelta(minutes=30):
                # Simple overlap detection using keyword matching
                overlap_score = self.calculate_task_overlap(task_description, task_info.get('description', ''))
                if overlap_score > 0.7:
                    overlapping_tasks.append({
                        'id': existing_id,
                        'description': task_info.get('description'),
                        'overlap_score': overlap_score
                    })

        # Register current task
        task_registry[task_id] = {
            'description': task_description,
            'timestamp': current_time,
            'status': 'active',
            'action': action,
            'context_hash': hashlib.md5(str(context).encode()).hexdigest()[:8]
        }
        self.write_json(self.task_registry, task_registry)

        return {
            'task_id': task_id,
            'overlapping_tasks': overlapping_tasks,
            'boundary_clear': len(overlapping_tasks) == 0
        }

    def calculate_task_overlap(self, task1: str, task2: str) -> float:
        """Calculate semantic overlap between two task descriptions"""
        # Simple keyword-based overlap calculation
        words1 = set(re.findall(r'\w+', task1.lower()))
        words2 = set(re.findall(r'\w+', task2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def validate_context_consistency(self, context: dict) -> Dict[str, any]:
        """
        Validate context consistency across agent operations
        Risk: Knowledge Inconsistency Across Agents (Priority 1)
        """
        context_hashes = self.read_json(self.context_hashes)

        # Extract key context elements
        context_key_elements = {
            'project_state': self.get_project_state_hash(),
            'input_hash': hashlib.md5(str(context.get('input', '')).encode()).hexdigest()[:8],
            'timestamp': datetime.now().isoformat()
        }

        # Check for inconsistencies
        inconsistencies = []
        for stored_hash, stored_context in context_hashes.items():
            # Check if project state has changed unexpectedly
            if (stored_context.get('project_state') != context_key_elements['project_state'] and
                datetime.now() - datetime.fromisoformat(stored_context.get('timestamp', '2000-01-01')) < timedelta(minutes=5)):
                inconsistencies.append({
                    'type': 'rapid_project_state_change',
                    'previous_hash': stored_context.get('project_state'),
                    'current_hash': context_key_elements['project_state'],
                    'time_diff_seconds': (datetime.now() - datetime.fromisoformat(stored_context.get('timestamp'))).total_seconds()
                })

        # Store current context
        current_hash = hashlib.md5(str(context_key_elements).encode()).hexdigest()[:8]
        context_hashes[current_hash] = context_key_elements

        # Keep only recent context (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        context_hashes = {
            h: ctx for h, ctx in context_hashes.items()
            if datetime.fromisoformat(ctx.get('timestamp', '2000-01-01')) > cutoff_time
        }

        self.write_json(self.context_hashes, context_hashes)

        return {
            'context_hash': current_hash,
            'inconsistencies': inconsistencies,
            'consistency_ok': len(inconsistencies) == 0
        }

    def get_project_state_hash(self) -> str:
        """Generate hash representing current project state"""
        state_indicators = []

        # Check key files that indicate project state
        key_files = [
            '.ai/PROGRESS.md',
            'package.json',
            '.ai/tasks.json'
        ]

        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    stat = full_path.stat()
                    state_indicators.append(f"{file_path}:{stat.st_mtime}:{stat.st_size}")
                except:
                    pass

        return hashlib.md5('|'.join(state_indicators).encode()).hexdigest()[:8]

    def check_communication_protocol(self, action: str, context: dict) -> Dict[str, any]:
        """
        Validate communication protocol adherence
        Risk: Communication Protocol Breakdowns (Priority 1)
        """
        protocol_violations = []

        # Check if action involves multi-agent communication
        multi_agent_indicators = ['Task', 'Skill', 'subagent', 'delegate', 'spawn']
        involves_multi_agent = any(indicator in action for indicator in multi_agent_indicators)

        if involves_multi_agent:
            input_text = str(context.get('input', ''))

            # Check for missing context preservation
            if len(input_text.strip()) < 10:
                protocol_violations.append({
                    'type': 'insufficient_context',
                    'description': 'Multi-agent action with minimal context provided'
                })

            # Check for missing success criteria
            success_keywords = ['success', 'complete', 'done', 'criteria', 'requirement']
            has_success_criteria = any(keyword in input_text.lower() for keyword in success_keywords)
            if not has_success_criteria:
                protocol_violations.append({
                    'type': 'missing_success_criteria',
                    'description': 'Multi-agent task without clear success criteria'
                })

        return {
            'involves_multi_agent': involves_multi_agent,
            'protocol_violations': protocol_violations,
            'protocol_ok': len(protocol_violations) == 0
        }

    def check_concurrent_agent_limit(self) -> Dict[str, any]:
        """
        Ensure we don't exceed safe concurrent agent limits
        Risk: Agent coordination complexity grows exponentially
        """
        task_registry = self.read_json(self.task_registry)

        # Count active tasks (within last 10 minutes)
        cutoff_time = datetime.now() - timedelta(minutes=10)
        active_tasks = []

        for task_id, task_info in task_registry.items():
            task_time = datetime.fromisoformat(task_info.get('timestamp', '2000-01-01'))
            if task_time > cutoff_time and task_info.get('status') == 'active':
                active_tasks.append(task_id)

        return {
            'active_task_count': len(active_tasks),
            'max_allowed': self.max_concurrent_agents,
            'limit_exceeded': len(active_tasks) >= self.max_concurrent_agents,
            'active_tasks': active_tasks
        }

    def run_coordination_safety_checks(self, action: str, context: dict) -> Dict[str, any]:
        """Run all coordination safety checks"""

        # Run all safety checks
        boundary_check = self.detect_task_boundary_confusion(action, context)
        consistency_check = self.validate_context_consistency(context)
        protocol_check = self.check_communication_protocol(action, context)
        concurrency_check = self.check_concurrent_agent_limit()

        # Determine overall safety status
        all_checks = [
            boundary_check['boundary_clear'],
            consistency_check['consistency_ok'],
            protocol_check['protocol_ok'],
            not concurrency_check['limit_exceeded']
        ]

        safety_score = sum(all_checks) / len(all_checks)

        result = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'safety_score': safety_score,
            'checks': {
                'task_boundaries': boundary_check,
                'context_consistency': consistency_check,
                'communication_protocol': protocol_check,
                'concurrency_limits': concurrency_check
            },
            'overall_status': 'SAFE' if safety_score >= 0.75 else 'WARNING' if safety_score >= 0.5 else 'DANGEROUS'
        }

        # Log coordination event
        self.log_coordination_event(result)

        # Print warnings if needed
        if result['overall_status'] in ['WARNING', 'DANGEROUS']:
            self.print_safety_warnings(result)

        return result

    def log_coordination_event(self, result: dict):
        """Log coordination safety event"""
        coordination_log = self.read_json(self.coordination_log)

        event_id = hashlib.md5(str(result).encode()).hexdigest()[:8]
        coordination_log[event_id] = result

        # Keep only last 100 events
        if len(coordination_log) > 100:
            sorted_events = sorted(coordination_log.items(),
                                 key=lambda x: x[1].get('timestamp', ''),
                                 reverse=True)
            coordination_log = dict(sorted_events[:100])

        self.write_json(self.coordination_log, coordination_log)

    def print_safety_warnings(self, result: dict):
        """Print safety warnings to stderr"""
        status = result['overall_status']
        checks = result['checks']

        print(f"🚨 AGENT COORDINATION {status}: Safety score {result['safety_score']:.2f}/1.00", file=sys.stderr)

        # Task boundary warnings
        if not checks['task_boundaries']['boundary_clear']:
            overlapping = checks['task_boundaries']['overlapping_tasks']
            print(f"⚠️  Task Boundary Confusion: {len(overlapping)} overlapping tasks detected", file=sys.stderr)
            for task in overlapping:
                print(f"   - {task['id']}: {task['description'][:50]}... (overlap: {task['overlap_score']:.2f})", file=sys.stderr)

        # Context consistency warnings
        if not checks['context_consistency']['consistency_ok']:
            inconsistencies = checks['context_consistency']['inconsistencies']
            print(f"⚠️  Context Inconsistency: {len(inconsistencies)} inconsistencies detected", file=sys.stderr)
            for inc in inconsistencies:
                print(f"   - {inc['type']}: {inc.get('time_diff_seconds', 0):.1f}s ago", file=sys.stderr)

        # Protocol warnings
        if not checks['communication_protocol']['protocol_ok']:
            violations = checks['communication_protocol']['protocol_violations']
            print(f"⚠️  Communication Protocol Issues: {len(violations)} violations", file=sys.stderr)
            for violation in violations:
                print(f"   - {violation['type']}: {violation['description']}", file=sys.stderr)

        # Concurrency warnings
        if checks['concurrency_limits']['limit_exceeded']:
            count = checks['concurrency_limits']['active_task_count']
            limit = checks['concurrency_limits']['max_allowed']
            print(f"⚠️  Too Many Concurrent Agents: {count}/{limit} active", file=sys.stderr)

def main():
    """Hook entry point - reads from stdin per Claude Code hook protocol"""
    try:
        # Read from stdin (Claude Code hook protocol)
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # No valid input - exit silently (non-blocking)
        sys.exit(0)

    # Extract hook data
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})

    # ONLY track actual agent spawning tools
    # Skill, Bash, Read, Write, Edit, etc. are NOT agent spawns
    AGENT_SPAWNING_TOOLS = ['Task']

    if tool_name not in AGENT_SPAWNING_TOOLS:
        # Skip coordination checks for non-agent-spawning tools
        sys.exit(0)

    # Build action and context from hook data
    action = tool_name
    context = {
        'input': str(tool_input),
        'tool_name': tool_name,
        **tool_input
    }

    safety_checker = AgentCoordinationSafety()
    result = safety_checker.run_coordination_safety_checks(action, context)

    # Output result for potential consumption by Claude Code
    print(json.dumps({
        'safety_status': result['overall_status'],
        'safety_score': result['safety_score'],
        'timestamp': result['timestamp']
    }))

    # Exit 0 for safe, don't block operations
    sys.exit(0)

if __name__ == '__main__':
    main()
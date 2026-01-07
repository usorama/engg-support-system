#!/usr/bin/env python3
"""
Veracity Watcher Daemon - Autonomous project synchronization.

Monitors registered projects for file changes and triggers
automatic re-indexing to keep the knowledge graph up-to-date.

Usage:
    python3 core/watcher_daemon.py              # Run in foreground
    python3 core/watcher_daemon.py --daemon     # Run as daemon
    python3 core/watcher_daemon.py --once       # Index once and exit

Features:
    - Real-time file system monitoring (FSEvents/inotify via watchdog)
    - Debounced change aggregation (prevents rapid re-indexing)
    - Git-only mode (only re-index on commits)
    - Graceful shutdown on SIGTERM/SIGINT
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
import fnmatch
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None

from core.project_registry import (
    load_registry, list_projects, ProjectConfig, WatchMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('veracity.daemon')


class ProjectEventHandler(FileSystemEventHandler):
    """
    Handles file system events for a single project.

    Filters events by file patterns and notifies the daemon
    of relevant changes for debounced re-indexing.
    """

    # Directories to always ignore
    IGNORE_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', 'venv', '.venv', '__pycache__',
        '.pytest_cache', 'dist', 'build', '.next',
        'coverage', '.nyc_output', '.tox'
    }

    def __init__(
        self,
        project_name: str,
        project_config: ProjectConfig,
        on_change_callback
    ):
        super().__init__()
        self.project_name = project_name
        self.config = project_config
        self.on_change = on_change_callback
        self.file_patterns = project_config.file_patterns

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        parts = Path(path).parts
        for part in parts:
            if part in self.IGNORE_DIRS:
                return True
            if part.startswith('.') and part not in {'.github', '.gitlab'}:
                return True
        return False

    def _matches_pattern(self, path: str) -> bool:
        """Check if path matches any of the watched file patterns."""
        filename = os.path.basename(path)
        for pattern in self.file_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def on_any_event(self, event: FileSystemEvent):
        """Handle any file system event."""
        if event.is_directory:
            return

        path = event.src_path

        # Filter out ignored paths
        if self._should_ignore(path):
            return

        # Filter by file pattern
        if not self._matches_pattern(path):
            return

        # Notify daemon of change
        logger.debug(f"[{self.project_name}] {event.event_type}: {path}")
        self.on_change(self.project_name, path)


class VeracityDaemon:
    """
    Background daemon that monitors registered projects and
    triggers re-indexing when files change.

    Features:
        - Debounced change aggregation
        - Multiple watch modes (realtime, polling, git-only)
        - Graceful shutdown
        - Automatic observer management
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.observers: Dict[str, Observer] = {}
        self.pending_changes: Dict[str, Set[str]] = {}
        self.debounce_timers: Dict[str, threading.Timer] = {}
        self.last_git_heads: Dict[str, str] = {}
        self.running = False
        self.poll_thread: Optional[threading.Thread] = None
        self.veracity_root = Path(__file__).parent.parent

    def start(self):
        """Start watching all registered projects."""
        if not WATCHDOG_AVAILABLE:
            logger.error("watchdog not installed. Run: pip install watchdog")
            sys.exit(1)

        self.running = True
        registry = load_registry(self.config_path)

        if not registry.projects:
            logger.warning("No projects registered. Use: python3 core/project_registry.py register <name> <path>")
            return

        # Start watchers for each project
        for name, project in registry.projects.items():
            if not project.enabled:
                logger.info(f"Skipping disabled project: {name}")
                continue

            if not os.path.isdir(project.root_dir):
                logger.warning(f"Project directory not found: {project.root_dir}")
                continue

            self._start_project_watcher(name, project)

        # Start polling thread for git-only and polling modes
        self.poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.poll_thread.start()

        logger.info(f"Veracity daemon started. Watching {len(self.observers)} project(s)")

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop all watchers and clean up."""
        self.running = False

        # Cancel all debounce timers
        for timer in self.debounce_timers.values():
            timer.cancel()

        # Stop all observers
        for name, observer in self.observers.items():
            observer.stop()
            observer.join(timeout=5)
            logger.info(f"Stopped watching: {name}")

        self.observers.clear()
        logger.info("Veracity daemon stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _start_project_watcher(self, name: str, project: ProjectConfig):
        """Start file system watcher for a project."""
        if project.watch_mode == WatchMode.REALTIME:
            observer = Observer()
            handler = ProjectEventHandler(
                project_name=name,
                project_config=project,
                on_change_callback=self._on_file_change
            )

            # Watch each target directory
            for target_dir in project.target_dirs:
                watch_path = os.path.join(project.root_dir, target_dir)
                if os.path.isdir(watch_path):
                    observer.schedule(handler, watch_path, recursive=True)
                    logger.info(f"Watching: {watch_path}")

            observer.start()
            self.observers[name] = observer

        elif project.watch_mode == WatchMode.GIT_ONLY:
            # Initialize git HEAD tracking
            git_head = self._get_git_head(project.root_dir)
            self.last_git_heads[name] = git_head
            logger.info(f"Git-only mode for {name}: HEAD={git_head[:8] if git_head else 'N/A'}")

        elif project.watch_mode == WatchMode.POLLING:
            # Polling handled in _polling_loop
            logger.info(f"Polling mode for {name}: interval={project.poll_interval}s")

    def _on_file_change(self, project_name: str, path: str):
        """Handle file change with debouncing."""
        self.pending_changes.setdefault(project_name, set()).add(path)
        self._reset_debounce_timer(project_name)

    def _reset_debounce_timer(self, project_name: str):
        """Reset the debounce timer for a project."""
        # Cancel existing timer
        if project_name in self.debounce_timers:
            self.debounce_timers[project_name].cancel()

        # Get debounce delay from config
        projects = list_projects(self.config_path)
        project = projects.get(project_name)
        debounce = project.debounce if project else 5

        # Create new timer
        timer = threading.Timer(
            debounce,
            self._trigger_reindex,
            args=[project_name]
        )
        timer.start()
        self.debounce_timers[project_name] = timer

    def _trigger_reindex(self, project_name: str):
        """Trigger incremental re-indexing for a project."""
        projects = list_projects(self.config_path)
        project = projects.get(project_name)

        if not project:
            logger.error(f"Project not found: {project_name}")
            return

        changed_files = self.pending_changes.get(project_name, set())
        file_count = len(changed_files)

        if file_count == 0:
            return

        logger.info(f"Re-indexing {project_name} ({file_count} file(s) changed)")

        try:
            # Run build_graph.py
            cmd = [
                sys.executable,
                str(self.veracity_root / "core" / "build_graph.py"),
                "--project-name", project_name,
                "--root-dir", project.root_dir,
                "--target-dirs", *project.target_dirs
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.veracity_root)

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"Re-indexed {project_name} successfully")
            else:
                logger.error(f"Re-index failed for {project_name}: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error(f"Re-index timeout for {project_name}")
        except Exception as e:
            logger.error(f"Re-index error for {project_name}: {e}")
        finally:
            # Clear pending changes
            self.pending_changes[project_name] = set()

    def _get_git_head(self, root_dir: str) -> Optional[str]:
        """Get the current git HEAD commit."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _polling_loop(self):
        """Background thread for polling and git-only mode."""
        while self.running:
            projects = list_projects(self.config_path)

            for name, project in projects.items():
                if not project.enabled:
                    continue

                if project.watch_mode == WatchMode.GIT_ONLY:
                    # Check if git HEAD changed
                    current_head = self._get_git_head(project.root_dir)
                    last_head = self.last_git_heads.get(name)

                    if current_head and current_head != last_head:
                        logger.info(f"Git commit detected in {name}: {current_head[:8]}")
                        self.last_git_heads[name] = current_head
                        self.pending_changes.setdefault(name, set()).add("git-commit")
                        self._trigger_reindex(name)

                elif project.watch_mode == WatchMode.POLLING:
                    # For polling mode, just trigger periodic re-index
                    # The build_graph.py handles hash-based change detection
                    pass  # Handled by individual poll intervals

            time.sleep(10)  # Check every 10 seconds

    def index_once(self):
        """Index all registered projects once and exit."""
        registry = load_registry(self.config_path)

        for name, project in registry.projects.items():
            if not project.enabled:
                continue

            logger.info(f"Indexing: {name}")
            self.pending_changes[name] = {"initial-index"}
            self._trigger_reindex(name)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Veracity Watcher Daemon")
    parser.add_argument("--daemon", "-d", action="store_true",
                        help="Run as background daemon")
    parser.add_argument("--once", action="store_true",
                        help="Index all projects once and exit")
    parser.add_argument("--config", type=Path,
                        help="Path to projects.yaml config file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    daemon = VeracityDaemon(config_path=args.config)

    if args.once:
        daemon.index_once()
    elif args.daemon:
        # Daemonize (basic - for proper daemonization use systemd/launchd)
        logger.info("Starting in daemon mode")
        daemon.start()
    else:
        # Foreground mode
        daemon.start()


if __name__ == "__main__":
    main()

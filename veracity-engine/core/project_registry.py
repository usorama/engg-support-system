"""
Project Registry - Configuration management for watched projects.

Manages the ~/.veracity/projects.yaml file that defines which projects
are monitored for automatic re-indexing.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum


class WatchMode(str, Enum):
    """How to monitor a project for changes."""
    REALTIME = "realtime"  # File system events (watchdog)
    POLLING = "polling"    # Periodic git HEAD check
    GIT_ONLY = "git-only"  # Only on git commits


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    root_dir: str
    target_dirs: List[str] = field(default_factory=lambda: ["src", "core", "lib"])
    watch_mode: WatchMode = WatchMode.REALTIME
    poll_interval: int = 60  # seconds
    debounce: int = 5  # seconds
    file_patterns: List[str] = field(default_factory=lambda: ["*.py", "*.md"])
    enabled: bool = True

    def __post_init__(self):
        # Normalize watch_mode to enum
        if isinstance(self.watch_mode, str):
            self.watch_mode = WatchMode(self.watch_mode)
        # Expand ~ in root_dir
        self.root_dir = os.path.expanduser(self.root_dir)


@dataclass
class RegistryConfig:
    """Global registry configuration."""
    version: int = 1
    defaults: Dict = field(default_factory=dict)
    projects: Dict[str, ProjectConfig] = field(default_factory=dict)


def get_config_path() -> Path:
    """Get the path to the projects.yaml config file."""
    config_dir = Path.home() / ".veracity"
    return config_dir / "projects.yaml"


def ensure_config_dir() -> Path:
    """Ensure the ~/.veracity directory exists."""
    config_dir = Path.home() / ".veracity"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_registry(config_path: Optional[Path] = None) -> RegistryConfig:
    """
    Load the project registry from YAML.

    If no config exists, returns an empty registry.
    """
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        return RegistryConfig()

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Parse defaults
    defaults = data.get('defaults', {})

    # Parse projects
    projects = {}
    for name, proj_data in data.get('projects', {}).items():
        # Merge defaults with project-specific config
        merged = {**defaults, **proj_data}
        projects[name] = ProjectConfig(**merged)

    return RegistryConfig(
        version=data.get('version', 1),
        defaults=defaults,
        projects=projects
    )


def save_registry(config: RegistryConfig, config_path: Optional[Path] = None) -> None:
    """Save the project registry to YAML."""
    if config_path is None:
        config_path = get_config_path()

    ensure_config_dir()

    # Convert to dict for YAML serialization
    data = {
        'version': config.version,
        'defaults': config.defaults,
        'projects': {}
    }

    for name, proj in config.projects.items():
        data['projects'][name] = {
            'root_dir': proj.root_dir,
            'target_dirs': proj.target_dirs,
            'watch_mode': proj.watch_mode.value,
            'poll_interval': proj.poll_interval,
            'debounce': proj.debounce,
            'file_patterns': proj.file_patterns,
            'enabled': proj.enabled
        }

    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def register_project(
    name: str,
    root_dir: str,
    target_dirs: Optional[List[str]] = None,
    watch_mode: WatchMode = WatchMode.REALTIME,
    config_path: Optional[Path] = None
) -> ProjectConfig:
    """
    Register a new project for automatic indexing.

    Args:
        name: Project name (used in Neo4j)
        root_dir: Absolute path to project root
        target_dirs: Directories to index (default: src, core, lib)
        watch_mode: How to monitor for changes
        config_path: Override config file path

    Returns:
        The created ProjectConfig
    """
    config = load_registry(config_path)

    project = ProjectConfig(
        root_dir=os.path.abspath(os.path.expanduser(root_dir)),
        target_dirs=target_dirs or ["src", "core", "lib", "tests", "docs"],
        watch_mode=watch_mode
    )

    config.projects[name] = project
    save_registry(config, config_path)

    return project


def unregister_project(name: str, config_path: Optional[Path] = None) -> bool:
    """
    Remove a project from the registry.

    Returns True if the project was found and removed.
    """
    config = load_registry(config_path)

    if name in config.projects:
        del config.projects[name]
        save_registry(config, config_path)
        return True

    return False


def list_projects(config_path: Optional[Path] = None) -> Dict[str, ProjectConfig]:
    """List all registered projects."""
    config = load_registry(config_path)
    return config.projects


def get_project(name: str, config_path: Optional[Path] = None) -> Optional[ProjectConfig]:
    """Get configuration for a specific project."""
    config = load_registry(config_path)
    return config.projects.get(name)


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Veracity Project Registry")
    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List registered projects")

    # Register command
    register_parser = subparsers.add_parser("register", help="Register a project")
    register_parser.add_argument("name", help="Project name")
    register_parser.add_argument("root_dir", help="Project root directory")
    register_parser.add_argument("--target-dirs", nargs="+", help="Directories to index")
    register_parser.add_argument("--watch-mode", choices=["realtime", "polling", "git-only"],
                                 default="realtime")

    # Unregister command
    unregister_parser = subparsers.add_parser("unregister", help="Unregister a project")
    unregister_parser.add_argument("name", help="Project name")

    args = parser.parse_args()

    if args.command == "list":
        projects = list_projects()
        if not projects:
            print("No projects registered. Use 'register' to add one.")
        else:
            print(f"{'Name':<20} {'Root Directory':<50} {'Mode':<10}")
            print("-" * 80)
            for name, proj in projects.items():
                status = "" if proj.enabled else "(disabled)"
                print(f"{name:<20} {proj.root_dir:<50} {proj.watch_mode.value:<10} {status}")

    elif args.command == "register":
        project = register_project(
            name=args.name,
            root_dir=args.root_dir,
            target_dirs=args.target_dirs,
            watch_mode=WatchMode(args.watch_mode)
        )
        print(f"Registered '{args.name}' at {project.root_dir}")
        print(f"  Target dirs: {project.target_dirs}")
        print(f"  Watch mode: {project.watch_mode.value}")

    elif args.command == "unregister":
        if unregister_project(args.name):
            print(f"Unregistered '{args.name}'")
        else:
            print(f"Project '{args.name}' not found")

    else:
        parser.print_help()

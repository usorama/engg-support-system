# STORY-019: Autonomous Project Watcher

**Priority**: P0 - BLOCKER
**Status**: COMPLETE
**Created**: 2025-12-31
**Dependencies**: STORY-018 (MCP Server)

---

## Problem Statement

The Veracity Engine requires **manual configuration of git hooks in every target project** for automatic re-indexing. This is:

1. **Invasive**: Modifies target projects
2. **Fragile**: Easy to forget or misconfigure
3. **Non-scalable**: Every new project needs manual setup
4. **Breaks autonomy**: The knowledge graph should be self-maintaining

**Business Impact**: Projects fall out of sync, agents get stale context, and the whole value proposition of "ground truth" is undermined.

---

## Success Criteria

1. Register a project once → it stays in sync forever
2. Zero modification required in target projects
3. Real-time or near-real-time change detection
4. Auto-start on system boot
5. Graceful handling of project additions/removals
6. Works for both git and non-git projects

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Veracity Daemon                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  File Watcher    │    │  Git Poller      │               │
│  │  (watchdog)      │    │  (fallback)      │               │
│  │                  │    │                  │               │
│  │  Real-time       │    │  Poll every 60s  │               │
│  │  FSEvents/inotify│    │  Check git HEAD  │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           │                       │                          │
│           └───────────┬───────────┘                          │
│                       ▼                                      │
│           ┌──────────────────────┐                          │
│           │   Change Aggregator  │                          │
│           │   (debounce 5s)      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                       │
│           ┌──────────────────────┐                          │
│           │   Incremental Index  │                          │
│           │   (build_graph.py)   │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                       │
│           ┌──────────────────────┐                          │
│           │      Neo4j KG        │                          │
│           └──────────────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Project Registry

```yaml
# ~/.veracity/projects.yaml
version: 1

defaults:
  watch_mode: realtime  # realtime | polling | git-only
  poll_interval: 60     # seconds (for polling mode)
  debounce: 5           # seconds to wait after last change
  file_patterns:
    - "*.py"
    - "*.md"
    - "*.ts"
    - "*.tsx"
    - "*.js"
    - "*.jsx"

projects:
  pinglearn:
    root_dir: /Users/umasankr/Projects/pinglearn/pinglearn-app
    target_dirs:
      - src
      - tests
      - scripts
      - docs
    watch_mode: realtime

  veracity-engine:
    root_dir: /Users/umasankr/Projects/veracity-engine
    target_dirs:
      - core
      - tests
      - docs
    watch_mode: git-only  # Only re-index on commits
```

### Daemon Components

#### 1. `core/watcher_daemon.py` - Main Daemon

```python
class VeracityDaemon:
    """
    Background daemon that monitors registered projects and
    triggers re-indexing when files change.
    """

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.observers = {}  # project_name -> Observer
        self.pending_changes = {}  # project_name -> set of paths
        self.debounce_timers = {}  # project_name -> Timer

    def start(self):
        """Start watching all registered projects."""
        for name, project in self.config.projects.items():
            self._start_project_watcher(name, project)

    def _start_project_watcher(self, name, project):
        """Start file system watcher for a project."""
        observer = Observer()
        handler = ProjectEventHandler(
            project_name=name,
            callback=self._on_change
        )
        observer.schedule(handler, project.root_dir, recursive=True)
        observer.start()
        self.observers[name] = observer

    def _on_change(self, project_name, path):
        """Handle file change with debouncing."""
        self.pending_changes.setdefault(project_name, set()).add(path)
        self._reset_debounce_timer(project_name)

    def _trigger_reindex(self, project_name):
        """Trigger incremental re-indexing for a project."""
        project = self.config.projects[project_name]
        subprocess.run([
            sys.executable,
            "core/build_graph.py",
            "--project-name", project_name,
            "--root-dir", project.root_dir,
            "--target-dirs", *project.target_dirs
        ])
        self.pending_changes[project_name].clear()
```

#### 2. `scripts/veracityd` - Daemon Control Script

```bash
#!/bin/bash
# Veracity Daemon Control Script

case "$1" in
    start)
        python3 core/watcher_daemon.py --daemon
        ;;
    stop)
        pkill -f "watcher_daemon.py"
        ;;
    status)
        pgrep -f "watcher_daemon.py" && echo "Running" || echo "Stopped"
        ;;
    register)
        python3 core/watcher_daemon.py --register "$2" "$3"
        ;;
esac
```

#### 3. `com.veracity.daemon.plist` - launchd Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.veracity.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3.11</string>
        <string>/Users/umasankr/Projects/veracity-engine/core/watcher_daemon.py</string>
        <string>--daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/veracity-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/veracity-daemon.err</string>
</dict>
</plist>
```

---

## Implementation Plan

### Phase 1: Core Daemon (2 hours)

1. Create `core/watcher_daemon.py`
2. Implement file system watching with watchdog
3. Add debouncing and change aggregation
4. Test with single project

### Phase 2: Project Registry (1 hour)

1. Create `~/.veracity/projects.yaml` schema
2. Implement config loading
3. Add CLI for project registration

### Phase 3: Service Integration (1 hour)

1. Create `scripts/veracityd` control script
2. Create launchd plist
3. Add installation script

### Phase 4: Testing (1 hour)

1. Test with pinglearn
2. Verify real-time sync
3. Test daemon restart/recovery

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|------------|
| `core/watcher_daemon.py` | CREATE | Main daemon implementation |
| `core/project_registry.py` | CREATE | Project config management |
| `scripts/veracityd` | CREATE | Daemon control script |
| `scripts/install-daemon.sh` | CREATE | launchd installation |
| `infra/com.veracity.daemon.plist` | CREATE | launchd config |
| `requirements.txt` | MODIFY | Add `watchdog>=4.0.0` |
| `tests/test_watcher.py` | CREATE | Daemon tests |

---

## Testing Checklist

- [x] Daemon starts and watches registered projects
- [x] File changes trigger re-indexing (debounced)
- [x] Daemon survives process restart (launchd KeepAlive)
- [x] launchd starts daemon on boot (com.veracity.daemon PID 49220)
- [x] `veracityd status` shows running state
- [x] pinglearn stays in sync automatically
- [x] No polling for realtime mode (uses watchdog.observers.fsevents)

---

## Definition of Done

1. `veracityd start` launches background watcher
2. Projects registered in `~/.veracity/projects.yaml` auto-sync
3. Zero configuration in target projects
4. Daemon auto-starts on macOS login
5. All tests pass
6. Documentation complete

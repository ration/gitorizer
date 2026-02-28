import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from gitorizer import git_ops
from gitorizer.config import RepoConfig

logger = logging.getLogger(__name__)


class _DebounceHandler(FileSystemEventHandler):
    """
    Watchdog event handler with debounce logic.
    Ignores events inside .git/ and directory-only events.
    Resets a timer on each relevant event; triggers commit after quiet period.
    """

    def __init__(self, config: RepoConfig, stop_event: threading.Event) -> None:
        super().__init__()
        self._config = config
        self._stop_event = stop_event
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        # Ignore .git/ internals — these would cause infinite commit loops
        git_dir = str(self._config.path / ".git")
        if str(event.src_path).startswith(git_dir):
            return

        # Ignore pure directory events (we care about file content)
        if event.is_directory:
            return

        logger.debug("Change detected in %s: %s %s", self._config.path, event.event_type, event.src_path)
        self._reset_timer()

    def _reset_timer(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            if not self._stop_event.is_set():
                self._timer = threading.Timer(
                    self._config.commit_debounce,
                    self._do_commit,
                )
                self._timer.daemon = True
                self._timer.start()

    def _do_commit(self) -> None:
        if self._stop_event.is_set():
            return

        repo_path = self._config.path
        logger.info("Debounce elapsed for %s, checking for changes", repo_path)

        changed = git_ops.get_changed_files(repo_path)
        if not changed:
            logger.debug("No changes to commit in %s", repo_path)
            return

        success = git_ops.commit(repo_path, changed)
        if success and self._config.push:
            git_ops.push(repo_path)

    def cancel_pending(self) -> None:
        """Cancel any pending debounce timer. Call before shutdown."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class RepoWatcher:
    """Manages a watchdog Observer for a single repository."""

    def __init__(self, config: RepoConfig, stop_event: threading.Event) -> None:
        self._config = config
        self._handler = _DebounceHandler(config, stop_event)
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            path=str(config.path),
            recursive=True,
        )

    def start(self) -> None:
        logger.info("Starting watcher for %s (debounce=%ds)", self._config.path, self._config.commit_debounce)
        self._observer.start()

    def stop(self) -> None:
        logger.info("Stopping watcher for %s", self._config.path)
        self._handler.cancel_pending()
        self._observer.stop()
        self._observer.join()

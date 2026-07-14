import logging
import subprocess
import threading
import time
from pathlib import Path

from gitorizer.config import PostChangeHookConfig

logger = logging.getLogger(__name__)


class PostChangeHook:
    """Coalesce content changes and run the configured hook command with the changed repos."""

    def __init__(self, config: PostChangeHookConfig) -> None:
        self._config = config
        self._condition = threading.Condition()
        self._changed_repos: set[Path] = set()
        self._deadline = 0.0
        self._stopping = False
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="post-change-hook",
        )
        self._thread.start()

    def notify(self, repo_path: Path) -> None:
        """Schedule one hook run after the configured quiet period."""
        with self._condition:
            if self._stopping:
                return
            self._changed_repos.add(repo_path)
            self._deadline = time.monotonic() + self._config.debounce
            self._condition.notify_all()

    def stop(self) -> None:
        """Flush a pending hook run and wait for the worker to finish."""
        with self._condition:
            self._stopping = True
            if self._changed_repos:
                self._deadline = time.monotonic()
            self._condition.notify_all()
        self._thread.join()

    def _loop(self) -> None:
        while True:
            with self._condition:
                while not self._changed_repos and not self._stopping:
                    self._condition.wait()

                if self._stopping and not self._changed_repos:
                    return

                remaining = self._deadline - time.monotonic()
                if remaining > 0:
                    self._condition.wait(timeout=remaining)
                    continue

                changed_repos = sorted(self._changed_repos)
                self._changed_repos.clear()

            self._run_hook(changed_repos)

            with self._condition:
                if self._stopping and not self._changed_repos:
                    return

    def _run_hook(self, changed_repos: list[Path]) -> None:
        command = [*self._config.command, *(str(path) for path in changed_repos)]
        logger.info("Running post-change hook: %s", " ".join(command))
        try:
            result = subprocess.run(
                command,
                cwd=Path.home(),
                capture_output=True,
                text=True,
                timeout=self._config.timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "Post-change hook killed after %d seconds: %s",
                self._config.timeout,
                " ".join(command),
            )
            return
        except OSError as e:
            logger.error("Could not run post-change hook %s: %s", command[0], e)
            return

        if result.stdout.strip():
            logger.info("Post-change hook stdout: %s", result.stdout.strip())
        if result.stderr.strip():
            logger.warning("Post-change hook stderr: %s", result.stderr.strip())
        if result.returncode != 0:
            logger.error(
                "Post-change hook failed with exit code %d: %s",
                result.returncode,
                " ".join(command),
            )

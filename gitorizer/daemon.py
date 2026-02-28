import logging
import signal
import threading

from gitorizer import git_ops
from gitorizer.config import AppConfig, RepoConfig
from gitorizer.watcher import RepoWatcher

logger = logging.getLogger(__name__)


def _pull_loop(config: RepoConfig, stop_event: threading.Event) -> None:
    """
    Background thread: periodically pull for one repo.
    Uses stop_event.wait(timeout) so shutdown is immediate rather than
    waiting out the full pull_interval sleep.
    """
    logger.info(
        "Pull scheduler started for %s (interval=%ds)",
        config.path,
        config.pull_interval,
    )
    while not stop_event.wait(timeout=config.pull_interval):
        git_ops.pull(config.path)
    logger.info("Pull scheduler stopped for %s", config.path)


def run(app_config: AppConfig) -> None:
    """Main daemon entry point. Blocks until SIGINT or SIGTERM."""
    stop_event = threading.Event()

    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down...", sig_name)
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    watchers: list[RepoWatcher] = []
    pull_threads: list[threading.Thread] = []

    for repo_config in app_config.repos:
        watcher = RepoWatcher(repo_config, stop_event)
        watcher.start()
        watchers.append(watcher)

        if repo_config.pull_interval > 0:
            t = threading.Thread(
                target=_pull_loop,
                args=(repo_config, stop_event),
                daemon=True,
                name=f"pull-{repo_config.path.name}",
            )
            t.start()
            pull_threads.append(t)

    logger.info(
        "Gitorizer running. Watching %d repo(s). Press Ctrl+C to stop.",
        len(app_config.repos),
    )

    stop_event.wait()

    logger.info("Stopping watchers...")
    for watcher in watchers:
        watcher.stop()

    logger.info("Waiting for pull threads to finish...")
    for t in pull_threads:
        t.join(timeout=5.0)

    logger.info("Gitorizer stopped.")

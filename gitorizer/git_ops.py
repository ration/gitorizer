import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def get_changed_files(repo_path: Path) -> list[str]:
    """Stage all changes and return list of changed filenames. Empty list means nothing to commit."""
    add_result = _run(["git", "add", "-A"], cwd=repo_path)
    if add_result.returncode != 0:
        logger.error("git add -A failed in %s: %s", repo_path, add_result.stderr.strip())
        return []

    status_result = _run(["git", "status", "--porcelain"], cwd=repo_path)
    if status_result.returncode != 0:
        logger.error("git status failed in %s: %s", repo_path, status_result.stderr.strip())
        return []

    changed: list[str] = []
    for line in status_result.stdout.splitlines():
        if line.strip():
            # porcelain format: "XY filename" — filename starts at column 3
            changed.append(line[3:].strip())
    return changed


def commit(repo_path: Path, changed_files: list[str]) -> bool:
    """Commit staged changes with an auto-generated message. Returns True on success."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
    files_str = ", ".join(changed_files[:10])
    if len(changed_files) > 10:
        files_str += f", ... (+{len(changed_files) - 10} more)"
    message = f"gitorizer: auto-commit {timestamp} [{files_str}]"

    result = _run(["git", "commit", "-m", message], cwd=repo_path)
    if result.returncode != 0:
        logger.error("git commit failed in %s: %s", repo_path, result.stderr.strip())
        return False

    logger.info("Committed in %s: %s", repo_path, message)
    return True


def push(repo_path: Path) -> bool:
    """Push to the configured remote. Returns True on success."""
    result = _run(["git", "push"], cwd=repo_path)
    if result.returncode != 0:
        logger.error("git push failed in %s: %s", repo_path, result.stderr.strip())
        return False
    logger.info("Pushed %s", repo_path)
    return True


def pull(repo_path: Path) -> bool:
    """Pull with rebase. Logs errors but does not raise. Returns True on success."""
    result = _run(["git", "pull", "--rebase"], cwd=repo_path)
    if result.returncode != 0:
        logger.error("git pull --rebase failed in %s: %s", repo_path, result.stderr.strip())
        return False
    logger.info("Pulled %s", repo_path)
    return True

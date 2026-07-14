import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gitorizer.config import RepoConfig
from gitorizer.watcher import _DebounceHandler


def repo_config(*, push: bool = False) -> RepoConfig:
    return RepoConfig(
        path=Path("/notes"),
        push=push,
        pull_interval=60,
        commit_debounce=1,
    )


class DebounceHandlerTest(unittest.TestCase):
    def _handler(self, on_content_change: Mock, *, push: bool = False) -> _DebounceHandler:
        return _DebounceHandler(
            repo_config(push=push),
            threading.Event(),
            on_content_change,
        )

    @patch("gitorizer.watcher.git_ops")
    def test_successful_commit_reports_content_change(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.get_changed_files.return_value = ["note.md"]
        git_ops.commit.return_value = True

        self._handler(content_change, push=True)._do_commit()

        git_ops.push.assert_called_once_with(Path("/notes"))
        content_change.assert_called_once_with()

    @patch("gitorizer.watcher.git_ops")
    def test_no_changes_reports_nothing(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.get_changed_files.return_value = []

        self._handler(content_change)._do_commit()

        git_ops.commit.assert_not_called()
        content_change.assert_not_called()

    @patch("gitorizer.watcher.git_ops")
    def test_failed_commit_reports_nothing(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.get_changed_files.return_value = ["note.md"]
        git_ops.commit.return_value = False

        self._handler(content_change, push=True)._do_commit()

        git_ops.push.assert_not_called()
        content_change.assert_not_called()


if __name__ == "__main__":
    unittest.main()

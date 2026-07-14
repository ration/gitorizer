import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gitorizer.config import RepoConfig
from gitorizer.daemon import _pull_once


def repo_config() -> RepoConfig:
    return RepoConfig(
        path=Path("/notes"),
        push=False,
        pull_interval=60,
        commit_debounce=1,
    )


class PullOnceTest(unittest.TestCase):
    @patch("gitorizer.daemon.git_ops")
    def test_pull_that_moves_head_reports_content_change(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.head.side_effect = ["abc", "def"]
        git_ops.pull.return_value = True

        _pull_once(repo_config(), content_change)

        content_change.assert_called_once_with()

    @patch("gitorizer.daemon.git_ops")
    def test_pull_without_new_commits_reports_nothing(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.head.return_value = "abc"
        git_ops.pull.return_value = True

        _pull_once(repo_config(), content_change)

        content_change.assert_not_called()

    @patch("gitorizer.daemon.git_ops")
    def test_failed_pull_reports_nothing(self, git_ops: Mock) -> None:
        content_change = Mock()
        git_ops.head.return_value = "abc"
        git_ops.pull.return_value = False

        _pull_once(repo_config(), content_change)

        content_change.assert_not_called()


if __name__ == "__main__":
    unittest.main()

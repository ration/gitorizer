import subprocess
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gitorizer.hooks import PostChangeHook
from gitorizer.config import PostChangeHookConfig


def hook_config(
    *command: str,
    debounce: int = 0,
) -> PostChangeHookConfig:
    return PostChangeHookConfig(command=command or ("indexer",), debounce=debounce)


class PostChangeHookTest(unittest.TestCase):
    @patch("gitorizer.hooks.subprocess.run")
    def test_changed_repos_are_coalesced_into_one_run_with_paths(self, run: Mock) -> None:
        def complete(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = complete
        hook = PostChangeHook(hook_config("indexer", "--update", debounce=60))
        hook.notify(Path("/notes"))
        hook.notify(Path("/blog"))
        hook.notify(Path("/notes"))
        hook.stop()

        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0],
            ["indexer", "--update", "/blog", "/notes"],
        )

    @patch("gitorizer.hooks.subprocess.run")
    def test_worker_survives_a_failing_hook(self, run: Mock) -> None:
        first_failed = threading.Event()
        second_finished = threading.Event()
        call_count = 0

        def execute(command, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first_failed.set()
                return subprocess.CompletedProcess(command, 1, "", "failed")
            second_finished.set()
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = execute
        hook = PostChangeHook(hook_config())
        hook.notify(Path("/notes"))
        self.assertTrue(first_failed.wait(timeout=1))
        hook.notify(Path("/notes"))
        self.assertTrue(second_finished.wait(timeout=1))
        hook.stop()

        self.assertEqual(run.call_count, 2)

    @patch("gitorizer.hooks.subprocess.run")
    def test_change_during_hook_run_schedules_another_run(self, run: Mock) -> None:
        first_started = threading.Event()
        release_first = threading.Event()
        second_finished = threading.Event()
        call_count = 0

        def execute(command, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first_started.set()
                release_first.wait(timeout=1)
            else:
                second_finished.set()
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = execute
        hook = PostChangeHook(hook_config("refresh"))
        hook.notify(Path("/notes"))
        self.assertTrue(first_started.wait(timeout=1))
        hook.notify(Path("/blog"))
        release_first.set()
        self.assertTrue(second_finished.wait(timeout=1))
        hook.stop()

        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ["refresh", "/notes"])
        self.assertEqual(run.call_args_list[1].args[0], ["refresh", "/blog"])

    @patch("gitorizer.hooks.subprocess.run")
    def test_hooks_run_with_the_configured_timeout(self, run: Mock) -> None:
        run.return_value = subprocess.CompletedProcess(["indexer"], 0, "", "")
        hook = PostChangeHook(hook_config())
        hook.notify(Path("/notes"))
        hook.stop()

        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["timeout"], 300)

    @patch("gitorizer.hooks.subprocess.run")
    def test_worker_survives_a_hook_timeout(self, run: Mock) -> None:
        first_timed_out = threading.Event()
        second_finished = threading.Event()
        call_count = 0

        def execute(command, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                first_timed_out.set()
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            second_finished.set()
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = execute
        hook = PostChangeHook(hook_config())
        hook.notify(Path("/notes"))
        self.assertTrue(first_timed_out.wait(timeout=1))
        hook.notify(Path("/notes"))
        self.assertTrue(second_finished.wait(timeout=1))
        hook.stop()

        self.assertEqual(run.call_count, 2)

    @patch("gitorizer.hooks.subprocess.run")
    def test_stop_flushes_a_pending_run(self, run: Mock) -> None:
        run.return_value = subprocess.CompletedProcess(["refresh"], 0, "", "")
        hook = PostChangeHook(hook_config("refresh", debounce=60))
        hook.notify(Path("/notes"))

        hook.stop()

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["refresh", "/notes"])


if __name__ == "__main__":
    unittest.main()

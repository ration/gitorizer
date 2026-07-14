import tempfile
import unittest
from pathlib import Path

from gitorizer.config import load_config


class PostChangeHookConfigTest(unittest.TestCase):
    def _load(self, post_change_hook: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            repo.mkdir()
            config = root / "gitorizer.toml"
            config.write_text(
                f'''\
[[repos]]
path = "{repo}"

{post_change_hook}
'''
            )
            return load_config(config)

    def test_loads_hook_command_string(self) -> None:
        config = self._load(
            '''\
[post_change_hook]
debounce = 45
command = "/home/me/bin/update-index"
'''
        )

        self.assertIsNotNone(config.post_change_hook)
        assert config.post_change_hook is not None
        self.assertEqual(config.post_change_hook.debounce, 45)
        self.assertEqual(config.post_change_hook.command, ("/home/me/bin/update-index",))

    def test_loads_hook_command_with_fixed_arguments(self) -> None:
        config = self._load(
            '''\
[post_change_hook]
command = ["indexer", "--update"]
'''
        )

        assert config.post_change_hook is not None
        self.assertEqual(config.post_change_hook.command, ("indexer", "--update"))
        self.assertEqual(config.post_change_hook.debounce, 30)
        self.assertEqual(config.post_change_hook.timeout, 300)

    def test_loads_hook_timeout(self) -> None:
        config = self._load(
            '''\
[post_change_hook]
command = "indexer"
timeout = 60
'''
        )

        assert config.post_change_hook is not None
        self.assertEqual(config.post_change_hook.timeout, 60)

    def test_rejects_non_positive_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self._load(
                '''\
[post_change_hook]
command = "indexer"
timeout = 0
'''
            )

    def test_rejects_negative_debounce(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            self._load(
                '''\
[post_change_hook]
debounce = -1
command = "indexer"
'''
            )

    def test_rejects_missing_command(self) -> None:
        with self.assertRaisesRegex(ValueError, "'command' key"):
            self._load(
                '''\
[post_change_hook]
debounce = 45
'''
            )

    def test_rejects_empty_command(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty array of strings"):
            self._load(
                '''\
[post_change_hook]
command = []
'''
            )


if __name__ == "__main__":
    unittest.main()

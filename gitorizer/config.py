import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Defaults:
    push: bool = False
    pull_interval: int = 300  # seconds; 0 = disabled
    commit_debounce: int = 10  # seconds of quiet before committing


@dataclass(frozen=True)
class RepoConfig:
    path: Path
    push: bool
    pull_interval: int
    commit_debounce: int


@dataclass(frozen=True)
class PostChangeHookConfig:
    command: tuple[str, ...]
    debounce: int = 30
    timeout: int = 300  # seconds before a running hook is killed


@dataclass(frozen=True)
class AppConfig:
    defaults: Defaults
    repos: list[RepoConfig]
    post_change_hook: PostChangeHookConfig | None = None


def load_config(config_path: Path) -> AppConfig:
    """Load and validate TOML config, merging defaults into each repo entry."""
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    raw_defaults = raw.get("defaults", {})
    defaults = Defaults(
        push=raw_defaults.get("push", False),
        pull_interval=raw_defaults.get("pull_interval", 300),
        commit_debounce=raw_defaults.get("commit_debounce", 10),
    )

    repos: list[RepoConfig] = []
    for raw_repo in raw.get("repos", []):
        path_str = raw_repo.get("path")
        if not path_str:
            raise ValueError("Each [[repos]] entry must have a 'path' key")

        repo_path = Path(path_str).expanduser().resolve()
        if not repo_path.is_dir():
            raise ValueError(f"Repo path does not exist or is not a directory: {repo_path}")

        repos.append(RepoConfig(
            path=repo_path,
            push=raw_repo.get("push", defaults.push),
            pull_interval=raw_repo.get("pull_interval", defaults.pull_interval),
            commit_debounce=raw_repo.get("commit_debounce", defaults.commit_debounce),
        ))

    if not repos:
        raise ValueError("Config must contain at least one [[repos]] entry")

    raw_post_change_hook = raw.get("post_change_hook")
    post_change_hook = None
    if raw_post_change_hook is not None:
        if not isinstance(raw_post_change_hook, dict):
            raise ValueError("post_change_hook must be a TOML table")
        debounce = raw_post_change_hook.get("debounce", 30)
        if type(debounce) is not int or debounce < 0:
            raise ValueError("post_change_hook.debounce must be a non-negative integer")

        timeout = raw_post_change_hook.get("timeout", 300)
        if type(timeout) is not int or timeout <= 0:
            raise ValueError("post_change_hook.timeout must be a positive integer")

        raw_command = raw_post_change_hook.get("command")
        if raw_command is None:
            raise ValueError("post_change_hook must have a 'command' key")
        if isinstance(raw_command, str) and raw_command:
            command = (raw_command,)
        elif (
            isinstance(raw_command, list)
            and raw_command
            and all(isinstance(arg, str) and arg for arg in raw_command)
        ):
            command = tuple(raw_command)
        else:
            raise ValueError(
                "post_change_hook.command must be a command string or a non-empty array of strings"
            )

        post_change_hook = PostChangeHookConfig(command, debounce, timeout)

    return AppConfig(defaults=defaults, repos=repos, post_change_hook=post_change_hook)

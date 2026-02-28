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
class AppConfig:
    defaults: Defaults
    repos: list[RepoConfig]


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

    return AppConfig(defaults=defaults, repos=repos)

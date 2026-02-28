import argparse
import logging
import os
import sys
from pathlib import Path

from gitorizer.config import load_config
from gitorizer.daemon import run


def _default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "gitorizer" / "gitorizer.toml"


def main() -> None:
    default_config = _default_config_path()

    parser = argparse.ArgumentParser(
        prog="gitorizer",
        description="Git repository daemon: auto-commit, push, and pull on file changes.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help=f"Path to TOML configuration file (default: {default_config})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )

    try:
        config = load_config(args.config)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    run(config)


if __name__ == "__main__":
    main()

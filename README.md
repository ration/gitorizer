# gitorizer

A lightweight daemon that monitors git repositories for file changes and automatically commits them. It can optionally push after each commit and periodically pull from remote.

Uses native filesystem events (inotify on Linux, FSEvents on macOS) for instant change detection, with a polling fallback for other platforms.

## Features

- Watches one or more repositories simultaneously
- Auto-commits after a configurable debounce period (waits for writes to settle)
- Optional auto-push after each commit
- Periodic pull from remote (configurable per repo)
- Single TOML config file with global defaults overridable per repository

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install git+https://github.com/ration/gitorizer.git
```

Or from a local clone:

```bash
git clone https://github.com/ration/gitorizer.git
uv tool install ./gitorizer
```

This installs the `gitorizer` binary to `~/.local/bin/`.

## Configuration

Create `$XDG_CONFIG_HOME/gitorizer/gitorizer.toml` (`XDG_CONFIG_HOME` defaults to `~/.config`):

```toml
[defaults]
push = false         # push after every auto-commit
pull_interval = 300  # seconds between pulls; 0 to disable
commit_debounce = 10 # seconds of quiet before committing

[[repos]]
path = "~/projects/my-repo"
push = true        # override default for this repo
pull_interval = 60

[[repos]]
path = "~/notes"
# inherits all defaults
```

Each `[[repos]]` block must have a `path`. All other keys are optional and fall back to `[defaults]`.

## Usage

```bash
gitorizer
```

By default, gitorizer reads `$XDG_CONFIG_HOME/gitorizer/gitorizer.toml` (`XDG_CONFIG_HOME` defaults to `~/.config`). Pass `--config` to use a different file.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `$XDG_CONFIG_HOME/gitorizer/gitorizer.toml` | Path to TOML config file |
| `--log-level` | `INFO` | Verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Stop the daemon with `Ctrl+C` (or `SIGTERM`). It will finish any in-progress git operation before exiting.

## Commit message format

```
gitorizer: auto-commit 2026-02-28T14:32 [notes.md, ideas.txt]
```

File lists longer than 10 entries are truncated with a count of the remainder.

## Running as a systemd service (Linux)

Create `~/.config/systemd/user/gitorizer.service`:

```ini
[Unit]
Description=Gitorizer git auto-commit daemon
After=network.target

[Service]
ExecStart=%h/.local/bin/gitorizer
Restart=on-failure
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

Then enable and start it:

```bash
systemctl --user enable --now gitorizer
journalctl --user -fu gitorizer
```

## Running as a launchd service (macOS)

Create a log directory and a LaunchAgent plist:

```bash
mkdir -p ~/.local/share/gitorizer
```

Create `~/Library/LaunchAgents/com.gitorizer.daemon.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gitorizer.daemon</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/.local/bin/gitorizer</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/.local/share/gitorizer/gitorizer.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/.local/share/gitorizer/gitorizer.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/YOUR_USERNAME</string>
        <key>PATH</key>
        <string>/Users/YOUR_USERNAME/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME</string>
</dict>
</plist>
```

Replace `YOUR_USERNAME` with your macOS username (`whoami`).

Load and start the service:

```bash
launchctl load ~/Library/LaunchAgents/com.gitorizer.daemon.plist
```

**Managing the service:**

```bash
# Start / stop
launchctl start com.gitorizer.daemon
launchctl stop com.gitorizer.daemon

# Disable autostart
launchctl unload ~/Library/LaunchAgents/com.gitorizer.daemon.plist

# Restart after config changes
launchctl stop com.gitorizer.daemon && launchctl start com.gitorizer.daemon

# Check status (shows PID and last exit code)
launchctl list | grep gitorizer

# View logs
tail -f ~/.local/share/gitorizer/gitorizer.log
```

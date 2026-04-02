# gdtick

Minimal always-on-top stock ticker for GNOME desktops.

## Architecture

Single-file uv-python script (`gdtick.py`) — no separate config or build files.

## Stack

- Python 3.12+, run via `uv run --script`
- **yahooquery** for stock quotes and intraday history (switched from yfinance due to fc.yahoo.com DNS blocking issues)
- **tkinter** for GUI (system package, not pip-installable — requires `python-preference = "only-system"` in uv config and `sudo apt install python3-tk`)

## Running

```bash
uv run gdtick.py SYMBOL    # foreground
uv run gdtick.py SYMBOL &>/dev/null & disown  # background
```

## UI Controls

- Left-click drag to move window
- Right-click to close
- Bottom-right corner drag to resize
- Fonts scale with window size

## Key Design Constraints

- Keep it single-file and minimal
- `exclude-newer` in uv config set to 14-day window
- Borderless window with custom drag/resize (no title bar)

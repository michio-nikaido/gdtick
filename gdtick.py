#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "yahooquery",
# ]
# [tool.uv]
# exclude-newer = "2026-03-19T00:00:00Z"
# python-preference = "only-system"
# ///
"""Minimal always-on-top stock ticker for GNOME desktops."""

import sys
import tkinter as tk
from datetime import datetime, time

from yahooquery import Ticker

BG = "#0a0a2a"
CHART_COLOR = "#1e3a5f"


def fetch_quote(ticker: Ticker, symbol: str) -> dict | None:
    data = ticker.price[symbol]
    if not isinstance(data, dict):
        return None
    try:
        price = data["regularMarketPrice"]
        change = data["regularMarketChange"]
        pct = data["regularMarketChangePercent"] * 100
        prev_close = data["regularMarketPreviousClose"]
    except (KeyError, TypeError):
        return None
    return {"price": price, "change": change, "pct": pct, "prev_close": prev_close}


def fetch_history(ticker: Ticker) -> list[tuple[float, float]]:
    """Fetch today's 1-minute intraday data. Returns [(timestamp, price), ...]."""
    df = ticker.history(period="1d", interval="1m")
    if df is None or df.empty:
        return []
    points = []
    for idx, row in df.iterrows():
        # Index can be MultiIndex (symbol, datetime) or just datetime
        if isinstance(idx, tuple):
            ts = idx[-1].timestamp()
        else:
            ts = idx.timestamp()
        points.append((ts, float(row["close"])))
    return points


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: gdtick.py SYMBOL", file=sys.stderr)
        sys.exit(1)

    symbol = sys.argv[1].upper()
    ticker = Ticker(symbol)

    root = tk.Tk()
    root.title(symbol)
    root.configure(bg="#444444", padx=1, pady=1)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.resizable(True, True)

    canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # Drag support
    drag = {"x": 0, "y": 0}

    def on_press(e):
        drag["x"] = e.x_root - root.winfo_x()
        drag["y"] = e.y_root - root.winfo_y()

    def on_drag(e):
        root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")

    root.bind("<Button-3>", lambda e: root.destroy())

    # Resize handle (bottom-right corner)
    def on_resize_press(e):
        drag["w"] = root.winfo_width()
        drag["h"] = root.winfo_height()
        drag["rx"] = e.x_root
        drag["ry"] = e.y_root

    def on_resize_drag(e):
        w = max(200, drag["w"] + (e.x_root - drag["rx"]))
        h = max(60, drag["h"] + (e.y_root - drag["ry"]))
        root.geometry(f"{w}x{h}")

    grip = tk.Frame(root, bg=BG, width=12, height=12, cursor="bottom_right_corner")
    grip.bind("<Button-1>", on_resize_press)
    grip.bind("<B1-Motion>", on_resize_drag)
    grip.lift()
    grip.place(relx=1.0, rely=1.0, anchor="se")

    # Text items on the canvas
    price_id = canvas.create_text(0, 0, text="--", fill="white",
                                  font=("monospace", 32, "bold"), anchor="e")
    change_id = canvas.create_text(0, 0, text="--", fill="gray",
                                   font=("monospace", 16), anchor="se")
    pct_id = canvas.create_text(0, 0, text="--", fill="gray",
                                font=("monospace", 16), anchor="ne")

    # Bind drag to canvas
    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)

    # Chart state
    history: list[tuple[float, float]] = []
    prev_close: float | None = None
    last_history_fetch = 0.0

    def draw_chart():
        canvas.delete("chart")
        if len(history) < 2:
            return

        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        prices = [p for _, p in history]
        all_prices = prices[:]
        if prev_close is not None:
            all_prices.append(prev_close)
        min_p = min(all_prices)
        max_p = max(all_prices)
        price_range = max_p - min_p
        if price_range == 0:
            price_range = 1.0

        t_start = history[0][0]
        now = datetime.now().timestamp()
        t_range = now - t_start
        if t_range <= 0:
            t_range = 1.0

        pad = 4

        # Previous close reference line
        if prev_close is not None:
            y_ref = pad + (1.0 - (prev_close - min_p) / price_range) * (ch - 2 * pad)
            canvas.create_line(0, y_ref, cw, y_ref, fill="#555555",
                               dash=(4, 4), width=1, tags="chart")

        points = []
        for ts, price in history:
            x = pad + (ts - t_start) / t_range * (cw - 2 * pad)
            y = pad + (1.0 - (price - min_p) / price_range) * (ch - 2 * pad)
            points.append(x)
            points.append(y)

        if len(points) >= 4:
            canvas.create_line(points, fill=CHART_COLOR, width=2, tags="chart",
                               smooth=True)

    def layout(e=None):
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()

        # Scale fonts to fit
        price_size = max(10, min(int(ch * 0.45), int(cw * 0.08)))
        side_size = max(8, min(int(ch * 0.2), int(cw * 0.05)))
        canvas.itemconfig(price_id, font=("monospace", price_size, "bold"))
        canvas.itemconfig(change_id, font=("monospace", side_size))
        canvas.itemconfig(pct_id, font=("monospace", side_size))

        # Position: price center-left, change top-right, pct bottom-right
        canvas.coords(price_id, cw * 0.55, ch * 0.5)
        canvas.coords(change_id, cw - 8, ch * 0.5 - 2)
        canvas.coords(pct_id, cw - 8, ch * 0.5 + 2)

        draw_chart()
        # Ensure text stays above chart
        for item in (price_id, change_id, pct_id):
            canvas.tag_raise(item)

    canvas.bind("<Configure>", layout)

    def update() -> None:
        nonlocal history, prev_close, last_history_fetch

        q = fetch_quote(ticker, symbol)
        if q:
            canvas.itemconfig(price_id, text=f"{q['price']:.2f}")
            color = "#22c55e" if q["change"] >= 0 else "#ef4444"
            sign = "+" if q["change"] >= 0 else ""
            canvas.itemconfig(change_id, text=f"{sign}{q['change']:.2f}", fill=color)
            canvas.itemconfig(pct_id, text=f"{sign}{q['pct']:.2f}%", fill=color)
            prev_close = q["prev_close"]

        # Refresh history every 60 seconds
        now = datetime.now().timestamp()
        if now - last_history_fetch >= 60:
            history = fetch_history(ticker)
            last_history_fetch = now
            draw_chart()
            canvas.tag_raise(price_id)
            canvas.tag_raise(change_id)
            canvas.tag_raise(pct_id)

        root.after(1000, update)

    update()
    # Center on the screen where the mouse pointer currently is
    root.update_idletasks()
    px, py = root.winfo_pointerxy()
    root.geometry(f"380x100+{px - 190}+{py - 50}")
    root.mainloop()


if __name__ == "__main__":
    main()

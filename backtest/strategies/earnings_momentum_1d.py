"""
Experiment A — 1-Day Earnings Momentum (Long Only)
===================================================

Hypothesis: the earnings beat IS the momentum event. The gap-up open on day 1
captures the move before mean-reversion sets in. No overnight hold.

Signal filters:
  1. SUE ≥ +0.10 (10% beat)
  2. Announcement-day price reaction ≥ +2%
  3. Announcement-day volume ≥ 1.5× 20-day average
  (No 52-week-high or VIX filter — keep the universe wide to maximise trades)

Entry:   open of day 1 after announcement (AMC assumed)
Exit:    close of day 1 — or stopped intraday if low ≤ open × (1 − stop_pct)
         OHLC approximation: if day_low ≤ stop_level, exit recorded at stop_level
Stop:    3% below open (intraday — approximated from daily low)
No overnight hold: position always closed by EOD of day 1.

Costs applied per trade (entry + exit):
  REALISTIC_5: 5bps slippage each way + 0.1% spread each way
  Total round-trip cost ≈ 10bps slippage + 0.2% spread
"""
from __future__ import annotations

from collections import defaultdict


# ── Signal computation ────────────────────────────────────────────────────────

def compute_momentum_1d_signals(
    earnings_by_sym: dict,
    daily_bars_by_sym: dict,
    sue_threshold:    float = 0.10,
    min_reaction_pct: float = 0.02,   # +2% reaction on announcement day
    min_vol_ratio:    float = 1.5,
    lookback_vol:     int   = 20,
) -> list[dict]:
    """
    Returns a flat list of signal dicts — one per qualifying trade:
      {sym, announce_date, entry_date, reaction_day,
       prior_close, reaction_close, reaction_pct,
       entry_open, day1_high, day1_low, day1_close,
       avg_vol, reaction_vol, sue}

    Entry and exit prices are included so the runner can simulate P&L without
    re-loading bar data.
    """
    from backtest.earnings_data import _next_trading_day

    trades: list[dict] = []

    for sym, events in earnings_by_sym.items():
        bars = daily_bars_by_sym.get(sym, [])
        if not bars:
            continue

        bar_by_date: dict[str, dict] = {b['t']: b for b in bars}
        sorted_dates: list[str]       = sorted(bar_by_date)
        date_idx_map                  = {d: i for i, d in enumerate(sorted_dates)}

        # Rolling 20-day avg volume
        avg_vol_by_date: dict[str, float] = {}
        for i, d in enumerate(sorted_dates):
            window = sorted_dates[max(0, i - lookback_vol):i]
            vols   = [bar_by_date[dd]['v'] for dd in window if 'v' in bar_by_date[dd]]
            avg_vol_by_date[d] = sum(vols) / len(vols) if vols else 0.0

        for event in events:
            sue          = event.get('sue')
            announce_date = event.get('date', '')
            if sue is None or not announce_date:
                continue

            # ── Filter 1: beat threshold ──────────────────────────────────────
            if sue < sue_threshold:
                continue

            # entry_date = AMC + 2 days (same as PEAD baseline)
            entry_date = _next_trading_day(announce_date, 2)

            entry_idx = date_idx_map.get(entry_date)
            if entry_idx is None or entry_idx < 2:
                continue

            reaction_day = sorted_dates[entry_idx - 1]   # day 1 = reaction day
            prior_day    = sorted_dates[entry_idx - 2]   # day 0 close

            reaction_bar = bar_by_date.get(reaction_day)
            prior_bar    = bar_by_date.get(prior_day)
            entry_bar    = bar_by_date.get(entry_date)   # day 2 = our entry day
            if reaction_bar is None or prior_bar is None or entry_bar is None:
                continue

            prior_close    = prior_bar['c']
            reaction_close = reaction_bar['c']
            if prior_close <= 0:
                continue
            reaction_pct = (reaction_close - prior_close) / prior_close

            # ── Filter 2: price reaction ≥ +2% ───────────────────────────────
            if reaction_pct < min_reaction_pct:
                continue

            # ── Filter 3: volume ≥ 1.5× avg ──────────────────────────────────
            reaction_vol = reaction_bar.get('v', 0)
            avg_vol      = avg_vol_by_date.get(reaction_day, 0)
            if avg_vol > 0 and reaction_vol < min_vol_ratio * avg_vol:
                continue

            # Pack everything the simulation needs
            trades.append({
                'sym':            sym,
                'announce_date':  announce_date,
                'reaction_day':   reaction_day,
                'entry_date':     entry_date,    # THIS is the trading day we simulate
                'prior_close':    prior_close,
                'reaction_close': reaction_close,
                'reaction_pct':   reaction_pct,
                'entry_open':     entry_bar['o'],
                'entry_high':     entry_bar['h'],
                'entry_low':      entry_bar['l'],
                'entry_close':    entry_bar['c'],
                'avg_vol':        avg_vol,
                'reaction_vol':   reaction_vol,
                'sue':            sue,
            })

    return sorted(trades, key=lambda x: x['entry_date'])


# ── Trade P&L simulation ──────────────────────────────────────────────────────

def simulate_momentum_1d_trade(
    signal: dict,
    stop_pct:   float = 0.03,    # 3% intraday stop from open
    cost_model_bps: float = 5.0, # one-way slippage bps
    spread_pct: float = 0.001,   # one-way half-spread
) -> dict:
    """
    Simulate a single 1-day momentum trade.
    Returns a trade result dict with P&L, exit reason, and prices.

    Stop approximation:
      stop_level = entry_open × (1 − stop_pct)
      If day_low ≤ stop_level → stopped out at stop_level (conservative: touched the low)
      Otherwise → exit at day_close
    """
    open_px  = signal['entry_open']
    low_px   = signal['entry_low']
    close_px = signal['entry_close']

    factor   = cost_model_bps / 10_000
    # Entry fill: buy at open + slippage + half-spread (adverse = buy high)
    entry_fill = open_px * (1 + factor) + open_px * spread_pct / 2

    stop_level = open_px * (1 - stop_pct)

    if low_px <= stop_level:
        # Stopped intraday — exit at stop level (sell low, adverse)
        exit_fill  = stop_level * (1 - factor) - stop_level * spread_pct / 2
        exit_reason = 'stop'
    else:
        # Hold to close
        exit_fill  = close_px * (1 - factor) - close_px * spread_pct / 2
        exit_reason = 'close'

    pnl_per_share = exit_fill - entry_fill   # positive = profit

    return {
        'sym':          signal['sym'],
        'entry_date':   signal['entry_date'],
        'sue':          signal['sue'],
        'reaction_pct': signal['reaction_pct'],
        'entry_open':   open_px,
        'entry_fill':   entry_fill,
        'exit_fill':    exit_fill,
        'exit_reason':  exit_reason,
        'stop_level':   stop_level,
        'entry_close':  close_px,
        'pnl_pct':      pnl_per_share / entry_fill,   # as fraction of entry
        'win':          pnl_per_share > 0,
    }

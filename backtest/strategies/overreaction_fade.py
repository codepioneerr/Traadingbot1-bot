"""
Experiment B — Overreaction Fade (Short the Gap)
=================================================

Hypothesis: extreme earnings beats cause the market to overshoot on day 1.
Shorting the gap-up open and covering at partial gap-fill captures the reversal.

Risk/reward geometry:
  Entry:  short at open of day 1 (the gap-up open)
  Target: prior_close + 50% × (open − prior_close)   [gap partially fills]
  Stop:   open × 1.03                                  [3% above entry]
  Example: prev_close $100, gap to $108 open
    TP  = $100 + 0.50 × ($108 − $100) = $104  →  −$4 from short entry = +3.7% gain
    Stop = $108 × 1.03 = $111.24              →  +$3.24 from short entry = −3% loss
    R:R  ≈ 1.23 : 1

Signal filters (same day as gap — reaction_day = announce_date+1):
  1. SUE ≥ +0.15 (only short extreme beats)
  2. Announcement-day reaction ≥ +4% (only fade large gaps)
  3. Announcement-day volume ≥ 2.0× 20-day average
  4. NOT within 5% of rolling max high (don't fade true breakouts)
     Proxy: rolling max-high over all available bars up to reaction_day

Entry/exit using OHLC approximation:
  Each holding day, check in this ORDER (conservative):
    1. If day_high ≥ stop_level → stopped out at stop_level (loss)
    2. elif day_low ≤ tp_level  → covered at TP (profit)
    3. else                     → mark at close, continue holding
  "Stop before TP" assumption: on days both levels breached, stop wins (worst case).

Maximum hold: 3 trading days. Exit at close of day 3 if still open.

Costs (per-trade, all-in):
  Entry short: 5bps slippage + 0.1% spread + 15bps borrow = 20.5bps adverse
  Exit cover:  5bps slippage + 0.1% spread                = 5.1bps adverse
"""
from __future__ import annotations

from collections import defaultdict


# ── Signal computation ────────────────────────────────────────────────────────

def compute_overreaction_fade_signals(
    earnings_by_sym: dict,
    daily_bars_by_sym: dict,
    sue_threshold:    float = 0.15,
    min_reaction_pct: float = 0.04,   # +4% gap required
    min_vol_ratio:    float = 2.0,
    max_ath_dist:     float = 0.05,   # skip if within 5% of rolling max high
    lookback_vol:     int   = 20,
    max_hold_days:    int   = 3,
) -> list[dict]:
    """
    Returns a flat list of signal dicts — one per qualifying fade trade.
    Each dict includes all bar data needed for multi-day P&L simulation.
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

        # Rolling ALL-TIME high (over all available history up to each date)
        # Used as proxy for "true all-time high" since bars start 2021-01-04
        ath_by_date: dict[str, float] = {}
        running_max = 0.0
        for d in sorted_dates:
            h = bar_by_date[d]['h']
            if h > running_max:
                running_max = h
            ath_by_date[d] = running_max

        for event in events:
            sue          = event.get('sue')
            announce_date = event.get('date', '')
            if sue is None or not announce_date:
                continue

            # ── Filter 1: extreme beat ────────────────────────────────────────
            if sue < sue_threshold:
                continue

            # entry_date = day 1 open (AMC assumed → +2 trading days)
            entry_date = _next_trading_day(announce_date, 2)

            entry_idx = date_idx_map.get(entry_date)
            if entry_idx is None or entry_idx < 2:
                continue

            reaction_day = sorted_dates[entry_idx - 1]
            prior_day    = sorted_dates[entry_idx - 2]

            reaction_bar = bar_by_date.get(reaction_day)
            prior_bar    = bar_by_date.get(prior_day)
            entry_bar    = bar_by_date.get(entry_date)
            if reaction_bar is None or prior_bar is None or entry_bar is None:
                continue

            prior_close    = prior_bar['c']
            reaction_close = reaction_bar['c']
            if prior_close <= 0:
                continue
            reaction_pct = (reaction_close - prior_close) / prior_close

            # ── Filter 2: gap ≥ +4% ──────────────────────────────────────────
            if reaction_pct < min_reaction_pct:
                continue

            # ── Filter 3: volume ≥ 2× ────────────────────────────────────────
            reaction_vol = reaction_bar.get('v', 0)
            avg_vol      = avg_vol_by_date.get(reaction_day, 0)
            if avg_vol > 0 and reaction_vol < min_vol_ratio * avg_vol:
                continue

            # ── Filter 4: NOT within 5% of rolling max high ───────────────────
            # We use entry_open vs ATH measured through reaction_day
            entry_open = entry_bar['o']
            ath = ath_by_date.get(reaction_day, 0)
            if ath > 0:
                dist_from_ath = (ath - entry_open) / ath
                if dist_from_ath < max_ath_dist:
                    continue   # too close to ATH — skip (true breakout candidate)

            # Collect holding bars (day 1 through day max_hold_days)
            hold_bars = []
            for offset in range(max_hold_days):
                idx = entry_idx + offset
                if idx >= len(sorted_dates):
                    break
                d = sorted_dates[idx]
                b = bar_by_date.get(d)
                if b:
                    hold_bars.append(b)

            if not hold_bars:
                continue

            trades.append({
                'sym':           sym,
                'announce_date': announce_date,
                'reaction_day':  reaction_day,
                'entry_date':    entry_date,
                'prior_close':   prior_close,
                'reaction_close': reaction_close,
                'reaction_pct':  reaction_pct,
                'entry_open':    entry_open,
                'avg_vol':       avg_vol,
                'reaction_vol':  reaction_vol,
                'sue':           sue,
                'ath':           ath,
                'hold_bars':     hold_bars,   # [{'t','o','h','l','c'}, ...]
            })

    return sorted(trades, key=lambda x: x['entry_date'])


# ── Trade P&L simulation ──────────────────────────────────────────────────────

def simulate_overreaction_trade(
    signal: dict,
    stop_pct:        float = 0.03,    # stop is 3% above entry open
    tp_gap_fill_pct: float = 0.50,    # TP at 50% gap fill
    cost_entry_bps:  float = 20.5,    # 5bps slip + 0.1% spread + 15bps borrow
    cost_exit_bps:   float = 5.1,     # 5bps slip + 0.1% spread (buy to cover)
    spread_pct:      float = 0.001,
) -> dict:
    """
    Simulate a single overreaction fade trade using OHLC approximation.

    Exit priority (conservative — stop before TP on same day):
      1. day_high ≥ stop_level → stopped at stop (loss)
      2. day_low  ≤ tp_level   → covered at TP  (profit)
      3. neither               → carry to next day; if last day, close at close

    Returns trade result dict with P&L per share (and %).
    """
    open_px    = signal['entry_open']
    prior_close = signal['prior_close']
    hold_bars   = signal['hold_bars']

    # Entry: short at open (adverse = buy-high effect on cover, but entry cost is here)
    factor_in  = cost_entry_bps / 10_000
    factor_out = cost_exit_bps  / 10_000

    # Short entry fill = open + slippage (adverse: filled higher)
    entry_fill = open_px * (1 + factor_in)

    # TP and stop levels (static — set at entry)
    gap_size   = open_px - prior_close
    tp_level   = prior_close + tp_gap_fill_pct * gap_size   # cover price for profit
    stop_level = open_px * (1 + stop_pct)                   # cover price for loss

    if tp_level >= entry_fill:
        # TP is at or above entry — no profit possible (can happen if gap is small)
        # This shouldn't occur if reaction_pct ≥ 4% and tp_gap_fill_pct = 0.50
        # but guard against edge cases
        tp_level = prior_close   # push TP to prior close

    exit_fill   = None
    exit_reason = None
    hold_days   = 0

    for bar in hold_bars:
        hold_days += 1
        is_last = (hold_days == len(hold_bars))

        # Conservative ordering: check stop FIRST, then TP
        if bar['h'] >= stop_level:
            # Stopped — cover at stop (adverse: buy higher than stop for shorts)
            cover_px   = stop_level * (1 + factor_out)
            exit_fill   = cover_px
            exit_reason = 'stop'
            break
        elif bar['l'] <= tp_level:
            # TP hit — cover at TP (slightly adverse slippage)
            cover_px   = tp_level * (1 + factor_out)
            exit_fill   = cover_px
            exit_reason = 'tp'
            break
        elif is_last:
            # Time stop — exit at close of last day
            cover_px   = bar['c'] * (1 + factor_out)
            exit_fill   = cover_px
            exit_reason = f'time_day{hold_days}'
            break

    if exit_fill is None:
        # Should not happen, but guard
        exit_fill   = hold_bars[-1]['c'] * (1 + factor_out)
        exit_reason = 'time_day_fallback'
        hold_days   = len(hold_bars)

    # Short P&L: profit when exit_fill < entry_fill (covered lower)
    pnl_per_share = entry_fill - exit_fill   # positive = profit (covered lower)
    pnl_pct       = pnl_per_share / entry_fill

    return {
        'sym':          signal['sym'],
        'entry_date':   signal['entry_date'],
        'sue':          signal['sue'],
        'reaction_pct': signal['reaction_pct'],
        'entry_open':   open_px,
        'entry_fill':   entry_fill,
        'exit_fill':    exit_fill,
        'exit_reason':  exit_reason,
        'tp_level':     tp_level,
        'stop_level':   stop_level,
        'hold_days':    hold_days,
        'pnl_pct':      pnl_pct,
        'win':          pnl_per_share > 0,
    }

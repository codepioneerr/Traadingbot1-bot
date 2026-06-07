"""
PEAD Short-Only Strategy — Experiment 1
========================================

Tests whether the short-side PEAD edge (misses producing multi-day drift down)
survives realistic borrow costs and stress-testing across the full 2021-2026 window.

Differences from baseline pead.py:
  - Shorts only (SUE ≤ threshold, longs filtered out)
  - 52-week LOW proximity filter replaces 52-week HIGH filter:
      Stock must be within 15% of its 52-week low at entry
      (falling-knife confirmation — misses on structurally weak stocks drift further)
  - Higher cost: 5bps (REALISTIC_5) + 15bps borrow + 10bps hard-to-borrow proxy = 30bps flat
    (no per-stock short-interest data available; 10bps proxy applied to all)
  - Same exits: −7% stop, 2% reversal, 10-day time stop

Entry filters (all required):
  1. SUE ≤ −sue_threshold         (default 0.05 = 5% miss)
  2. Reaction-day price drop ≤ −1% (confirms direction)
  3. Reaction-day volume ≥ 1.5× 20-day average
  4. Stock within 15% of 52-week LOW at entry (new — replaces 52wk-high filter)
  5. VIX regime not 'high'
"""
from __future__ import annotations

from collections import defaultdict
from .base import Strategy, Signal
from .pead import PEADStrategy   # reuse the on_bar / universe logic wholesale


# ── Signal pre-computation (short-only variant) ───────────────────────────────

def compute_short_only_signals(
    earnings_by_sym: dict,
    daily_bars_by_sym: dict,
    regime_map: dict,
    sue_threshold:    float = 0.05,
    min_reaction_pct: float = 0.01,   # reaction must be ≤ −min_reaction_pct
    min_vol_ratio:    float = 1.5,
    max_lo_dist:      float = 0.15,   # within 15% of 52-week low
    lookback_vol:     int   = 20,
    lookback_52wk:    int   = 252,
    top_n_per_day:    int   = 10,
    entry_offset:     int   = 2,      # trading days after announcement (2=AMC default)
) -> dict[str, list[tuple[str, str]]]:
    """
    Returns {entry_date: [(sym, 'short'), ...]} — short signals only.

    entry_offset controls entry timing:
      1 = day-1 open (aggressive — enter on gap day open)
      2 = day-2 open (default, AMC conservative)
      3 = day-3 open (delayed entry)
    """
    from backtest.earnings_data import _next_trading_day

    signals: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for sym, events in earnings_by_sym.items():
        bars = daily_bars_by_sym.get(sym, [])
        if not bars:
            continue

        bar_by_date: dict[str, dict] = {b['t']: b for b in bars}
        sorted_dates: list[str]       = sorted(bar_by_date)

        # Rolling 20-day avg volume
        avg_vol_by_date: dict[str, float] = {}
        for i, d in enumerate(sorted_dates):
            window = sorted_dates[max(0, i - lookback_vol):i]
            vols   = [bar_by_date[dd]['v'] for dd in window if 'v' in bar_by_date[dd]]
            avg_vol_by_date[d] = sum(vols) / len(vols) if vols else 0.0

        # Rolling 52-week LOW lookup
        lo_by_date: dict[str, float] = {}
        for i, d in enumerate(sorted_dates):
            window = sorted_dates[max(0, i - lookback_52wk):i + 1]
            lows   = [bar_by_date[dd]['l'] for dd in window if 'l' in bar_by_date[dd]]
            lo_by_date[d] = min(lows) if lows else float('inf')

        date_idx_map = {d: i for i, d in enumerate(sorted_dates)}

        for event in events:
            sue             = event.get('sue')
            announce_date   = event.get('date', '')
            if sue is None or not announce_date:
                continue

            # ── Filter 1: miss only ───────────────────────────────────────────
            if sue > -sue_threshold:
                continue
            side = 'short'

            # Compute entry_date with the requested offset
            entry_date = _next_trading_day(announce_date, entry_offset)

            # Make sure we have bar data for entry and the two preceding days
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

            # ── Filter 2: reaction confirms short direction ────────────────────
            if reaction_pct > -min_reaction_pct:
                continue

            # ── Filter 3: volume spike ────────────────────────────────────────
            reaction_vol = reaction_bar.get('v', 0)
            avg_vol      = avg_vol_by_date.get(reaction_day, 0)
            if avg_vol > 0 and reaction_vol < min_vol_ratio * avg_vol:
                continue

            # ── Filter 4: within 15% of 52-week LOW (falling knife) ───────────
            lo_52wk    = lo_by_date.get(reaction_day, 0)
            entry_open = entry_bar['o']
            if lo_52wk > 0 and lo_52wk < float('inf'):
                # distance from 52wk low = (entry - low) / entry
                dist_from_low = (entry_open - lo_52wk) / entry_open if entry_open > 0 else 1.0
                if dist_from_low > max_lo_dist:
                    continue  # too far above its low — not a falling knife

            # ── Filter 5: VIX regime ──────────────────────────────────────────
            regime = regime_map.get(entry_date, {})
            if regime.get('vix_regime') == 'high':
                continue

            signals[entry_date].append((sym, side))

    # Cap per day
    capped: dict[str, list[tuple[str, str]]] = {}
    for date, entries in signals.items():
        capped[date] = entries[:top_n_per_day]

    return capped


# ── Strategy class (thin wrapper around PEADStrategy) ─────────────────────────

class PEADShortOnlyStrategy(PEADStrategy):
    """
    Identical to PEADStrategy but only takes short positions.
    Signal filtering happens in compute_short_only_signals() before
    this class is instantiated, so no changes needed in on_bar.
    """
    pass

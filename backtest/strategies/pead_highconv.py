"""
PEAD High-Conviction Long Strategy — Experiment 2
==================================================

Tests whether the long-side PEAD edge exists at higher selectivity thresholds.
The baseline failed (PF 0.849, WR 35%) — hypothesis: the 5% SUE threshold
captures too much noise. At ≥15% or ≥25% only genuine outlier beats qualify.

Differences from baseline pead.py:
  - Longs only (shorts filtered out)
  - Higher SUE threshold (0.15 or 0.25 — passed as parameter)
  - Stronger price reaction required: ≥ +3% (vs original 1%)
  - Stronger volume filter: ≥ 2.0× (vs original 1.5×)
  - Tighter 52-week high proximity: within 10% (vs original 15%)
  - Tighter VIX filter: only 'low' regime allowed (vs 'not high' = low+normal)
    Rationale: "VIX < 20" maps roughly to 'low' tercile in the percentile regime map
  - Same exits: −7% stop, 2% reversal, 10-day time stop
  - Cost: REALISTIC_5 (5bps + 0.1% spread)
"""
from __future__ import annotations

from collections import defaultdict
from .pead import PEADStrategy


def compute_highconv_long_signals(
    earnings_by_sym: dict,
    daily_bars_by_sym: dict,
    regime_map: dict,
    sue_threshold:    float = 0.15,    # 0.15 or 0.25 — test both
    min_reaction_pct: float = 0.03,    # +3% minimum reaction day move
    min_vol_ratio:    float = 2.0,     # 2× average volume
    max_hi_dist:      float = 0.10,    # within 10% of 52-week high
    lookback_vol:     int   = 20,
    lookback_52wk:    int   = 252,
    top_n_per_day:    int   = 10,
) -> dict[str, list[tuple[str, str]]]:
    """
    Returns {entry_date: [(sym, 'long'), ...]} — high-conviction longs only.

    All five filters must pass simultaneously. Single threshold miss → skip.
    """
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

        # Rolling 52-week HIGH lookup
        hi_by_date: dict[str, float] = {}
        for i, d in enumerate(sorted_dates):
            window = sorted_dates[max(0, i - lookback_52wk):i + 1]
            highs  = [bar_by_date[dd]['h'] for dd in window if 'h' in bar_by_date[dd]]
            hi_by_date[d] = max(highs) if highs else 0.0

        date_idx_map = {d: i for i, d in enumerate(sorted_dates)}

        for event in events:
            sue        = event.get('sue')
            entry_date = event.get('entry_date', '')
            if sue is None or not entry_date:
                continue

            # ── Filter 1: high-conviction beat (raised threshold) ─────────────
            if sue < sue_threshold:
                continue
            side = 'long'

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

            # ── Filter 2: strong upside reaction (≥ +3%) ─────────────────────
            if reaction_pct < min_reaction_pct:
                continue

            # ── Filter 3: high volume (≥ 2×) ─────────────────────────────────
            reaction_vol = reaction_bar.get('v', 0)
            avg_vol      = avg_vol_by_date.get(reaction_day, 0)
            if avg_vol > 0 and reaction_vol < min_vol_ratio * avg_vol:
                continue

            # ── Filter 4: within 10% of 52-week high ─────────────────────────
            hi_52wk    = hi_by_date.get(reaction_day, 0)
            entry_open = entry_bar['o']
            if hi_52wk > 0 and (hi_52wk - entry_open) / hi_52wk > max_hi_dist:
                continue

            # ── Filter 5: VIX 'low' regime only (proxy for VIX < 20) ─────────
            # The percentile regime map splits into terciles: low | normal | high
            # 'low' tercile historically corresponds to VIX below ~18-20.
            regime = regime_map.get(entry_date, {})
            vix_label = regime.get('vix_regime', 'unknown')
            if vix_label != 'low':
                continue

            signals[entry_date].append((sym, side))

    # Cap per day
    capped: dict[str, list[tuple[str, str]]] = {}
    for date, entries in signals.items():
        capped[date] = entries[:top_n_per_day]

    return capped


class PEADHighConvStrategy(PEADStrategy):
    """High-conviction long-only PEAD variant."""
    pass

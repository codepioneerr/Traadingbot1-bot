"""
PEAD — Post-Earnings Announcement Drift strategy.

Captures the multi-day price drift that follows earnings surprises where the
market systematically under-reacts to fundamental news (Bernard & Thomas 1989).

Signal: SUE (Standardized Unexpected Earnings)
    SUE = (actual_eps − estimated_eps) / abs(estimated_eps)
    Long  when SUE ≥ +0.05  (≥5% beat)
    Short when SUE ≤ −0.05  (≥5% miss)
    Skip  when |SUE| < 0.05 (no edge in the middle)

Entry filters (all required to enter):
    1. SUE threshold met (above)
    2. Announcement-day price reaction confirms direction:
         Long  → reaction_day close ≥ +1% vs prior close
         Short → reaction_day close ≤ −1% vs prior close
    3. Announcement-day volume ≥ 1.5× 20-day average daily volume
    4. (Longs only) Stock within 15% of 52-week high — recency bias amplifies drift
    5. VIX regime not 'high'

Entry timing:
    Open of entry_date (conservatively treated as AMC: 2 trading days after
    announcement date). Entry price = bar['o'] on entry_date.

Adaptive exit (follow the drift):
    1. Price reversal > 2% from post-entry high (long) or low (short) → exit
    2. Hard stop loss: 7% against position from entry
    3. Hard max hold: 10 trading days

Position sizing:
    Inherits from BacktestEngine (default 20% of equity per position, max 6).

Interface:
    Follows the same Strategy ABC as orb.py.
    Constructed with pre-computed signals_by_date — call
    compute_pead_signals() before instantiating.
"""

from __future__ import annotations

from collections import defaultdict
from .base import Strategy, Signal


class PEADStrategy(Strategy):
    """PEAD strategy — runs on DAILY bars."""

    def __init__(
        self,
        signals_by_date: dict,        # {date_str: [(sym, side), ...]}  side='long'|'short'
        all_trading_dates: list,       # sorted list of every trading date in backtest window
        max_hold_days:   int   = 10,
        stop_loss_pct:   float = 0.07,
        reversal_pct:    float = 0.02,
    ):
        self.signals_by_date = signals_by_date
        self.max_hold_days   = max_hold_days
        self.stop_loss_pct   = stop_loss_pct
        self.reversal_pct    = reversal_pct

        # Pre-build universe lookup: date → set of symbols that must be active.
        # A symbol stays in the universe from entry_date through
        # entry_date + max_hold_days + 2 (buffer so the engine calls on_bar
        # every day while the position is open — PEAD positions span multiple days).
        self._universe: dict[str, set[str]] = self._build_universe(
            signals_by_date, all_trading_dates
        )

        # Cross-day state — NOT cleared by the engine's daily _per_symbol_state.clear().
        # The engine clears state['key'] between days; we store hold duration and
        # watermarks here so they survive overnight.
        # {symbol: {'bars_held': int, 'peak': float, 'trough': float, 'entry_date': str}}
        self._pead_state: dict = defaultdict(dict)

    # ── Strategy interface ─────────────────────────────────────────────────────

    def params(self) -> dict:
        return {
            'max_hold_days': self.max_hold_days,
            'stop_loss_pct': self.stop_loss_pct,
            'reversal_pct':  self.reversal_pct,
        }

    def universe(self, date, ctx: dict) -> list[str]:
        """Return symbols with active PEAD positions or pending entries today."""
        date_str = date if isinstance(date, str) else str(date)[:10]
        return list(self._universe.get(date_str, set()))

    def on_bar(self, symbol: str, bar: dict, state: dict, ctx: dict) -> list[Signal]:
        """
        Called once per trading day per active symbol (daily bar).

        Key engine behaviour this must respect:
            - state (= engine's _per_symbol_state[symbol]) is CLEARED at the start
              of every new calendar day.  We cannot rely on it for cross-day data.
            - The engine RE-INJECTS state['position'] = pos.to_dict() before each
              on_bar call when a position is open.  We use this to detect open positions.
            - Cross-day tracking (bars_held, watermarks) lives in self._pead_state,
              which is a strategy-level dict and survives across days.

        bar keys used: 't' (date or datetime), 'o', 'h', 'l', 'c'.
        """
        # ── Detect open position via engine-injected state['position'] ─────────
        pos_dict = state.get('position')       # None when no open position
        date_str = str(bar.get('t', ''))[:10]  # always YYYY-MM-DD

        # ── A) No open position — check for entry signal ───────────────────────
        if pos_dict is None:
            ps = self._pead_state.get(symbol, {})

            # Prevent double-entry: if we already entered this signal, skip
            if ps.get('entry_date') == date_str:
                return []

            entry_list = self.signals_by_date.get(date_str, [])
            this_entry = next((e for e in entry_list if e[0] == symbol), None)
            if this_entry is None:
                return []

            _, side = this_entry
            # Initialise cross-day tracking
            self._pead_state[symbol] = {
                'entry_date': date_str,
                'bars_held':  0,
                'peak':       bar['o'],   # high-water mark (long)
                'trough':     bar['o'],   # low-water mark  (short)
            }
            return [Signal(
                symbol=symbol,
                action='buy' if side == 'long' else 'short',
                reason=f'pead-{side}',
            )]

        # ── B) Position is open — update cross-day state and check exits ────────
        ps         = self._pead_state.setdefault(symbol, {})
        bars_held  = ps.get('bars_held', 0) + 1
        ps['bars_held'] = bars_held

        side        = pos_dict.get('side', 'long')
        entry_price = pos_dict.get('entry_price', bar['c'])
        close       = bar['c']

        # Update high/low watermarks with today's intraday range
        if side == 'long':
            ps['peak']   = max(ps.get('peak',   bar['h']), bar['h'])
        else:
            ps['trough'] = min(ps.get('trough', bar['l']), bar['l'])

        # ── Exit rule 1: hard stop loss (7%) ─────────────────────────────────
        pnl_pct = (
            (close - entry_price) / entry_price if side == 'long'
            else (entry_price - close) / entry_price
        )
        if pnl_pct <= -self.stop_loss_pct:
            self._pead_state.pop(symbol, None)
            return [Signal(symbol=symbol, action='exit', reason='stop-loss')]

        # ── Exit rule 2: max hold (10 trading days) ───────────────────────────
        if bars_held >= self.max_hold_days:
            self._pead_state.pop(symbol, None)
            return [Signal(symbol=symbol, action='exit', reason='max-hold')]

        # ── Exit rule 3: reversal > 2% from watermark ────────────────────────
        if side == 'long':
            peak = ps.get('peak', close)
            if peak > 0 and (peak - close) / peak >= self.reversal_pct:
                self._pead_state.pop(symbol, None)
                return [Signal(symbol=symbol, action='exit', reason='reversal')]
        else:
            trough = ps.get('trough', close)
            if trough > 0 and (close - trough) / trough >= self.reversal_pct:
                self._pead_state.pop(symbol, None)
                return [Signal(symbol=symbol, action='exit', reason='reversal')]

        # Momentum stall → extend hold (no action; max-hold is the safety net)
        return []

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_universe(
        self,
        signals_by_date: dict,
        all_trading_dates: list,
    ) -> dict[str, set[str]]:
        """
        Build {date_str → set(symbol)} so the engine calls on_bar for every
        symbol on every day it may have an open PEAD position.

        A symbol is included from entry_date through entry_date + max_hold + 2.
        The +2 buffer ensures the engine can process the final exit bar even
        if the position reaches max hold exactly on the last allowed day.
        """
        all_sorted = sorted(all_trading_dates)
        idx_map    = {d: i for i, d in enumerate(all_sorted)}
        universe: dict[str, set[str]] = defaultdict(set)

        for entry_date, entries in signals_by_date.items():
            start_idx = idx_map.get(entry_date)
            if start_idx is None:
                continue
            for offset in range(self.max_hold_days + 3):
                future_idx = start_idx + offset
                if future_idx >= len(all_sorted):
                    break
                future_date = all_sorted[future_idx]
                for sym, _ in entries:
                    universe[future_date].add(sym)

        return dict(universe)


# ── Signal pre-computation ─────────────────────────────────────────────────────

def compute_pead_signals(
    earnings_by_sym: dict,       # {sym: [event_dicts]}  from load_all_earnings()
    daily_bars_by_sym: dict,     # {sym: [daily bar dicts]}  t=YYYY-MM-DD
    regime_map: dict,            # {date_str: {'vix_regime': ...}}
    sue_threshold:    float = 0.05,
    min_reaction_pct: float = 0.01,   # ±1% announcement-day reaction required
    min_vol_ratio:    float = 1.5,    # volume ≥ 1.5× 20-day average
    max_hi_dist:      float = 0.15,   # longs: must be within 15% of 52wk high
    lookback_vol:     int   = 20,     # days to compute avg volume
    lookback_52wk:    int   = 252,    # trading days in 52wk high window
    top_n_per_day:    int   = 10,     # max signals on any single entry day
) -> dict[str, list[tuple[str, str]]]:
    """
    Apply all entry filters and return {entry_date: [(sym, side), ...]}.

    Filters applied in order:
        1. SUE ≥ threshold (long) or ≤ -threshold (short)
        2. Reaction-day price change confirms direction
        3. Reaction-day volume ≥ 1.5× 20-day avg
        4. (Longs only) Price within 15% of 52-week high
        5. VIX regime not 'high'

    'reaction_day' = entry_date − 1 trading day.
    This is the day the market first reacted to the earnings (AMC timing assumed).
    """
    signals: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for sym, events in earnings_by_sym.items():
        bars = daily_bars_by_sym.get(sym, [])
        if not bars:
            continue

        # Build date → bar lookup and sorted date list
        bar_by_date: dict[str, dict] = {b['t']: b for b in bars}
        sorted_dates: list[str]       = sorted(bar_by_date)

        # Build rolling 20-day avg volume lookup (indexed by date)
        avg_vol_by_date: dict[str, float] = {}
        for i, d in enumerate(sorted_dates):
            window = sorted_dates[max(0, i - lookback_vol):i]
            vols   = [bar_by_date[dd]['v'] for dd in window if 'v' in bar_by_date[dd]]
            avg_vol_by_date[d] = sum(vols) / len(vols) if vols else 0.0

        # Build rolling 52wk high lookup
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

            # ── Filter 1: SUE threshold ───────────────────────────────────────
            if sue >= sue_threshold:
                side = 'long'
            elif sue <= -sue_threshold:
                side = 'short'
            else:
                continue

            # ── reaction_day = trading day before entry_date ──────────────────
            entry_idx = date_idx_map.get(entry_date)
            if entry_idx is None or entry_idx < 2:
                continue   # need at least 2 prior days
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

            # ── Filter 2: price reaction confirms direction ────────────────────
            if side == 'long'  and reaction_pct < min_reaction_pct:
                continue
            if side == 'short' and reaction_pct > -min_reaction_pct:
                continue

            # ── Filter 3: volume ≥ 1.5× 20-day average ───────────────────────
            reaction_vol = reaction_bar.get('v', 0)
            avg_vol      = avg_vol_by_date.get(reaction_day, 0)
            if avg_vol > 0 and reaction_vol < min_vol_ratio * avg_vol:
                continue

            # ── Filter 4: (longs only) within 15% of 52wk high ───────────────
            if side == 'long':
                hi_52wk        = hi_by_date.get(reaction_day, 0)
                entry_open     = entry_bar['o']
                if hi_52wk > 0 and (hi_52wk - entry_open) / hi_52wk > max_hi_dist:
                    continue

            # ── Filter 5: VIX regime not high ────────────────────────────────
            regime = regime_map.get(entry_date, {})
            if regime.get('vix_regime') == 'high':
                continue

            signals[entry_date].append((sym, side))

    # Cap signals per day to avoid unrealistic crowding
    capped: dict[str, list[tuple[str, str]]] = {}
    for date, entries in signals.items():
        # Sort: longs first (PEAD long side historically stronger), then by sym
        longs  = [(s, d) for s, d in entries if d == 'long']
        shorts = [(s, d) for s, d in entries if d == 'short']
        capped[date] = (longs + shorts)[:top_n_per_day]

    return capped

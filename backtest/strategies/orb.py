"""
ORB (Opening Range Breakout) strategy on "stocks in play".

Evidence basis: QuantConnect replication of Zarattini "stocks in play" study.
Sharpe ~2.4 vs ~0.84 SPY. Edge is in universe selection (high rel-vol + catalyst),
NOT in the OR pattern applied to a static index universe.

Tunable params (swept by evaluate.py during in-sample optimisation):
  or_minutes   : opening range window (1, 5, 15)
  n_vwap_bars  : consecutive bars below VWAP before momentum exit (1-3)
  atr_mult     : ATR-based stop multiplier when OR is tight (0.5-1.5)
  eod_flat_min : minutes before close to force-flat (default 5 → 15:55 ET)
"""
from datetime import time
from .base import Strategy, Signal


class ORBStrategy(Strategy):

    # ---------- defaults (swept by evaluate.py) ----------
    def __init__(
        self,
        or_minutes: int = 5,
        n_vwap_bars: int = 2,
        atr_mult: float = 0.75,
        eod_flat_min: int = 5,
        min_rel_volume: float = 1.5,   # min ratio of today vol to N-day avg
    ):
        self.or_minutes = or_minutes
        self.n_vwap_bars = n_vwap_bars
        self.atr_mult = atr_mult
        self.eod_flat_min = eod_flat_min
        self.min_rel_volume = min_rel_volume

    def params(self) -> dict:
        return {
            'or_minutes': self.or_minutes,
            'n_vwap_bars': self.n_vwap_bars,
            'atr_mult': self.atr_mult,
            'eod_flat_min': self.eod_flat_min,
            'min_rel_volume': self.min_rel_volume,
        }

    # ---------- universe ----------
    def universe(self, date, ctx: dict) -> list[str]:
        """
        In backtest: filter the candidate list by relative volume >= min_rel_volume.
        ctx['candidates'] is populated by data.py from pre-market volume scan.
        ctx['catalyst_list'] optionally supplied from Perplexity research log.
        """
        candidates = ctx.get('candidates', [])
        # Filter by relative volume if the data is available
        filtered = []
        for sym in candidates:
            rel_vol = ctx.get('rel_volume', {}).get(sym, 0.0)
            if rel_vol >= self.min_rel_volume:
                filtered.append(sym)
        # If no volume data available (e.g. thin feed), pass all candidates through
        return filtered if filtered else candidates

    # ---------- per-bar logic ----------
    def on_bar(self, symbol: str, bar: dict, state: dict, ctx: dict) -> list[Signal]:
        signals = []
        bar_time: time = bar['t'].time()
        market_open = time(9, 30)
        eod_exit_time = time(15, 60 - self.eod_flat_min)  # 15:55 by default

        # --- Phase 1: build opening range ---
        or_end = time(9, 30 + self.or_minutes)

        if bar_time < market_open:
            return []

        if bar_time <= or_end:
            # Still inside the opening range — track high/low
            state.setdefault('or_high', bar['h'])
            state.setdefault('or_low', bar['l'])
            state['or_high'] = max(state['or_high'], bar['h'])
            state['or_low'] = min(state['or_low'], bar['l'])
            state['or_set'] = True
            state['or_close'] = bar['c']
            return []

        if not state.get('or_set'):
            return []

        orh = state['or_high']
        orl = state['or_low']
        or_width = orh - orl
        vwap = bar.get('vwap', bar['c'])
        atr = state.get('atr', or_width)  # fallback to OR width if ATR unavailable
        position = ctx.get('positions', {}).get(symbol)

        # --- Phase 2: EOD forced flat (Rule 1) ---
        if bar_time >= eod_exit_time and position:
            signals.append(Signal(
                symbol=symbol,
                action='exit',
                reason='eod-flat',
            ))
            state['position'] = None
            return signals

        # --- Phase 3: monitor open position ---
        if position:
            side = position.get('side', 'long')
            entry = position.get('entry_price', bar['c'])
            target = position.get('target')
            stop = position.get('stop')

            # Rule 5: catastrophic stop
            pnl_pct = (bar['c'] - entry) / entry if side == 'long' else (entry - bar['c']) / entry
            if pnl_pct <= -0.07:
                signals.append(Signal(symbol=symbol, action='exit', reason='stop'))
                state['position'] = None
                return signals

            # Rule 4: measured-move target (partial exit at 50%)
            if target and not position.get('partial_taken'):
                if (side == 'long' and bar['h'] >= target) or (side == 'short' and bar['l'] <= target):
                    signals.append(Signal(
                        symbol=symbol,
                        action='exit',
                        qty=position.get('qty', 0) * 0.5,
                        reason='target',
                    ))
                    position['partial_taken'] = True

            # Rule 3: failed breakout — price returned into OR box
            in_or_box = orl <= bar['c'] <= orh
            if in_or_box:
                state['bars_in_box'] = state.get('bars_in_box', 0) + 1
                if state['bars_in_box'] >= 2:
                    signals.append(Signal(symbol=symbol, action='exit', reason='failed-breakout'))
                    state['position'] = None
                    return signals
            else:
                state['bars_in_box'] = 0

            # Rule 2: VWAP/momentum break
            if side == 'long' and bar['c'] < vwap:
                state['bars_below_vwap'] = state.get('bars_below_vwap', 0) + 1
                if state['bars_below_vwap'] >= self.n_vwap_bars:
                    signals.append(Signal(symbol=symbol, action='exit', reason='momentum-trail'))
                    state['position'] = None
                    return signals
            elif side == 'short' and bar['c'] > vwap:
                state['bars_above_vwap'] = state.get('bars_above_vwap', 0) + 1
                if state['bars_above_vwap'] >= self.n_vwap_bars:
                    signals.append(Signal(symbol=symbol, action='exit', reason='momentum-trail'))
                    state['position'] = None
                    return signals
            else:
                state['bars_below_vwap'] = 0
                state['bars_above_vwap'] = 0

            return signals

        # --- Phase 4: entry signals (no current position) ---
        # Long breakout: close above ORH, above VWAP, volume picking up
        long_vol_ok = bar['v'] > state.get('avg_vol', bar['v']) * 0.8
        if bar['c'] > orh and bar['c'] > vwap and long_vol_ok:
            # Stop: ORL, or ATR-based if OR is unusually tight
            min_stop_dist = atr * self.atr_mult
            stop_price = min(orl, bar['c'] - min_stop_dist)
            target_price = bar['c'] + or_width  # measured move

            signals.append(Signal(
                symbol=symbol,
                action='buy',
                stop=stop_price,
                target=target_price,
                reason='orb-long',
            ))

        # Short breakdown: close below ORL, below VWAP, volume picking up
        elif bar['c'] < orl and bar['c'] < vwap and long_vol_ok:
            max_stop_dist = atr * self.atr_mult
            stop_price = max(orh, bar['c'] + max_stop_dist)
            target_price = bar['c'] - or_width

            signals.append(Signal(
                symbol=symbol,
                action='short',
                stop=stop_price,
                target=target_price,
                reason='orb-short',
            ))

        return signals

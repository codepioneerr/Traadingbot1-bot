"""
Event-driven backtest engine.

Processes minute bars chronologically:
  1. Calls strategy.universe() at market open each day
  2. Calls strategy.on_bar() for each bar of each symbol
  3. Applies fills via the cost model
  4. Tracks equity curve, open positions, and closed trades

Usage:
    from backtest.engine import BacktestEngine
    from backtest.strategies.orb import ORBStrategy
    from backtest.costs import REALISTIC_5
    from backtest.data import load_bars

    engine = BacktestEngine(
        strategy=ORBStrategy(),
        cost_model=REALISTIC_5,
        starting_equity=100_000,
        max_positions=6,
    )
    results = engine.run(bars_by_symbol, spy_bars)
"""
from __future__ import annotations
from datetime import datetime, date
from collections import defaultdict

from .strategies.base import Strategy, Signal
from .costs import CostModel, FRICTIONLESS


class Position:
    def __init__(self, symbol, side, qty, entry_price, stop, target, entry_time, reason):
        self.symbol = symbol
        self.side = side          # 'long' | 'short'
        self.qty = qty
        self.entry_price = entry_price
        self.stop = stop
        self.target = target
        self.entry_time = entry_time
        self.entry_reason = reason
        self.partial_taken = False

    def market_value(self, price: float) -> float:
        if self.side == 'long':
            return price * self.qty
        # Short: reserved entry_price*qty; mark-to-market = entry + unrealised_pnl
        return self.entry_price * self.qty + self.unrealised_pnl(price)

    def unrealised_pnl(self, price: float) -> float:
        if self.side == 'long':
            return (price - self.entry_price) * self.qty
        else:
            return (self.entry_price - price) * self.qty

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'qty': self.qty,
            'entry_price': self.entry_price,
            'stop': self.stop,
            'target': self.target,
        }


class BacktestEngine:

    def __init__(
        self,
        strategy: Strategy,
        cost_model: CostModel = FRICTIONLESS,
        starting_equity: float = 100_000,
        max_positions: int = 6,
        sizing_pct: float = 0.20,   # fraction of equity per position (overridden by ctx if VIX provided)
    ):
        self.strategy = strategy
        self.cost_model = cost_model
        self.starting_equity = starting_equity
        self.max_positions = max_positions
        self.sizing_pct = sizing_pct

        # Runtime state
        self.equity = starting_equity
        self.cash = starting_equity
        self.positions: dict[str, Position] = {}
        self.closed_trades: list[dict] = []
        self.equity_curve: list[float] = [starting_equity]
        self.daily_equity: list[float] = []
        self._per_symbol_state: dict[str, dict] = defaultdict(dict)
        self._last_price: dict[str, float] = {}  # last known price per symbol

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        bars_by_symbol: dict[str, list[dict]],
        spy_bars: list[dict] | None = None,
        ctx_by_date: dict[str, dict] | None = None,
    ) -> dict:
        """
        bars_by_symbol: {symbol: [bar_dict, ...]} — bars pre-sorted ascending by time
        spy_bars: daily SPY bars for benchmark equity curve
        ctx_by_date: optional per-date context (candidates, rel_volume, sizing_mode, etc.)
        Returns dict with equity_curve, trades, daily_equity.
        """
        # Merge all bars into one chronological stream
        all_bars: list[tuple[datetime, str, dict]] = []
        for symbol, bars in bars_by_symbol.items():
            for b in bars:
                raw_t = b['t']
                if isinstance(raw_t, str):
                    raw_t = raw_t.replace('Z', '+00:00')
                    t = datetime.fromisoformat(raw_t)
                else:
                    t = raw_t
                all_bars.append((t, symbol, b))
        all_bars.sort(key=lambda x: x[0])

        current_day: date | None = None
        today_universe: list[str] = []

        for ts, symbol, bar in all_bars:
            day = ts.date()
            bar['t'] = ts  # replace string with datetime

            # New trading day setup
            if day != current_day:
                if current_day is not None:
                    self._record_day_equity(all_bars, current_day)
                current_day = day
                self._per_symbol_state.clear()

                ctx = (ctx_by_date or {}).get(str(day), {})
                ctx['positions'] = {s: p.to_dict() for s, p in self.positions.items()}
                ctx['cash'] = self.cash
                ctx['equity'] = self.equity

                today_universe = self.strategy.universe(day, ctx)

            if symbol not in today_universe:
                continue

            # Build per-bar context
            ctx = (ctx_by_date or {}).get(str(day), {})
            ctx['positions'] = {s: p.to_dict() for s, p in self.positions.items()}
            ctx['cash'] = self.cash
            ctx['equity'] = self.equity

            state = self._per_symbol_state[symbol]
            # Inject current position into state for strategy to read
            if symbol in self.positions:
                state['position'] = self.positions[symbol].to_dict()
                state['position']['partial_taken'] = self.positions[symbol].partial_taken
            else:
                state.pop('position', None)

            signals = self.strategy.on_bar(symbol, bar, state, ctx)
            self._process_signals(signals, symbol, bar, ts)

            # Track last price for all-position equity mark
            self._last_price[symbol] = bar['c']

            # Update equity (mark all positions to last known price)
            self.equity = self.cash + sum(
                p.market_value(self._last_price.get(s, p.entry_price))
                for s, p in self.positions.items()
            )
            self.equity_curve.append(self.equity)

        # Record last day
        if current_day is not None:
            self._record_day_equity(all_bars, current_day)

        return {
            'equity_curve': self.equity_curve,
            'daily_equity': self.daily_equity,
            'trades': self.closed_trades,
            'final_equity': self.equity,
        }

    # ── Signal processing ─────────────────────────────────────────────────────

    def _process_signals(self, signals: list[Signal], symbol: str, bar: dict, ts: datetime):
        for sig in signals:
            if sig.action in ('buy', 'short'):
                self._open_position(sig, bar, ts)
            elif sig.action in ('sell', 'cover', 'exit'):
                self._close_position(sig, symbol, bar, ts)

    def _open_position(self, sig: Signal, bar: dict, ts: datetime):
        if len(self.positions) >= self.max_positions:
            return
        if sig.symbol in self.positions:
            return  # already have one

        fill_price = self.cost_model.fill_price(bar['c'], sig.action)
        position_value = self.equity * self.sizing_pct
        qty = max(1, int(position_value / fill_price))
        cost = qty * fill_price

        if cost > self.cash:
            qty = max(1, int(self.cash / fill_price))
            cost = qty * fill_price

        if qty < 1 or cost > self.cash:
            return

        self.cash -= cost
        self.positions[sig.symbol] = Position(
            symbol=sig.symbol,
            side='long' if sig.action == 'buy' else 'short',
            qty=qty,
            entry_price=fill_price,
            stop=sig.stop,
            target=sig.target,
            entry_time=ts,
            reason=sig.reason,
        )

    def _close_position(self, sig: Signal, symbol: str, bar: dict, ts: datetime):
        pos = self.positions.get(symbol)
        if pos is None:
            return

        # Adverse fill direction: longs sell low, shorts buy-to-cover high
        close_action = 'sell' if pos.side == 'long' else 'buy'
        fill_price = self.cost_model.fill_price(bar['c'], close_action)
        qty = sig.qty if sig.qty else pos.qty

        if pos.side == 'long':
            realised = (fill_price - pos.entry_price) * qty
            self.cash += qty * fill_price
        else:
            realised = (pos.entry_price - fill_price) * qty
            # Return reserved capital + profit (or minus loss)
            self.cash += qty * pos.entry_price + realised

        self.closed_trades.append({
            'symbol': symbol,
            'side': pos.side,
            'qty': qty,
            'entry_price': pos.entry_price,
            'exit_price': fill_price,
            'stop': pos.stop,
            'target': pos.target,
            'entry_time': str(pos.entry_time),
            'exit_time': str(ts),
            'exit_reason': sig.reason,
            'pnl': realised,
        })

        if qty >= pos.qty:
            del self.positions[symbol]
        else:
            pos.qty -= qty
            pos.partial_taken = True

    def _record_day_equity(self, all_bars, day):
        # Mark all open positions to last bar of the day (or last known price)
        day_bars: dict[str, float] = {}
        for ts, symbol, bar in all_bars:
            if ts.date() == day:
                day_bars[symbol] = bar['c']

        eq = self.cash
        for symbol, pos in self.positions.items():
            price = day_bars.get(symbol, self._last_price.get(symbol, pos.entry_price))
            eq += pos.market_value(price)
        self.daily_equity.append(eq)
        self.equity = eq

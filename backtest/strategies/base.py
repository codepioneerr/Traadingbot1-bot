"""
Strategy interface — every strategy implements this contract.
Used by both backtest/engine.py and the live executor.
One code path, two harnesses.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Signal:
    symbol: str
    action: str           # 'buy' | 'sell' | 'short' | 'cover' | 'exit'
    qty: float | None = None      # None → let position manager size it
    stop: float | None = None     # initial stop price
    target: float | None = None   # first target price
    reason: str = ''              # exit-reason label for scorecard
    meta: dict = field(default_factory=dict)


class Strategy(ABC):

    @abstractmethod
    def universe(self, date, ctx: dict) -> list[str]:
        """
        Return the list of tickers to consider for this date.
        ctx contains account state, sizing_mode, catalyst_list, etc.
        Called once per day, before the first bar.
        """

    @abstractmethod
    def on_bar(self, symbol: str, bar: dict, state: dict, ctx: dict) -> list[Signal]:
        """
        Called for every bar of every symbol in today's universe.
        bar: {'t': datetime, 'o': float, 'h': float, 'l': float, 'c': float, 'v': int, 'vwap': float}
        state: per-symbol mutable state dict (persists across bars within a day)
        ctx: read-only context (account, sizing_mode, open_positions, etc.)
        Must be a pure function of inputs — no I/O, no side effects.
        Returns a (possibly empty) list of Signals.
        """

    @abstractmethod
    def params(self) -> dict:
        """
        Return current parameter dict.
        evaluate.py uses this to sweep parameter combinations for in-sample optimisation.
        Example: {'or_minutes': 5, 'n_vwap_bars': 2, 'atr_mult': 0.5}
        """

    def set_params(self, params: dict) -> None:
        """Override to accept a new parameter dict during sweeps."""
        for k, v in params.items():
            if hasattr(self, k):
                setattr(self, k, v)

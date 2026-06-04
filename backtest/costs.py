"""
Transaction cost model.

Alpaca stock commission: $0.
Model slippage as a per-side cost in basis points (bps).

Two standard passes:
  frictionless : 0 bps/side  — "if it can't win here, it can't win anywhere"
  realistic    : 5 bps/side  — also reported at 10 bps for sensitivity
"""


def apply_slippage(price: float, action: str, slippage_bps: float) -> float:
    """
    Returns the fill price after slippage.
    action: 'buy' / 'short' → adverse fill is higher
            'sell' / 'cover' / 'exit' → adverse fill is lower
    """
    factor = slippage_bps / 10_000
    if action in ('buy', 'short'):
        return price * (1 + factor)
    else:
        return price * (1 - factor)


def apply_spread(price: float, action: str, spread_pct: float) -> float:
    """
    Apply half-spread as an additional cost.
    spread_pct: bid/ask spread as a fraction of price (e.g. 0.001 = 0.1%)
    """
    half = price * spread_pct / 2
    if action in ('buy', 'short'):
        return price + half
    else:
        return price - half


class CostModel:
    def __init__(self, slippage_bps: float = 0.0, spread_pct: float = 0.0):
        self.slippage_bps = slippage_bps
        self.spread_pct = spread_pct

    def fill_price(self, price: float, action: str) -> float:
        p = apply_slippage(price, action, self.slippage_bps)
        p = apply_spread(p, action, self.spread_pct)
        return p

    def __repr__(self):
        return f'CostModel(slippage={self.slippage_bps}bps, spread={self.spread_pct*100:.3f}%)'


# Standard passes used by evaluate.py
FRICTIONLESS = CostModel(slippage_bps=0.0, spread_pct=0.0)
REALISTIC_5  = CostModel(slippage_bps=5.0,  spread_pct=0.001)
REALISTIC_10 = CostModel(slippage_bps=10.0, spread_pct=0.001)

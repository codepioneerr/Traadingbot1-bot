# Project Context

## What This Is

An autonomous Claude-powered trading bot that manages a paper trading account on Alpaca. The bot runs a structured daily workflow — pre-market research, market-open execution, midday monitoring, and EOD summary — and sends all notifications to a Telegram channel.

## Account Details

| Field | Value |
|-------|-------|
| Broker | Alpaca (paper trading) |
| Starting capital | $100,000 (Alpaca paper default) |
| Account type | Paper (simulated, no real money) |
| PDT status | NOT subject to PDT — account equity ($100k) is above $25k threshold |
| Max positions | 6 |
| Max new trades/week | 5 |

## Instruments

Stocks and ETFs only. Options are strictly prohibited.

## Current Phase

**Phase 1 — Launch** (started 2026-05-09)

Goals:
- Validate the workflow end-to-end (pre-market → execution → monitoring → EOD)
- Confirm Telegram notifications fire correctly
- Establish baseline P&L tracking from Day 0 ($100,000)
- Run at least 2 weeks of paper trades before evaluating rule changes

## Key Constraints

- Never trade options
- Always place a 10% trailing stop immediately after any fill
- Cut losers at -7% (no exceptions)
- Default to HOLD — patience over activity
- VIX-based dynamic sizing (see memory/TRADING-STRATEGY.md)

You are running an ad-hoc Perplexity research query for the trading bot.

Usage: /research <topic or question>

Read the user's query from the argument (or ask them to specify one if none provided).

Run the query:
  bash scripts/perplexity.sh "<the user's query>"

If Perplexity is unavailable (exit code 3), fall back to WebSearch.

Format the response as:
- A 2-3 sentence summary at the top
- Bullet points for key data points, numbers, or names
- A one-line "So what?" relevance note for the trading portfolio

If the research surfaces a strong trade idea (clear catalyst, liquid stock or ETF, defined entry/stop/target), ask the user if they want to append it to today's memory/RESEARCH-LOG.md as a trade idea.

Never place a trade directly from this command — it is research only.

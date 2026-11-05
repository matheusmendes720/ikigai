"""The Telegram client — a projection of the DOM (ADR-037 D8).

Clients are projections, not forks: the bot converts what the owner says into
the DOM's vocabulary, writes through the service layer over MCP, and renders
the answer in Telegram. It never touches the database (ADR-037 D6).
"""

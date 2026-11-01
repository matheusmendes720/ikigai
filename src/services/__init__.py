"""The service layer: domain rules with no transport concerns.

`services/` is the only layer clients reach (ADR-037 §6 rule 2). The transport
in `src/transport/` translates domain intent into MCP tool calls; nothing below
this line knows that MCP exists.
"""

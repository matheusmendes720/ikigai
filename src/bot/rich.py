"""The report, as a rich message: a table the client renders as a table.

A bot that sends its daily report as `sendMessage` is a client deciding that
structure is not worth carrying. Telegram disagrees: `sendRichMessage` renders
Markdown tables natively, with alignment, and it is the difference between a
report the owner reads and a wall of dashes.

The rules this module keeps, from the Bot API's own limits:

- **32768 characters** in the message, and the payload is cut below that here
  rather than by the API after a rejection.
- **20 columns** in a table. Three are used; the cap is enforced anyway so a
  caller cannot discover it through a 400.
- `rich_message` takes **exactly one** of `markdown`, `html`, `blocks`. This
  module always sends `markdown`, because the text that goes in it is prose
  the agent wrote, and an agent writes Markdown.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

__all__ = [
    "MAX_CHUNK",
    "MAX_COLUMNS",
    "MAX_MARKDOWN",
    "chunk_markdown",
    "markdown_table",
    "plain_table",
    "report_markdown",
    "rich_payload",
]

#: The API's ceiling, with room left for the fence characters.
MAX_MARKDOWN = 32000

#: The API's ceiling on a table's columns.
MAX_COLUMNS = 20

#: One conversational message: under Telegram's 4096-char ceiling with room
#: for the rich wrapper, so a chunk is a single readable message rather than
#: a wall the owner scrolls. Prose is split here, not truncated by the API.
MAX_CHUNK = 3800

Align = str  # "left" | "center" | "right"


def _cell(value: Any) -> str:
    """One table cell: no newline, no bare pipe, no empty cell.

    A `|` inside a cell ends the cell. The escape is a backslash and it works
    in the API's Markdown, but the cheap thing is to not rely on it: the
    caller's data is prose, and prose with a pipe in it is prose that was
    going to break the table anyway.
    """
    text = " ".join(str(value).split())
    if not text:
        return "—"
    return text.replace("|", "\\|")


def markdown_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    aligns: Sequence[Align] | None = None,
) -> str:
    """A Markdown table, header row and alignment row included.

    An empty `rows` is a table with a header and nothing under it — which is
    the honest rendering of "nothing happened today", and better than a
    heading with no table under it at all.
    """
    header = list(headers)[:MAX_COLUMNS]
    if not header:
        raise ValueError("a table needs at least one column")

    marks = list(aligns)[: len(header)] if aligns else ["left"] * len(header)
    while len(marks) < len(header):
        marks.append("left")

    def rule(align: str) -> str:
        if align == "right":
            return "---:"
        if align == "center":
            return ":---:"
        return ":---"

    lines = [
        "| " + " | ".join(_cell(name) for name in header) + " |",
        "|" + "|".join(rule(align) for align in marks) + "|",
    ]
    for row in rows:
        cells = [_cell(value) for value in list(row)[: len(header)]]
        while len(cells) < len(header):
            cells.append("—")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def plain_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    """The same table, for a client that would not render the rich one.

    Aligned with padding, because a bot's fallback is read in the same chat as
    the bot's success — and a fallback that looks like debris teaches the
    owner to trust the report less, not more.
    """
    header = [str(name) for name in headers]
    body = [[" ".join(str(value).split()) or "—" for value in row] for row in rows]
    widths = [len(name) for name in header]
    for row in body:
        for index, cell in enumerate(row[: len(widths)]):
            widths[index] = max(widths[index], len(cell))

    def line(values: Sequence[str]) -> str:
        padded = [value.ljust(widths[index]) for index, value in enumerate(values[: len(widths)])]
        return "  ".join(padded).rstrip()

    out = [line(header), "  ".join("-" * width for width in widths)]
    out.extend(line(row) for row in body)
    return "\n".join(out)


def report_markdown(
    title: str,
    table: str,
    body: str = "",
    footer: str = "",
) -> str:
    """The whole message: a heading, the table, and what the agent said.

    The order is the reader's: what this is, the facts, then the prose. The
    footer carries the receipt (how long it took), which is the last thing
    anyone needs and the first thing a bot tends to put on top.
    """
    blocks = [f"# {title.strip()}", table.strip()]
    prose = body.strip()
    if prose:
        blocks.append(prose)
    receipt = footer.strip()
    if receipt:
        blocks.append(f"*{receipt}*")
    text = "\n\n".join(block for block in blocks if block)
    if len(text) > MAX_MARKDOWN:
        text = text[: MAX_MARKDOWN - 1].rstrip() + "…"
    return text


def _is_fence(line: str) -> bool:
    """A line that opens or closes a fenced code block."""
    return line.lstrip().startswith("```")


def _markdown_blocks(text: str) -> list[str]:
    """The atomic units of prose: a fenced code block stays whole, and the
    prose between fences splits on blank lines. A chunk boundary may fall
    between blocks, never inside a fence."""
    blocks: list[str] = []
    paragraph: list[str] = []
    fence: list[str] | None = None
    for line in text.split("\n"):
        if fence is not None:
            fence.append(line)
            if _is_fence(line) and len(fence) > 1:
                blocks.append("\n".join(fence))
                fence = None
            continue
        if _is_fence(line):
            if paragraph:
                blocks.append("\n".join(paragraph).strip())
                paragraph = []
            fence = [line]
            continue
        if line.strip():
            paragraph.append(line)
        elif paragraph:
            blocks.append("\n".join(paragraph).strip())
            paragraph = []
    if fence is not None:
        blocks.append("\n".join(fence))
    if paragraph:
        blocks.append("\n".join(paragraph).strip())
    return [block for block in blocks if block]


def _split_oversized(block: str, limit: int) -> list[str]:
    """A block too big for one message, split at line boundaries (and a line
    too big at character boundaries). A fenced block re-opens and closes its
    fence on every piece, so each chunk still renders as code."""
    lines = block.split("\n")
    pieces: list[str] = []
    if _is_fence(lines[0]):
        opener = lines[0]
        inner = lines[1:]
        if inner and _is_fence(inner[-1]):
            inner = inner[:-1]
        budget = max(1, limit - len(opener) - len("```") - 2)
        current: list[str] = []
        size = 0
        for line in inner:
            if len(line) > budget:
                if current:
                    pieces.append(opener + "\n" + "\n".join(current) + "\n```")
                    current, size = [], 0
                for start in range(0, len(line), budget):
                    pieces.append(opener + "\n" + line[start : start + budget] + "\n```")
                continue
            if current and size + len(line) + 1 > budget:
                pieces.append(opener + "\n" + "\n".join(current) + "\n```")
                current, size = [], 0
            current.append(line)
            size += len(line) + 1
        if current:
            pieces.append(opener + "\n" + "\n".join(current) + "\n```")
        return pieces
    current_text = ""
    for line in lines:
        candidate = line if not current_text else current_text + "\n" + line
        if len(candidate) <= limit:
            current_text = candidate
            continue
        if current_text:
            pieces.append(current_text)
        if len(line) <= limit:
            current_text = line
        else:
            for start in range(0, len(line), limit):
                pieces.append(line[start : start + limit])
            current_text = ""
    if current_text:
        pieces.append(current_text)
    return pieces


def chunk_markdown(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Split prose into readable messages, each at most `limit` characters,
    at paragraph boundaries. Empty text yields no chunks. A fenced code block
    is never cut in half: an oversized one is split with its fence re-opened
    on every piece. This is what makes a long answer arrive as a few digestible
    messages instead of one truncated wall."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    for block in _markdown_blocks(text):
        if len(block) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized(block, limit))
            continue
        candidate = block if not current else current + "\n\n" + block
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = block
    if current:
        chunks.append(current)
    return chunks


def rich_payload(chat_id: str, markdown: str) -> dict[str, Any]:
    """The body of one `sendRichMessage` call.

    `rich_message` carries exactly one content field — the API reads the
    others as absent, and two of them is a rejection — so this builds the
    object with `markdown` and nothing else.
    """
    text = markdown[:MAX_MARKDOWN]
    return {"chat_id": chat_id, "rich_message": {"markdown": text}}

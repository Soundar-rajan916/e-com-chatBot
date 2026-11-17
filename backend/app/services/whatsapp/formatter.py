"""Markdown to WhatsApp formatting and message chunking utilities."""

import re

# Markdown link regex: [label](url)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
# Relative or empty link regex: [label](/url) or [label]()
RELATIVE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((?!https?://)[^)]*\)")
# Markdown bold: **text** or __text__
BOLD_PATTERN = re.compile(r"(\*\*|__)(.*?)\1")
# Markdown strikethrough: ~~text~~
STRIKE_PATTERN = re.compile(r"~~(.*?)~~")
# Markdown headers: # Header -> *Header*
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
# Bullet list items: - item or * item
BULLET_PATTERN = re.compile(r"^[\*\-]\s+(.+)$", re.MULTILINE)
# Markdown table pattern (at least 2 lines of table rows)
TABLE_PATTERN = re.compile(r"((?:^[ \t]*\|[^\n]+\|[ \t]*\n?){2,})", re.MULTILINE)


def _format_markdown_table(match: re.Match[str]) -> str:
    """Transform markdown tables into clean WhatsApp-friendly bulleted lists."""
    raw_table = match.group(0).strip()
    lines = [l.strip() for l in raw_table.splitlines() if l.strip()]
    if len(lines) < 2:
        return raw_table

    # Header row
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    # Exclude separator lines like |---|---|
    data_lines = [l for l in lines[1:] if not re.match(r"^[\|\s\-:]+$", l)]
    if not data_lines:
        return raw_table

    formatted_rows: list[str] = []
    for line in data_lines:
        cols = [c.strip() for c in line.strip("|").split("|")]
        row_fields: list[str] = []
        order_num = ""
        for h, val in zip(headers, cols):
            # Clean unwanted link wrappers: [text](...) -> text
            val = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", val).strip()
            if not val or val.lower() in ("-", "n/a", "none", "null"):
                continue

            # Clean header name (remove currency indicators like (₹))
            clean_h = re.sub(r"[\(₹\)]", "", h).strip()

            # If this is Order #, highlight it nicely
            if "order" in clean_h.lower() and re.match(r"^ORD-", val, re.IGNORECASE):
                order_num = val
                row_fields.insert(0, f"📦 *Order {val}*")
            else:
                row_fields.append(f"  • *{clean_h}*: {val}")

        if row_fields:
            if not order_num:
                row_fields = [f"• {f.strip()}" for f in row_fields]
            formatted_rows.append("\n".join(row_fields))

    return "\n\n".join(formatted_rows)


def format_for_whatsapp(text: str) -> str:
    """Format markdown text into clean WhatsApp friendly plain text syntax."""
    if not text:
        return ""

    out = text

    # 1. Transform markdown tables into clean bulleted plain text
    out = TABLE_PATTERN.sub(_format_markdown_table, out)

    # 2. Format external web links: [Label](url) -> Label: url (or just url)
    def _replace_link(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        if label.lower() == url.lower():
            return url
        return f"{label}: {url}"

    out = LINK_PATTERN.sub(_replace_link, out)

    # 3. Strip relative/empty links: [Label](/path) -> Label
    out = RELATIVE_LINK_PATTERN.sub(r"\1", out)

    # 4. Format headers: ### Title -> *Title*
    out = HEADER_PATTERN.sub(r"*\2*", out)

    # 5. Format bold: **text** -> *text*
    out = BOLD_PATTERN.sub(r"*\2*", out)

    # 6. Format strikethrough: ~~text~~ -> ~text~
    out = STRIKE_PATTERN.sub(r"~\1~", out)

    # 7. Format bullets: - item -> • item
    out = BULLET_PATTERN.sub(r"• \1", out)

    # 8. Strip inline code backticks: `code` -> code
    out = re.sub(r"`([^`]+)`", r"\1", out)

    # 9. Clean up any leftover table pipe separators or excessive empty lines
    out = re.sub(r"^[\|\s\-:]+$", "", out, flags=re.MULTILINE)
    out = re.sub(r"\n{3,}", "\n\n", out)

    return out.strip()


def chunk_whatsapp_message(text: str, max_chars: int = 3500) -> list[str]:
    """Split message into chunks if exceeding max_chars, keeping paragraph/sentence boundaries."""
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text.strip()

    while len(remaining) > max_chars:
        # Try finding a split point at double newline
        split_idx = remaining.rfind("\n\n", 0, max_chars)
        if split_idx == -1 or split_idx < max_chars // 2:
            # Try single newline
            split_idx = remaining.rfind("\n", 0, max_chars)

        if split_idx == -1 or split_idx < max_chars // 2:
            # Try sentence end
            for punct in (". ", "! ", "? "):
                idx = remaining.rfind(punct, 0, max_chars)
                if idx != -1 and idx > split_idx:
                    split_idx = idx + 1

        if split_idx == -1 or split_idx < max_chars // 4:
            # Fallback: whitespace
            split_idx = remaining.rfind(" ", 0, max_chars)

        if split_idx == -1:
            # Hard limit split
            split_idx = max_chars

        chunk = remaining[:split_idx].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_idx:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks

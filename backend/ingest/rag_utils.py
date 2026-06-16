"""Shared RAG helpers — chunking and text normalization."""
from __future__ import annotations


def chunk_content(text: str, max_chars: int = 1200) -> list[str]:
    """Split long research into paragraph-aware chunks for embedding."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""
    for para in (p.strip() for p in text.split("\n\n") if p.strip()):
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(para) <= max_chars:
            current = para
        else:
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            current = ""
    if current:
        chunks.append(current)
    return chunks

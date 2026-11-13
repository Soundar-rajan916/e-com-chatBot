import asyncio
import hashlib
import re
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory, engine
from app.models import PolicyChunk
from app.services.embeddings import get_embedder

try:
    import pypdf
except ImportError:
    pypdf = None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract plain text from a PDF file using pypdf."""
    if pypdf is None:
        raise ImportError("pypdf is required for PDF ingestion. Run `pip install pypdf`.")
    reader = pypdf.PdfReader(str(pdf_path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n\n".join(pages_text)


def chunk_text(
    text: str, source_name: str, min_chars: int = 300, max_chars: int = 800
) -> list[tuple[str, str]]:
    """
    Heading-based chunker that extracts (section_title, chunk_content).
    Ensures headings are kept inside the chunk text and chunks avoid breaking sentences.
    """
    lines = text.strip().splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = "General Policy"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = stripped.lstrip("#").strip()
        else:
            if stripped:
                current_lines.append(stripped)

    if current_lines:
        sections.append((current_title, current_lines))

    chunks: list[tuple[str, str]] = []

    for title, sec_lines in sections:
        section_body = " ".join(sec_lines)
        full_section = f"## {title}\n{section_body}".strip()

        if len(full_section) <= max_chars:
            chunks.append((title, full_section))
        else:
            # Split by sentences without breaking mid-sentence
            sentences = re.split(r"(?<=[.!?।])\s+", section_body)
            cur_chunk_body = []
            cur_len = len(f"## {title}\n")

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if cur_len + len(sent) + 1 > max_chars and cur_chunk_body:
                    chunk_text = f"## {title}\n" + " ".join(cur_chunk_body)
                    chunks.append((title, chunk_text))
                    cur_chunk_body = [sent]
                    cur_len = len(f"## {title}\n") + len(sent)
                else:
                    cur_chunk_body.append(sent)
                    cur_len += len(sent) + 1

            if cur_chunk_body:
                chunk_text = f"## {title}\n" + " ".join(cur_chunk_body)
                chunks.append((title, chunk_text))

    return chunks


async def ingest_file(session: AsyncSession, file_path: Path, embedder) -> tuple[int, int, int]:
    """
    Ingests a single policy file into policy_chunks table.
    Returns (added, updated, skipped) counts.
    """
    source_name = file_path.name
    lang = "ta" if ("_ta" in source_name or "tamil" in source_name.lower()) else "en"

    if file_path.suffix.lower() == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = file_path.read_text(encoding="utf-8")

    chunks_data = chunk_text(raw_text, source_name)
    print(f"Processing '{source_name}': {len(chunks_data)} chunks found.")

    added = 0
    updated = 0
    skipped = 0

    # Fetch existing chunks for this source
    existing_stmt = select(PolicyChunk).where(PolicyChunk.source_file == source_name)
    existing_result = await session.execute(existing_stmt)
    existing_chunks = {c.chunk_index: c for c in existing_result.scalars().all()}

    to_embed = []

    for idx, (title, content) in enumerate(chunks_data):
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = existing_chunks.get(idx)

        if existing and existing.content_hash == content_hash:
            skipped += 1
            continue

        to_embed.append((idx, title, content, content_hash, existing))

    if to_embed:
        print(f"  Embedding {len(to_embed)} new/updated chunks for {source_name}...")
        texts_to_embed = [item[2] for item in to_embed]
        embeddings = await embedder.embed_documents(texts_to_embed)

        for (idx, title, content, content_hash, existing), emb in zip(to_embed, embeddings):
            if existing:
                existing.section_title = title
                existing.content = content
                existing.content_hash = content_hash
                existing.embedding = emb
                existing.language = lang
                updated += 1
            else:
                new_chunk = PolicyChunk(
                    id=uuid.uuid4(),
                    source_file=source_name,
                    section_title=title,
                    language=lang,
                    chunk_index=idx,
                    content=content,
                    content_hash=content_hash,
                    embedding=emb,
                )
                session.add(new_chunk)
                added += 1

    # Remove any stale chunks (e.g. if file shrank)
    if len(chunks_data) < len(existing_chunks):
        stale_indices = [idx for idx in existing_chunks if idx >= len(chunks_data)]
        if stale_indices:
            del_stmt = delete(PolicyChunk).where(
                PolicyChunk.source_file == source_name,
                PolicyChunk.chunk_index.in_(stale_indices),
            )
            await session.execute(del_stmt)

    await session.commit()
    return added, updated, skipped


async def main():
    policy_dir = Path(__file__).resolve().parent.parent / "data" / "policy"
    if not policy_dir.exists():
        print(f"Policy directory {policy_dir} does not exist.")
        return

    embedder = get_embedder()
    files = sorted(list(policy_dir.glob("*.md")) + list(policy_dir.glob("*.pdf")))

    print(f"Found {len(files)} policy files to ingest.")
    total_added, total_updated, total_skipped = 0, 0, 0

    async with async_session_factory() as session:
        for f in files:
            a, u, s = await ingest_file(session, f, embedder)
            total_added += a
            total_updated += u
            total_skipped += s

    print("\n" + "=" * 50)
    print("POLICY INGESTION SUMMARY:")
    print(f"  Added:   {total_added}")
    print(f"  Updated: {total_updated}")
    print(f"  Skipped: {total_skipped}")
    print("=" * 50)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

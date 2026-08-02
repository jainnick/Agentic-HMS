from pathlib import Path

from app.core.config import get_settings
from app.modules.knowledge.chunking import prepare_chunks
from app.modules.knowledge.extraction import extract_pdf_pages


def main() -> None:
    settings = get_settings()

    pdf_path = Path(
        "sample_hotel_policy.pdf"
    )

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Place a test PDF at: {pdf_path.resolve()}"
        )

    pdf_bytes = pdf_path.read_bytes()

    pages = extract_pdf_pages(
        pdf_bytes,
    )

    chunks = prepare_chunks(
        pages,
        chunk_size_words=settings.knowledge_chunk_size,
        overlap_words=settings.knowledge_chunk_overlap,
    )

    print(
        f"Extracted pages: {len(pages)}"
    )

    print(
        f"Created chunks: {len(chunks)}"
    )

    for chunk in chunks[:3]:
        print()
        print(
            f"Chunk index: {chunk.chunk_index}"
        )
        print(
            f"Page number: {chunk.page_number}"
        )
        print(
            f"Content hash: {chunk.content_hash}"
        )
        print(
            f"Content preview: {chunk.content[:300]}"
        )


if __name__ == "__main__":
    main()
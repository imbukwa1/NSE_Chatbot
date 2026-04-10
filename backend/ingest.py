from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from services.pinecone_service import upsert_documents


REPORTS_DIR = Path(__file__).resolve().parent / "data" / "annual_reports"
ANNUAL_REPORTS_NAMESPACE = "annual_reports"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    tokens = _tokenize(text)
    if not tokens:
        return []

    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(tokens), step):
        chunk_tokens = tokens[start : start + chunk_size]
        if chunk_tokens:
            chunks.append(" ".join(chunk_tokens))
    return chunks


def _metadata_from_filename(pdf_path: Path) -> tuple[str, str]:
    stem = pdf_path.stem.upper()
    ticker_match = re.search(r"[A-Z]{2,5}", stem)
    year_match = re.search(r"(20\d{2})", stem)
    ticker = ticker_match.group(0) if ticker_match else stem.split("_")[0]
    year = year_match.group(1) if year_match else "unknown"
    return ticker, year


def build_pdf_chunks(reports_dir: Path = REPORTS_DIR) -> list[dict[str, Any]]:
    records = []
    for pdf_path in sorted(reports_dir.glob("*.pdf")):
        ticker, year = _metadata_from_filename(pdf_path)
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                for chunk_index, chunk in enumerate(_chunk_text(text)):
                    records.append(
                        {
                            "id": f"{ticker}-{year}-p{page_number}-c{chunk_index}",
                            "ticker": ticker,
                            "year": year,
                            "page": page_number,
                            "text": chunk,
                            "text_preview": chunk[:240],
                        }
                    )
    return records


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    records = build_pdf_chunks()
    result = upsert_documents(records, namespace=ANNUAL_REPORTS_NAMESPACE)
    print(result)


if __name__ == "__main__":
    main()

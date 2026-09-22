"""PDF -> Markdown conversion.

Primary path uses LlamaParse (LlamaCloud API) when ``LLAMA_CLOUD_API_KEY`` is
configured. A local ``pypdf`` fallback keeps the pipeline usable offline and in
tests when no API keys are present.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ParserError(RuntimeError):
    """Raised when a PDF cannot be converted to text/markdown."""


def _parse_with_llamaparse(file_path: str) -> str:
    from llama_parse import LlamaParse

    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        result_type="markdown",
        verbose=False,
        language="en",
    )
    documents = parser.load_data(file_path)
    return "\n\n".join(doc.text for doc in documents if getattr(doc, "text", None))


def _parse_with_pypdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ParserError(
            "pypdf is not installed and LlamaParse is unavailable. "
            "Install 'pypdf' or set LLAMA_CLOUD_API_KEY."
        ) from exc

    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def parse_pdf_to_markdown(
    source: str | bytes | Path,
    *,
    prefer_llamaparse: bool = True,
) -> str:
    """Convert a PDF (path or raw bytes) into Markdown text.

    Falls back from LlamaParse to pypdf automatically.
    """

    # Normalise to a filesystem path.
    tmp_created = False
    if isinstance(source, (bytes, bytearray)):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(bytes(source))
        tmp.close()
        file_path = tmp.name
        tmp_created = True
    else:
        file_path = str(source)

    if not os.path.exists(file_path):
        raise ParserError(f"PDF not found: {file_path}")

    fallback_reason: object = "LlamaParse returned no text"
    try:
        has_llama = prefer_llamaparse and bool(os.getenv("LLAMA_CLOUD_API_KEY"))
        if has_llama:
            try:
                text = _parse_with_llamaparse(file_path)
                if text and text.strip():
                    return text
            except Exception as exc:  # fall through to the local parser
                fallback_reason = exc
        else:
            fallback_reason = "LLAMA_CLOUD_API_KEY not set"

        text = _parse_with_pypdf(file_path)
        if not text.strip():
            raise ParserError(f"No extractable text in PDF ({fallback_reason})")
        return text
    finally:
        if tmp_created:
            try:
                os.unlink(file_path)
            except OSError:
                pass


__all__ = ["parse_pdf_to_markdown", "ParserError"]

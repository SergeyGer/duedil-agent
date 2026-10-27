"""Deterministic offline agents: read a pitch deck, then write a memo from it.

These exist so the hosted demo can be honest. It runs without API keys, so the real LLM
nodes cannot work — and before this module every input produced the same
``Investment Memo — Unknown Startup``, which made the example picker meaningless and
looked like a bug.

What these agents are, precisely:

* :class:`OfflineExtractorLLM` reads the deck with the same idea the real rules use —
  look for a figure next to the words that identify it (``$500M`` near "ARR") — and
  returns the JSON shape the real Extractor returns, marking anything the deck does not
  state as ``[NOT_FOUND]`` instead of guessing.
* :class:`OfflineSupervisorLLM` assembles the six-section memo from the metrics, the
  benchmark verdict and the Red Flags it is handed, quoting them rather than inventing
  analysis.

They are **rules, not judgement**. They cannot weigh a claim and do not pretend to:
every memo they write ends by saying it was assembled offline without a model, and the
UI says the same above the results. Their value is that a different deck produces a
visibly different analysis, and that the missing-data path stays honest.

Imported by the demo only — nothing in ``app.graph`` depends on this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

#: How a figure the deck does not state is reported, in the decks and here alike.
NOT_FOUND = "[NOT_FOUND]"

_AMOUNT_RE = re.compile(
    r"\$\s?(\d[\d,.]*)\s*(billion|million|thousand|bn|mn|[kmb])?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_MAGNITUDE = {
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "thousand": 1e3,
    "k": 1e3,
}

#: Words that identify a figure, in priority order — the first match wins.
_ARR_WORDS = (r"\bARR\b", r"\bannual recurring revenue\b", r"run rate", r"\brevenue\b")
_MRR_WORDS = (r"\bMRR\b", r"\bmonthly recurring revenue\b")
_TAM_WORDS = (r"\bTAM\b", r"total addressable market", r"\baddressable market\b")

_SECTOR_KEYWORDS = (
    ("B2B SaaS", (r"\bsaas\b", r"subscription")),
    ("Marketplace", (r"\bmarketplace\b", r"\bcommission\b")),
    ("Developer tools", (r"\bcode editor\b", r"\bdevelopers\b", r"\bIDE\b")),
    ("Mobility", (r"\bper-ride\b", r"\bridesharing\b", r"\bcar\b")),
    ("Travel", (r"\btravell?ers?\b", r"\bstays?\b", r"\baccommodation\b")),
    ("AI infrastructure", (r"\bagents?\b", r"\bAI\b")),
)


def _magnitude(word: str | None) -> float:
    return _MAGNITUDE.get((word or "").lower(), 1.0)


def _number(raw: str) -> float:
    """``"1,200"`` -> ``1200.0``; tolerant of both separator conventions."""

    cleaned = raw.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", flat) if part.strip()]


def _amounts(sentence: str) -> list[float]:
    return [_number(m.group(1)) * _magnitude(m.group(2)) for m in _AMOUNT_RE.finditer(sentence)]


def format_amount(value: float) -> str:
    """``500_000_000`` -> ``"$500M"``; ``1_200_000`` -> ``"$1.2M"``."""

    for divisor, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if value >= divisor:
            scaled = value / divisor
            text = f"{scaled:.1f}".rstrip("0").rstrip(".")
            return f"${text}{suffix}"
    return f"${value:,.0f}"


def _figure_near(text: str, words: tuple[str, ...]) -> float | None:
    """First amount mentioned in a sentence that also names the figure."""

    for sentence in _sentences(text):
        if any(re.search(word, sentence, re.IGNORECASE) for word in words):
            amounts = _amounts(sentence)
            if amounts:
                return amounts[0]
    return None


def _explicitly_absent(text: str, words: tuple[str, ...]) -> bool:
    """True when the deck itself says the figure is not available."""

    for sentence in _sentences(text):
        if any(re.search(word, sentence, re.IGNORECASE) for word in words) and re.search(
            r"not disclosed|not published|not applicable|not stated|no public|has never published",
            sentence,
            re.IGNORECASE,
        ):
            return True
    return False


#: Lines that describe the document, not the company. A blueprint deck often opens with
#: "STRICTLY CONFIDENTIAL" or "# SLIDE 1: …", and taking that as the company name produced a
#: memo about a company called "SLIDE 1".
_BOILERPLATE = (
    "strictly confidential",
    "confidential",
    "slide ",
    "blueprint",
    "pitch deck",
    "venture pitch",
    "vision",
    "mission",
    "category",
    "visual",
    "on-slide",
    "table of contents",
    "investor",
    "message",
    "headline",
    "copy ",
    "typography",
    "layout",
    "wireframe",
    "executive summary",
    "financial",
    "roadmap",
    "traction",
    "competition",
    "business model",
    "why now",
    "problem",
    "solution",
    "use of funds",
)

#: ``Artisan builds …`` / ``TensorWave is …`` — a company name followed by a verb that describes it.
_BODY_NAME_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'-]*(?:[ \t]+[A-Z][A-Za-z0-9&.'-]*)?)[ \t]+"
    r"(?:builds|offers|provides|develops|raised|serves|powers|delivers)\b"
)

_EXPLICIT_NAME_RE = re.compile(
    r"(?:company|startup|company name)\s*[:\-]\s*([A-Z][A-Za-z0-9&.' -]{1,40})",
    re.IGNORECASE,
)


#: Ordinary words that the sentence pattern ("X builds …") can catch: they describe the text,
#: not the company.
_STOP_NAMES = {
    "this",
    "that",
    "these",
    "the",
    "it",
    "its",
    "our",
    "we",
    "they",
    "their",
    "there",
    "company",
    "startup",
    "team",
    "deck",
    "slide",
    "market",
    "product",
    "platform",
    "solution",
    "business",
    "and",
    "for",
    "with",
    "from",
}


def _looks_like_name(candidate: str) -> bool:
    lowered = (candidate or "").strip().lower()
    if len(lowered) < 2 or len(lowered) > 40:
        return False
    if lowered in _STOP_NAMES:
        return False
    if any(word in lowered for word in _BOILERPLATE):
        return False
    return bool(re.search(r"[A-Za-z]", candidate))


def company_from_filename(name: str) -> str:
    """Derive a readable company name from a deck's file name.

    ``Figure_AI_Pitch_Deck.pdf`` -> ``Figure AI``. The file name is a signal the reader chose,
    and for the reconstruction decks it is the only place the company is named.
    """

    stem = Path(name or "").stem
    stem = re.sub(r"(?i)[-_ ]?(pitch[-_ ]?deck|deck|presentation|slides?)$", "", stem)
    stem = stem.replace("_", " ").replace("-", " ").strip()
    words = []
    for word in stem.split():
        if word.isupper() and len(word) <= 4:  # AI, ML, GPU
            words.append(word)
        elif word.isalpha() and re.search(r"[A-Z]", word[1:]):  # TensorWave keeps its shape
            words.append(word)
        elif word.isalpha():
            words.append(word.capitalize())
        else:
            words.append(word)
    return " ".join(words[:4]).strip()


#: File names that describe a file, not a company.
_GENERIC_FILE_WORDS = {
    "sample",
    "deck",
    "pitch",
    "template",
    "test",
    "demo",
    "file",
    "document",
    "scan",
    "untitled",
    "copy",
    "final",
    "new",
    "presentation",
    "slides",
}


def _specific_filename(name: str) -> str:
    """The company part of a file name, or ``""`` when the name says nothing about the company."""

    candidate = company_from_filename(name)
    words = [word.lower() for word in candidate.split()]
    if not words or all(word in _GENERIC_FILE_WORDS for word in words):
        return ""
    return candidate


def extract_company_name(text: str, deck_name: str = "") -> str:
    """Read the company name from the deck, falling back to the file name.

    An explicit "Company: X" wins, then a body sentence that names the company and says what it
    does ("Artisan builds …"), then the first heading that is not document boilerplate, and
    finally the file name. The order matters: a blueprint deck has no company in its title, and
    guessing from headings produced memos about "SLIDE 1".
    """

    explicit = _EXPLICIT_NAME_RE.search(text or "")
    if explicit and _looks_like_name(explicit.group(1)):
        return explicit.group(1).strip(" *_—–-")

    body = _BODY_NAME_RE.search(text or "")
    if body:
        candidate = body.group(1).splitlines()[0].strip(" *_—–-")
        if _looks_like_name(candidate):
            return candidate

    from_name = _specific_filename(deck_name)
    if _looks_like_name(from_name):
        return from_name

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^#{1,3}\s+\**([^#\n]+?)\**\s*$", stripped)
        candidate = match.group(1) if match else stripped
        candidate = candidate.split(":", 1)[0]
        for stop in (" — ", " – ", " - ", " (", " series ", " pitch", " deck"):
            index = candidate.lower().find(stop)
            if index > 0:
                candidate = candidate[:index]
        candidate = candidate.strip(" *_—–-")
        if _looks_like_name(candidate):
            return candidate

    return "Unknown Startup"


def _team_size(text: str) -> str:
    # Reuse the project's own headcount rule so the offline demo and the live run
    # read "about 300 employees" the same way.
    from .utils import find_team_mentions

    mentions = find_team_mentions(text)
    return str(mentions[0]) if mentions else NOT_FOUND


def _founded_year(text: str) -> str:
    match = re.search(r"\bfounded\s+(?:in\s+)?((?:19|20)\d{2})", text, re.IGNORECASE)
    if not match:
        match = re.search(r"^\s*Founded\s*[:\-—]\s*((?:19|20)\d{2})", text, re.IGNORECASE | re.M)
    return match.group(1) if match else NOT_FOUND


def _founders(text: str) -> list[str]:
    # The value may sit after a separator on the same line ("Team: Jane Doe") or on the
    # line below the label ("**Team**\n\nJane Doe, …") — the pypdf fallback produces the
    # latter, because a PDF heading is its own paragraph.
    match = re.search(
        r"[Ff]ounded by ([^.;\n]+)"
        r"|[Cc]o-?founded by ([^.;\n]+)"
        r"|[Ff]ounders?\s*[:\-—]\s*([^\n]+)"
        r"|\*{0,2}(?:Team|Founders?)\*{0,2}\s*[:\-—]?\s*\n\s*([^\n]+)"
        r"|\*{0,2}(?:Team|Founders?)\*{0,2}\s*[:\-—]\s*([^\n]+)",
        text,
    )
    if not match:
        return []
    raw = next((group for group in match.groups() if group), "")
    raw = re.split(r"\s+(?:in|at)\s+\d{4}|\s+as of\b", raw)[0]
    raw = raw.split(";")[0]
    names = []
    for candidate in re.split(r",| and ", raw):
        cleaned = candidate.strip(" *_().")
        # Drop the trailing company/location fragment ("... , Stockholm") and role notes
        # in brackets ("(CEO)"), then any leading verb the sentence started with.
        # Drop a role note in brackets: "(CEO)", "(chairman)" — with or without its
        # closing bracket, since the sentence may be truncated.
        cleaned = re.split(r"\s*\((?=[A-Za-z])", cleaned)[0]
        cleaned = re.sub(
            r"^(?:co-?)?founded by\s+|^founders?\s*[:\-—]?\s*", "", cleaned, flags=re.I
        )
        # "Anton Osika. Small, senior team" -> "Anton Osika"
        cleaned = cleaned.split(".")[0]
        # A role may be attached with a dash instead of brackets: "Jane Doe — CEO".
        cleaned = re.split(
            r"\s*[—–-]\s*(?=(?:CEO|CTO|CPO|COO|CFO|chairman|founder|president)\b)",
            cleaned,
            flags=re.I,
        )[0]
        cleaned = cleaned.strip(" *_().")
        if not cleaned or len(cleaned.split()) > 4:
            continue
        # A "founder" that is described as a body of people is not a person.
        if re.search(r"\b(team|staff|employees|people|engineers|researchers)\b", cleaned, re.I):
            continue
        if not re.match(r"^[A-Z]", cleaned):
            continue
        names.append(cleaned)
    return names[:3]


def _sector(text: str) -> str:
    for label, patterns in _SECTOR_KEYWORDS:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return label
    return NOT_FOUND


def _business_model(text: str) -> str:
    for sentence in _sentences(text):
        if re.search(r"commission|per[- ]seat|subscription|per[- ]ride|usage", sentence, re.I):
            return sentence[:160]
    return NOT_FOUND


def _leadership_claim(text: str) -> str:
    for sentence in _sentences(text):
        match = re.search(
            r"([^.]*\b(?:leader|leading|largest|fastest|most popular)\b[^.]*)", sentence, re.I
        )
        if match:
            return match.group(1).strip()[:160]
    return NOT_FOUND


def extract_metrics(deck_text: str, website_url: str = "", deck_name: str = "") -> dict[str, Any]:
    """Read the metrics the real Extractor looks for, using the deck's own words."""

    arr = None if _explicitly_absent(deck_text, _ARR_WORDS) else _figure_near(deck_text, _ARR_WORDS)
    mrr = None if _explicitly_absent(deck_text, _MRR_WORDS) else _figure_near(deck_text, _MRR_WORDS)
    tam = None if _explicitly_absent(deck_text, _TAM_WORDS) else _figure_near(deck_text, _TAM_WORDS)

    metrics: dict[str, Any] = {
        "company_name": extract_company_name(deck_text, deck_name),
        "sector": _sector(deck_text),
        "business_model": _business_model(deck_text),
        "founded_year": _founded_year(deck_text),
        "arr": format_amount(arr) if arr else NOT_FOUND,
        "mrr": format_amount(mrr) if mrr else NOT_FOUND,
        "team_size": _team_size(deck_text),
        "tam": format_amount(tam) if tam else NOT_FOUND,
        "founders": _founders(deck_text) or NOT_FOUND,
        "claimed_leadership": _leadership_claim(deck_text),
        "website": website_url or NOT_FOUND,
        "key_claims": _key_claims(deck_text),
    }
    return metrics


def _key_claims(deck_text: str, limit: int = 4) -> list[str]:
    claims = []
    for sentence in _sentences(deck_text):
        if len(sentence) < 40:
            continue
        if re.search(
            r"\b(fastest|leader|leading|largest|first|record|growth|growing|scal)\b", sentence, re.I
        ):
            claims.append(sentence)
        if len(claims) >= limit:
            break
    return claims


class _Response:
    """Minimal stand-in for a LangChain ``AIMessage``."""

    def __init__(self, content: str) -> None:
        self.content = content


class OfflineExtractorLLM:
    """Answers the Extractor prompt with metrics read from the deck in the request."""

    def invoke(self, messages, **_: object) -> _Response:  # noqa: ANN001 - mimic LangChain
        deck = ""
        deck_name = ""
        for message in messages:
            content = str(getattr(message, "content", ""))
            if "SOURCE FILE:" in content:
                head = content.split("SOURCE FILE:", 1)[1].split("\n", 1)[0]
                deck_name = head.strip()
            if "PITCH DECK TEXT:" in content:
                deck = content.split("PITCH DECK TEXT:", 1)[1]
                break
        return _Response(json.dumps(extract_metrics(deck, deck_name=deck_name), ensure_ascii=False))


def _json_block(context: str, label: str) -> dict[str, Any]:
    match = re.search(rf"{label}\s*\(JSON\):\s*(\{{.*?\n\}})", context, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def _clean(text: object, limit: int = 180) -> str:
    """Flatten a fragment of the deck or of the market notes into one readable sentence.

    Deck text arrives with its own markdown headings and line breaks; pasted into a bullet they
    read like a paste accident. This keeps the words, drops the formatting and truncates.
    """

    value = str(text or "")
    value = re.sub(r"^\s*#{1,6}\s*", "", value, flags=re.MULTILINE)
    value = value.replace("|", " ").replace("*", "")
    value = re.sub(r"\s+", " ", value).strip(" -:;,")
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value


_LABELS = {
    "company_name": "Company",
    "arr": "ARR",
    "mrr": "MRR",
    "tam": "TAM",
    "team_size": "Team size",
    "business_model": "Business model",
    "founded_year": "Founded",
    "claimed_leadership": "Claimed leadership",
}

_NOISE_PREFIXES = ("query:", "offline search:")


def _label(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " ").capitalize())


def _currency(metrics: dict[str, Any]) -> str:
    for symbol in ("€", "£", "¥"):
        if any(symbol in str(metrics.get(key) or "") for key in ("arr", "mrr", "tam")):
            return symbol
    return "$"


def _money(value: object, currency: str = "$") -> str:
    if isinstance(value, (int, float)) and value:
        return f"{currency}{value:,.2f}"
    return "not computable"


def _value(value: object) -> str:
    """Render a metric the way a reader expects, not the way the extractor stores it."""

    text = _clean(value, limit=140)
    if not text or text == NOT_FOUND:
        return "— not stated in the deck"
    return text


def build_offline_memo(supervisor_input: str) -> str:
    """Assemble the six-section memo from the supervisor's own context.

    The context already carries the metrics, the benchmark verdict, the market notes and
    the Red Flags, so the memo restates them — no analysis is invented, and the footer
    says the text was assembled without a model.
    """

    metrics = _json_block(supervisor_input, "EXTRACTED METRICS")
    benchmarks = _json_block(supervisor_input, "FINANCIAL BENCHMARKS")

    flags_match = re.search(r"RED FLAGS:\s*(.*?)(?:\n\nWrite|\Z)", supervisor_input, re.DOTALL)
    flags = [
        line.strip("- ").strip()
        for line in (flags_match.group(1) if flags_match else "").splitlines()
        if line.strip().startswith("-")
    ]
    flags = [flag for flag in flags if flag and flag.lower() not in {"none", "no red flags"}]

    market_match = re.search(
        r"EXTERNAL MARKET DATA:\s*(.*?)\n\nRED FLAGS:", supervisor_input, re.DOTALL
    )
    market = (market_match.group(1).strip() if market_match else "") or "(no market data)"

    company = metrics.get("company_name") or "Unknown Startup"
    verdict = benchmarks.get("verdict") or "No financial verdict available."
    status = benchmarks.get("status") or "unknown"

    metric_lines = [
        f"- **{_label(key)}**: "
        + (", ".join(_value(item) for item in value) if isinstance(value, list) else _value(value))
        for key, value in metrics.items()
        if key != "key_claims"
    ]
    claims = [_clean(claim, limit=140) for claim in (metrics.get("key_claims") or [])][:3]
    claims = [claim for claim in claims if claim]
    claims_block = "\n".join(f"- {claim}" for claim in claims) or "- none stated in the deck"

    # `ENVIRONMENT` lines with an empty body mean the search returned nothing: say so rather
    # than quoting the queries as if they were findings.
    market_lines = [
        _clean(line, limit=400)
        for line in market.splitlines()
        if line.strip() and line.strip() != "()"
    ]
    market_body = [line for line in market_lines if not line.lower().startswith(_NOISE_PREFIXES)]
    market_block = (
        "\n".join(market_body)
        if market_body
        else (
            "No external market data was collected for this run — the offline demo does not call "
            "a search provider."
        )
    )

    recommendation = {"above": "INVEST", "below": "REJECT"}.get(status, "DEEP AUDIT")
    flags_count = len(flags)

    return (
        f"# Investment Memo — {company}\n\n"
        "## 1. Executive Summary\n"
        f"Automated first-pass due diligence for **{company}**. The financial audit "
        f"returned **{status}**: {verdict}\n\n"
        + (
            f"The critic raised **{flags_count}** "
            f"{'Red Flag' if flags_count == 1 else 'Red Flags'}, listed in section 5. "
            if flags_count
            else "No Red Flags were raised in this pass. "
        )
        + f"Claims the deck makes about itself:\n{claims_block}\n\n"
        "## 2. Startup Metrics\n"
        + ("\n".join(metric_lines) or "- no metrics extracted from the deck")
        + "\n\n"
        "## 3. Market Analysis\n"
        f"{market_block}\n\n"
        "## 4. Financial Audit\n"
        f"{verdict}\n\n"
        f"- Status: **{status}**\n"
        f"- ARR: {_value(metrics.get('arr'))} | team size: {_value(metrics.get('team_size'))} | "
        f"ARR per employee: {_money(benchmarks.get('arr_per_employee'), _currency(metrics))}\n"
        f"- Benchmark: {_money(benchmarks.get('benchmark_arr_per_employee'), _currency(metrics))} "
        "(B2B SaaS, per employee)\n\n"
        "## 5. Hidden Risks (Red Flags)\n"
        + ("\n".join(f"- {flag}" for flag in flags) or "- none")
        + "\n\n"
        "## 6. Final Recommendation\n"
        f"**{recommendation}**\n\n"
        f"{flags_count} {'Red Flag' if flags_count == 1 else 'Red Flags'} and a "
        f"**{status}** financial audit. This is a first-pass screen produced without a "
        "language model: the figures were read from the deck by rule, and no external market "
        "data was collected. Configure the API keys to get a model's judgement instead.\n"
    )


class OfflineSupervisorLLM:
    """Writes the memo from the metrics, verdict and Red Flags it is handed."""

    def invoke(self, messages, **_: object) -> _Response:  # noqa: ANN001 - mimic LangChain
        context = "\n".join(str(getattr(message, "content", "")) for message in messages)
        return _Response(build_offline_memo(context))


__all__ = [
    "NOT_FOUND",
    "OfflineExtractorLLM",
    "OfflineSupervisorLLM",
    "build_offline_memo",
    "company_from_filename",
    "extract_company_name",
    "extract_metrics",
    "format_amount",
]

#!/usr/bin/env python3
"""Generate example pitch decks for five real IT companies, from public facts only.

Why these are generated rather than downloaded
---------------------------------------------
The original pitch decks of Airbnb and Uber are proprietary documents; even though
some were published for a conference or a fundraise, republishing them in this
repository would be a copyright problem. For companies founded two or three years ago
there is usually no public deck at all.

So every deck here is **written from publicly reported facts about the company** -
funding rounds, disclosed ARR, disclosed headcount, founding year - with the sources
listed on the last slide of each deck. Each one is deliberately labelled as a
reconstructed case study, and each is built so that DueDil.Agent has something
realistic to chew on:

* a claim that external data can corroborate or contradict (headcount, traction),
* numbers in the formats a real deck uses (``$1.2M``, ``~11-50``, ``$14B``),
* at least one figure no public source states, which the pipeline must report as
  ``[NOT_FOUND]`` instead of inventing.

Usage::

    python scripts/make_example_decks.py                  # all five -> examples/
    python scripts/make_example_decks.py cursor           # just one
    python scripts/make_example_decks.py --list
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

DEFAULT_DIR = "examples"

# ---------------------------------------------------------------------------
# Public facts. Every value is attributed on the deck's own sources slide; the
# `as_of` date matters because funding and ARR figures move quickly.
# ---------------------------------------------------------------------------
COMPANIES: list[dict] = [
    {
        "slug": "airbnb",
        "title": "Airbnb — Series B (2011), reconstructed",
        "subtitle": "Marketplace for short-term stays — global category leader",
        "tier": "globally known",
        "founded": "2008",
        "headquarters": "San Francisco, USA",
        "deck_date": "2011 (Series B era)",
        "slides": [
            ("Problem", "Travellers pay hotel prices for accommodation they do not want; "
                        "homeowners sit on unused space they cannot monetise."),
            ("Solution", "A two-sided marketplace: hosts list space, guests book it. "
                         "Trust is handled by profiles, reviews and verified payments."),
            ("Market", "Global travel accommodation. Public analyses put the addressable "
                       "market in the hundreds of billions of dollars; Airbnb itself has "
                       "never published a TAM for the 2011 round."),
            ("Traction (2011)", "Airbnb reported roughly 1 million nights booked and listings "
                                "in the tens of thousands across more than 10,000 cities."),
            ("Business model", "Commission on each booking, charged to guest and host. "
                               "No inventory ownership, no property leases."),
            ("Team", "Brian Chesky (CEO), Joe Gebbia (CPO), Nathan Blecharczyk (CTO). "
                     "Company headcount at the time: about 40 people."),
            ("Funding", "Series B, July 2011: $112M led by Andreessen Horowitz, valuing the "
                        "company at about $1.3B."),
            ("Later reality (context for the reader)", "By its 2020 IPO Airbnb had become a "
                                                       "public company; this deck describes the "
                                                       "2011 position only."),
            ("ARR", "Not disclosed in 2011 — the company reported bookings and nights, not "
                    "recurring revenue."),
        ],
        "sources": [
            "Business Insider — 'Airbnb's first-ever pitch deck' (2011 deck coverage)",
            "TechCrunch / press coverage of the July 2011 $112M Series B at ~$1.3B valuation",
            "Airbnb S-1 filing (2020) — historical context",
        ],
    },
    {
        "slug": "uber",
        "title": "Uber — Series B era (2011), reconstructed",
        "subtitle": "On-demand black car service, expanding city by city",
        "tier": "globally known",
        "founded": "2009",
        "headquarters": "San Francisco, USA",
        "deck_date": "2011 (Series B era)",
        "slides": [
            ("Problem", "Getting a reliable car in a city is slow, opaque and expensive; "
                        "payment is awkward and supply is unpredictable."),
            ("Solution", "Tap a button, a car arrives, payment is automatic. Supply is "
                         "managed centrally per city instead of by dispatch radio."),
            ("Market", "Urban ground transportation. The 2011 deck framed it as the taxi and "
                       "black-car market of a handful of launch cities, not a global TAM."),
            ("Traction (2011)", "Operating in a small number of US cities, with the majority "
                                "of trips in San Francisco; a few tens of thousands of trips "
                                "per month."),
            ("Why it scales", "Each new city is the same playbook: recruit drivers, seed "
                              "demand, reach liquidity. Fixed product cost, repeating launch."),
            ("Business model", "Per-ride commission. No fleet ownership, minimal marginal "
                               "cost per additional trip."),
            ("Team", "Travis Kalanick (CEO), Garrett Camp (chairman). About 30 employees in "
                     "2011."),
            ("Funding", "Series B, December 2011: $32M, following a $11M Series A."),
            ("ARR", "Not applicable at the time — Uber reported gross bookings, not "
                    "recurring revenue."),
        ],
        "sources": [
            "Press coverage of Uber's 2011 Series B ($32M) and Series A ($11M)",
            "TechCrunch reporting on Uber's early city-by-city metrics",
            "Uber S-1 filing (2019) — historical context",
        ],
    },
    {
        "slug": "cursor",
        "title": "Cursor (Anysphere) — reconstructed case study",
        "subtitle": "AI-native code editor — the fastest-scaling B2B software story to date",
        "tier": "fast-growing, founded 2022",
        "founded": "2022",
        "headquarters": "San Francisco, USA",
        "deck_date": "2025",
        "slides": [
            ("Problem", "Developers spend more time reading and editing code than writing it; "
                        "existing assistants autocomplete lines, not intent."),
            ("Solution", "An editor built around a model that understands the whole repository: "
                         "multi-file edits, refactors and questions answered in place."),
            ("Traction", "Reported ARR passed $100M within roughly two years of launch, then "
                         "$500M (mid-2025); vendor and press reporting put it above that by "
                         "the end of 2025."),
            ("Growth", "Reported as the fastest B2B software company to reach $1B ARR — "
                       "roughly two years, against five to seven for the previous generation "
                       "of SaaS leaders."),
            ("Team", "Founded by Michael Truell, Sualeh Asif, Arvid Lunnemark and Aman "
                     "Sanger; engineering-heavy organisation."),
            ("Business model", "Per-seat subscription, individual developers and enterprise "
                               "teams, billed monthly or annually."),
            ("Funding", "Series D, November 2025: $2.3B raised at a $29.3B valuation."),
            ("Market", "[NOT_FOUND] — no audited TAM was published with the round."),
        ],
        "sources": [
            "Businesswire — 'Cursor Secures $2.3 Billion Series D Financing at $29.3 Billion "
            "Valuation' (Nov 2025)",
            "SaaStr — 'Cursor Hit $1B ARR' analysis of reported growth",
            "CNBC / TechCrunch coverage of the 2025 round",
        ],
    },
    {
        "slug": "lovable",
        "title": "Lovable — reconstructed case study",
        "subtitle": "Prompt-to-app builder — Europe's fastest-growing software company",
        "tier": "fast-growing, founded 2023",
        "founded": "2023",
        "headquarters": "Stockholm, Sweden",
        "deck_date": "2026",
        "slides": [
            ("Problem", "Building a product still requires writing code. Non-technical founders "
                        "and product teams cannot turn an idea into working software."),
            ("Solution", "Describe the app in natural language; Lovable generates a full-stack "
                         "web application, deployable and editable."),
            ("Traction", "Crossed $100M ARR around eight months after launch; reported to pass "
                         "$400M ARR by early 2026, adding roughly $100M of revenue in a single "
                         "month."),
            ("Efficiency", "The company reported reaching that run rate with about 146 "
                           "employees — an unusually high revenue-per-headcount ratio."),
            ("Business model", "Subscription with usage-based credits; free tier feeding "
                               "self-serve conversion."),
            ("Team", "Co-founded by Anton Osika. Small, senior team; heavy automation instead "
                     "of headcount."),
            ("Funding", "$400M round at a $13.3B valuation, following earlier rounds through "
                        "2025."),
            ("Market", "[NOT_FOUND] — no audited TAM was published with the round."),
        ],
        "sources": [
            "TechCrunch — 'Lovable says it added $100M in revenue last month alone, with just "
            "146 employees' (Mar 2026)",
            "Tech Funding News — '$400M at $13.3B valuation' coverage",
            "Business Insider — valuation coverage (2026)",
        ],
    },
    {
        "slug": "cognition",
        "title": "Cognition AI — reconstructed case study",
        "subtitle": "Devin, an autonomous software engineer",
        "tier": "fast-growing, founded 2023",
        "founded": "2023",
        "headquarters": "San Francisco, USA",
        "deck_date": "2026",
        "slides": [
            ("Problem", "Software teams spend a large share of their time on routine work: "
                        "migrations, test coverage, ticket triage, dependency upgrades."),
            ("Solution", "Devin, an agent that takes a ticket and works it end to end inside "
                         "its own environment — editing, running tests and opening pull "
                         "requests."),
            ("Traction", "Enterprise deployments reported across financial services and "
                         "technology customers; ARR figures are reported by press, not "
                         "audited."),
            ("Positioning", "Sells autonomous execution rather than assistance: output is a "
                            "pull request, not a suggestion."),
            ("Team", "Co-founded by Scott Wu with a team of competitive-programming "
                     "backgrounds."),
            ("Business model", "Enterprise contracts priced against engineering capacity, "
                               "with usage-based components."),
            ("Funding", "$400M raised at a $10.2B valuation (2025); reported acquisition of "
                        "Windsurf the same year."),
            ("ARR", "[NOT_FOUND] — the company has not published an audited ARR figure."),
            ("Market", "[NOT_FOUND] — no audited TAM was published."),
        ],
        "sources": [
            "Yahoo Finance — 'Cognition AI defies turbulence with a $400M raise at $10.2B "
            "valuation'",
            "Tech Funding News — coverage of the Windsurf acquisition and valuation",
            "Cognition company blog — funding and growth post",
        ],
    },
]

_STYLES = {
    "title": ("Helvetica-Bold", 19, 0),
    "subtitle": ("Helvetica-Oblique", 11.5, 8),
    "meta": ("Helvetica", 9, 6),
    "h": ("Helvetica-Bold", 12.5, 16),
    "p": ("Helvetica", 10, 3),
    "source": ("Helvetica", 8.5, 5),
}


def _wrap(text: str, width: int = 96) -> list[str]:
    """Naive word wrap — enough for a generated deck and keeps the PDF readable."""

    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build(company: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=A4)
    pdf.setTitle(company["title"])
    pdf.setAuthor("DueDil.Agent example data")
    _, height = A4
    y = height - 2.5 * cm

    def line(kind: str, text: str, indent: float = 2.5) -> None:
        nonlocal y
        font, size, before = _STYLES[kind]
        pdf.setFont(font, size)
        for chunk in _wrap(text, 96 if kind in {"p", "source"} else 78):
            y -= before + size + 2
            if y < 2.2 * cm:
                pdf.showPage()
                y = height - 2.5 * cm
                pdf.setFont(font, size)
            pdf.drawString(indent * cm, y, chunk)
            before = 0
        y -= 2

    line("title", company["title"])
    line("subtitle", company["subtitle"])
    line(
        "meta",
        f"Reconstructed case study for DueDil.Agent testing · founded {company['founded']} · "
        f"{company['headquarters']} · figures as of {company['deck_date']}",
    )

    line("h", "About this document")
    line(
        "p",
        "This is not the company's original pitch deck. It is a summary written from publicly "
        "reported facts so that DueDil.Agent has realistic input; the sources are listed on the "
        "last page. Where a figure is not public, the deck says [NOT_FOUND] on purpose — the "
        "pipeline is expected to flag it rather than guess.",
    )

    for heading, body in company["slides"]:
        line("h", heading)
        line("p", body)

    line("h", "Sources")
    for source in company["sources"]:
        line("source", f"- {source}")
    line(
        "source",
        "Compiled for testing purposes. No affiliation with, or endorsement by, the companies "
        "named above.",
    )

    pdf.showPage()
    pdf.save()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if "--list" in args:
        for company in COMPANIES:
            print(f"{company['slug']:10} {company['tier']:24} {company['title']}")
        return 0

    wanted = [a for a in args if not a.startswith("-")] or [c["slug"] for c in COMPANIES]
    out_dir = Path(DEFAULT_DIR)

    unknown = [slug for slug in wanted if slug not in {c["slug"] for c in COMPANIES}]
    if unknown:
        print(f"error: unknown company slug(s): {', '.join(unknown)}", file=sys.stderr)
        print("       use --list to see the available ones", file=sys.stderr)
        return 2

    for company in COMPANIES:
        if company["slug"] not in wanted:
            continue
        path = out_dir / f"{company['slug']}_deck.pdf"
        build(company, path)
        print(f"Wrote example deck: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

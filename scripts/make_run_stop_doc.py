#!/usr/bin/env python3
"""Build ``Run_Stop_Project.docx`` — the personal "how to run / how to stop" walkthrough.

The document is written for the person who owns this machine, not for contributors, and
it is deliberately **not** committed: it contains host-specific notes (paths, UID hints,
Docker Desktop behaviour) and lives only in the working copy. ``.gitignore`` excludes it.

Regenerate it at any time::

    python scripts/make_run_stop_doc.py                 # -> ./Run_Stop_Project.docx
    python scripts/make_run_stop_doc.py --out /tmp/x.docx

``python-docx`` is a development-only dependency. It is installed on demand into the
local environment and is *not* part of ``requirements.txt`` — the runtime image must not
carry a document library it never uses.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
except ImportError:  # pragma: no cover - convenience path for a fresh machine
    print("python-docx is missing; installing it into the current environment ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "python-docx"])
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "Run_Stop_Project.docx"

ACCENT = RGBColor(0x1A, 0x4D, 0x8F)
MUTED = RGBColor(0x5A, 0x64, 0x70)
CODE_BG = "F2F4F7"
NOTE_BG = "FFF8E1"
OK_BG = "EAF7EE"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def shade(paragraph, colour: str) -> None:
    """Give a paragraph a background colour (Word has no style for that)."""

    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), colour)
    properties.append(shading)


def code(document: Document, text: str) -> None:
    """A monospaced, shaded, copy-pasteable command block."""

    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.left_indent = Inches(0.12)
    shade(paragraph, CODE_BG)
    run = paragraph.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    # Word needs the font set on the run's rPr for non-ASCII and for older versions.
    run._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")


def callout(document: Document, text: str, *, kind: str = "note", bold_prefix: str = "") -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    shade(paragraph, NOTE_BG if kind == "note" else OK_BG)
    if bold_prefix:
        run = paragraph.add_run(bold_prefix)
        run.bold = True
    paragraph.add_run(text)


def bullets(document: Document, items: list[str]) -> None:
    for item in items:
        document.add_paragraph(item, style="List Bullet")


def numbered(document: Document, items: list[str]) -> None:
    for item in items:
        document.add_paragraph(item, style="List Number")


def table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    grid = document.add_table(rows=1, cols=len(headers))
    grid.style = "Light Grid Accent 1"
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, header in zip(grid.rows[0].cells, headers, strict=True):
        cell.text = ""
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
    for row in rows:
        cells = grid.add_row().cells
        for cell, value in zip(cells, row, strict=True):
            cell.text = value
    document.add_paragraph()


def field(paragraph, instruction: str) -> None:
    """Insert a Word field code (used for the auto-updating table of contents)."""

    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, end):
        run._r.append(element)


def setup(document: Document) -> None:
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)

    for name, size in (("Heading 1", 20), ("Heading 2", 15), ("Heading 3", 12.5)):
        style = styles[name]
        style.font.name = "Calibri Light"
        style.font.size = Pt(size)
        style.font.color.rgb = ACCENT

    section = document.sections[0]
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.9)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    header = section.header.paragraphs[0]
    header.text = "DueDil.Agent — Run & Stop Guide"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if header.runs:
        header.runs[0].font.size = Pt(9)
        header.runs[0].font.color.rgb = MUTED

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(
        "Personal copy — not part of the repository (Run_Stop_Project.docx)"
    ).font.size = Pt(8)
    if footer.runs:
        footer.runs[0].font.color.rgb = MUTED


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def build(output: Path) -> Path:
    document = Document()
    setup(document)

    # --- cover -------------------------------------------------------------
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("DueDil.Agent")
    run.font.size = Pt(30)
    run.font.bold = True
    run.font.color.rgb = ACCENT

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(
        "How to start the project when you want to work on it,\nand how to stop it when you switch to another project"
    )
    run.font.size = Pt(13)
    run.font.color.rgb = MUTED

    document.add_paragraph()
    callout(
        document,
        "Nothing in this project starts by itself. The containers use the restart policy "
        "“no”, so after a server reboot — or after Docker Desktop restarts — they stay down "
        "until you explicitly start them. Nothing here holds a port or memory while you work "
        "on something else.",
        kind="ok",
        bold_prefix="In one sentence: ",
    )

    document.add_paragraph()
    table(
        document,
        ["Where you work", "What you need", "Shortest command"],
        [
            ["Windows laptop (VS Code)", "Docker Desktop running", r".\start.cmd"],
            ["Linux server (terminal / SSH)", "Docker Engine running", "./start.sh"],
            ["Either machine, inside VS Code", "Dev Containers extension", "Reopen in Container"],
        ],
    )

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Contents")
    run.bold = True
    run.font.size = Pt(12)
    field(paragraph, r'TOC \o "1-2" \h \z \u')
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = note.add_run(
        "(If the contents look empty: click it and press F9, or use References → Update Table.)"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED

    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # --- 1. what runs ------------------------------------------------------
    document.add_heading("1. What actually runs", level=1)
    document.add_paragraph(
        "The project has one long-running container and one one-off tool. Both are defined in "
        "docker-compose.yml and neither starts on its own."
    )
    table(
        document,
        ["Name", "What it is", "Starts when", "Address"],
        [
            [
                "duedil-agent-ui",
                "The Streamlit web application",
                "./start.sh, Docker Desktop, or VS Code",
                "http://localhost:8501",
            ],
            [
                "duedil-agent-cli",
                "Command-line runs (no server)",
                "Only when you ask for it; exits when the run finishes",
                "—",
            ],
            [
                "duedil-agent_duedil-data",
                "Volume holding generated memos (persists across stops)",
                "—",
                "inside Docker",
            ],
        ],
    )
    document.add_paragraph(
        "There is no database, no message broker and no background worker: the only thing that "
        "can occupy this machine is the web application on port 8501."
    )

    document.add_heading("Why nothing starts by itself", level=2)
    document.add_paragraph(
        "Docker can restart containers automatically. This project switched that off on purpose "
        '— the compose file sets restart: "no" for both services. Verified behaviour:'
    )
    bullets(
        document,
        [
            "After a server reboot the containers stay stopped; the Docker service itself may start, but no container of this project does.",
            "After a Docker Desktop restart on Windows the same applies.",
            "Port 8501 is free for other projects as soon as you stop this one.",
            "Two projects that use the same port can therefore not collide: only the one you started holds it.",
        ],
    )

    # --- 2. Windows --------------------------------------------------------
    document.add_heading("2. Start and stop on Windows (laptop)", level=1)
    document.add_paragraph(
        "Prerequisite: Docker Desktop is installed and running. If the whale icon in the task bar "
        "is animating, wait for it to settle — the scripts check this and tell you if it is not ready."
    )

    document.add_heading("Start", level=2)
    document.add_paragraph("Option A — one double-click, no typing:")
    numbered(
        document,
        [
            "Open the project folder in File Explorer (the folder that contains docker-compose.yml).",
            "Double-click start.cmd.",
            "Wait for the line “ok app is up: http://localhost:8501”, then open http://localhost:8501.",
        ],
    )
    document.add_paragraph("Option B — from a terminal (PowerShell, recommended for daily work):")
    code(document, "cd C:\\path\\to\\duedil-agent\n.\\start.cmd")
    document.add_paragraph("Option C — from VS Code's integrated terminal (PowerShell):")
    code(document, "cd C:\\path\\to\\duedil-agent\n.\\scripts\\project.ps1 start")
    callout(
        document,
        "If PowerShell blocks the script, allow it for this window only: "
        "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass — then run the command again.",
    )

    document.add_heading("Stop", level=2)
    document.add_paragraph("Any of these frees the machine completely:")
    code(
        document,
        "REM double-click, or from a terminal:\n.\\stop.cmd\n\nREM the same thing, explicitly:\n.\\scripts\\project.ps1 stop",
    )
    document.add_paragraph(
        "Stopping removes the containers but keeps the volume with the generated memos, so the next "
        "start is fast and your reports are still there."
    )

    document.add_heading("Check what is running", level=2)
    code(document, ".\\scripts\\project.ps1 status")
    document.add_paragraph(
        "The output lists this project's containers, their health, the address, and it repeats the "
        "auto-start settings so you can confirm that nothing is set to come back on its own."
    )

    # --- 3. Linux ----------------------------------------------------------
    document.add_heading("3. Start and stop on the Linux server", level=1)
    document.add_paragraph(
        "Same commands, bash spelling. Run them from the project directory (on this server that is "
        "/root/projects/duedil-agent/duedil-agent)."
    )
    code(
        document,
        "cd /root/projects/duedil-agent/duedil-agent\n"
        "./start.sh                 # build if needed, start, wait until healthy\n"
        "./stop.sh                  # stop and free the port\n"
        "./scripts/project.sh status",
    )
    table(
        document,
        ["Command", "What it does"],
        [
            ["./start.sh", "Starts everything and waits until the app answers"],
            ["./stop.sh", "Stops and removes the containers; the data volume is kept"],
            ["./scripts/project.sh restart", "Stop, then start again"],
            ["./scripts/project.sh logs", "Follow the application log (Ctrl+C to leave)"],
            ["./scripts/project.sh status", "Containers, health, address, auto-start settings"],
            ["./scripts/project.sh shell", "A shell inside the running container"],
            ["./scripts/project.sh cli <deck.pdf> [url]", "One CLI run in a throwaway container"],
            ["./scripts/project.sh rebuild", "Rebuild without cache, then restart"],
            ["./scripts/project.sh clean", "Remove containers, volumes and the image"],
        ],
    )
    callout(
        document,
        "Because the stack is started from a terminal here, closing the SSH session does not stop it — "
        "the containers keep running on the server until you run ./stop.sh. Use "
        "./scripts/project.sh status after reconnecting to see where you left things.",
    )

    document.add_heading("Optional: keep Docker itself from starting at boot", level=2)
    document.add_paragraph(
        "The project's containers already never start by themselves. If you also want the Docker "
        "daemon itself to stay down until you need it, the script can do that (it asks for sudo):"
    )
    code(
        document,
        "./scripts/project.sh autostart off     # docker will not start on reboot\n"
        "./scripts/project.sh autostart on      # back to the normal behaviour\n"
        "./scripts/project.sh autostart status  # show the current setting",
    )
    document.add_paragraph(
        "Trade-off worth knowing: with the daemon disabled you must start it by hand after every "
        "reboot (sudo systemctl start docker) before ./start.sh can work. The default "
        "(daemon on, containers off) is usually the comfortable middle ground."
    )

    # --- 4. VS Code / dev container ---------------------------------------
    document.add_heading("4. Working in VS Code: the Dev Containers extension", level=1)
    document.add_paragraph(
        "The repository ships a dev container configuration, so VS Code can develop inside the very "
        "same image the project deploys. Nothing else needs to be installed on the laptop — no "
        "Python, no dependency management."
    )

    document.add_heading("One-time setup", level=2)
    numbered(
        document,
        [
            "Install the extension “Dev Containers” (publisher: Microsoft) in VS Code.",
            "Make sure Docker Desktop (Windows) or Docker Engine (Linux) is running.",
            "Open the project folder in VS Code: File → Open Folder…",
            "Press F1 (or Ctrl+Shift+P) and run: Dev Containers: Reopen in Container.",
            "The first run builds the image and takes a few minutes; later runs take seconds.",
        ],
    )
    document.add_paragraph(
        "When it finishes, the bottom-left corner shows “Dev Container: DueDil.Agent”, and the "
        "application is already running inside the container — open http://localhost:8501, VS Code "
        "forwards the port for you."
    )

    document.add_heading("What you get inside the container", level=2)
    bullets(
        document,
        [
            "Python 3.12 with the exact pinned dependencies from requirements.txt.",
            "ruff, pytest and pytest-cov in /app/.venv, wired into VS Code as the interpreter.",
            "The same non-root user (duedil) as production, so permission problems surface here rather than in deployment.",
            "The whole repository mounted at /app: edits are visible on the host immediately.",
        ],
    )

    document.add_heading("Leaving the container", level=2)
    document.add_paragraph(
        "Closing the VS Code window stops the containers (the configuration asks Docker Compose to "
        "shut down), which is exactly what you want when switching projects. To stay in the "
        "container but free the machine, use the command palette entry "
        "“Dev Containers: Reopen Folder Locally”."
    )

    document.add_heading("How to stop everything while you are inside the container", level=2)
    callout(
        document,
        "While VS Code is attached, this container IS the application container — the very one the "
        "stop command would remove. Asking it to remove itself is why the direct approach does not "
        "work: the Docker CLI is not installed inside the container and the Docker socket is not "
        "mounted into it. The two reliable ways below both take a few seconds.",
        bold_prefix="Why you cannot simply type stop in the container's terminal: ",
    )
    document.add_paragraph(
        "Way 1 — from VS Code (recommended; it also returns you to your laptop):"
    )
    numbered(
        document,
        [
            "Press F1 (or Ctrl+Shift+P) to open the Command Palette.",
            "Type and run: Dev Containers: Reopen Folder Locally.",
            "Wait until the window reloads in the bottom-left corner it should no longer say “Dev Container”.",
            "Everything is stopped now: VS Code ran the stop for the compose project, and the app is no longer listening on port 8501.",
            "Optional confirmation in the local terminal: .\\scripts\\project.ps1 status (Windows) or ./scripts/project.sh status (Linux). It should report that no container of the project exists.",
        ],
    )
    document.add_paragraph("Way 2 — a second terminal outside the container:")
    numbered(
        document,
        [
            "Open a normal terminal on the host (Windows Terminal / PowerShell, or an SSH session to the Linux server). Do not use the terminal inside VS Code — it lives in the container.",
            "Run the stop command: .\\stop.cmd on Windows, or ./stop.sh on the server.",
            "VS Code notices that the container is gone and offers to reopen the folder locally (or does it on its own). The containers, including the one VS Code was attached to, are removed.",
        ],
    )
    document.add_paragraph(
        "Way 3 — close the window. Clicking the X on the VS Code window also stops the stack, because "
        "the configuration sets shutdownAction: stopCompose. Use this when you are leaving for the day "
        "and do not need to confirm anything."
    )
    note = document.add_paragraph()
    run = note.add_run(
        "If you ever do want the Docker CLI inside the container, it can be added by mounting "
        "/var/run/docker.sock and installing the client — but that grants the container control over "
        "every container on the machine, and stopping the stack would still kill the session you are "
        "typing in. The three ways above exist so that is unnecessary."
    )
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    callout(
        document,
        "The dev container keeps using port 8501. If it is already taken because you started the app "
        "with ./start.sh, stop that first (./stop.sh) — or the two will compete for the same port.",
    )

    document.add_heading("Switching between projects", level=2)
    document.add_paragraph(
        "Each project should have its own compose project name, so their containers and volumes are "
        "kept apart. This one uses the name duedil-agent (set in docker-compose.yml). Practical "
        "routine when moving to another project:"
    )
    numbered(
        document,
        [
            "In the project you are leaving, run the stop command (or close the VS Code dev container window).",
            "Confirm with status that no container of it is left: ./scripts/project.sh status.",
            "Open the other project in VS Code and start it the same way.",
        ],
    )
    document.add_paragraph(
        "If two projects still conflict, the usual cause is the same host port. Change the published "
        "port of one of them (for example 8502:8501 in its docker-compose.yml) or stop the other "
        "project — the status command shows which container holds a port."
    )

    # --- 5. everyday recipes ----------------------------------------------
    document.add_heading("5. Everyday recipes", level=1)
    table(
        document,
        ["I want to…", "Windows", "Linux server"],
        [
            ["Start working", r".\start.cmd", "./start.sh"],
            ["Stop for today", r".\stop.cmd", "./stop.sh"],
            [
                "See if it is running",
                r".\scripts\project.ps1 status",
                "./scripts/project.sh status",
            ],
            ["Watch the log", r".\scripts\project.ps1 logs", "./scripts/project.sh logs"],
            [
                "Run a deck through the CLI",
                r".\scripts\project.ps1 cli examples\cursor_deck.pdf https://cursor.com",
                "./scripts/project.sh cli examples/cursor_deck.pdf https://cursor.com",
            ],
            [
                "Rebuild after changing dependencies",
                r".\scripts\project.ps1 rebuild",
                "./scripts/project.sh rebuild",
            ],
            [
                "Remove everything of this project",
                r".\scripts\project.ps1 clean",
                "./scripts/project.sh clean",
            ],
        ],
    )

    # --- 6. troubleshooting -----------------------------------------------
    document.add_heading("6. If something does not work", level=1)
    table(
        document,
        ["Symptom", "What it means", "What to do"],
        [
            [
                "“the Docker daemon is not running”",
                "Docker Desktop is closed (Windows) or the daemon is stopped (Linux).",
                "Start Docker Desktop and wait for the whale icon to settle; on Linux: sudo systemctl start docker",
            ],
            [
                "“port is already allocated”",
                "Another container or program holds 8501 — often this project started twice.",
                "Run the status command, then stop the other project or this one; or publish a different port.",
            ],
            [
                "The page does not open, but the container is “healthy”",
                "The port is published but the browser has a stale tab.",
                "Open http://localhost:8501 again, or check the address printed by status.",
            ],
            [
                "The container restarts again and again",
                "A crash inside the application — the restart policy is “no”, so this is not Docker's doing.",
                "Run the logs command and read the traceback; rebuild if you changed dependencies.",
            ],
            [
                "Files created in the container belong to another user",
                "On Linux, the container user id differs from yours.",
                "Keep editing through VS Code, which matches the ids, or run: sudo chown -R $USER:$USER .",
            ],
            [
                "The app answers with the offline warning banner",
                "No API keys are configured, so no language model runs.",
                "Expected for a demo. Put your keys in .env (copy env.example) and restart to get full analysis.",
            ],
        ],
    )

    document.add_heading("Where to look for more", level=2)
    bullets(
        document,
        [
            "README.md — what the project does and how it is deployed.",
            "docs/wiki/Installation-and-Deployment.md — full local, Docker and cloud instructions.",
            "docs/wiki/Troubleshooting.md — problems seen in practice and how they were solved.",
            "docker-compose.yml — the services, ports and volumes described in this document.",
        ],
    )

    document.add_paragraph()
    callout(
        document,
        "This file is generated by scripts/make_run_stop_doc.py and is listed in .gitignore, so it "
        "stays on your machine and never appears in the repository. Regenerate it with "
        "make devcontainer-doc after the scripts change.",
        kind="ok",
        bold_prefix="About this document: ",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the personal Run & Stop guide (docx).")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    path = build(Path(args.out))
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

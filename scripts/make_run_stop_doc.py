#!/usr/bin/env python3
"""Build the personal "how to run / how to stop" walkthrough as a Word document.

The document is written for the person who owns this machine, not for contributors, and
it is deliberately **not** committed: it contains host-specific notes (paths, UID hints,
Docker Desktop behaviour) and lives only in the working copy. ``.gitignore`` excludes it.

Regenerate it at any time::

    python scripts/make_run_stop_doc.py                       # Russian -> Run_Stop_Project.docx
    python scripts/make_run_stop_doc.py --lang ru --out Run_Stop_Project_RU.docx
    python scripts/make_run_stop_doc.py --lang en --out Run_Stop_Project_EN.docx

``python-docx`` is a development-only dependency. It is installed on demand into the
local environment and is *not* part of ``requirements.txt`` — the runtime image must not
carry a document library it never uses.

Each language is a list of blocks (``Content.blocks``); the renderer knows nothing about
the topic, so adding a language means adding one list.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
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

Block = tuple
"""One element of the document: ``(kind, ...)`` where kind is h1/h2/p/code/bullets/
steps/table/callout/callout_bold/toc/muted/space."""


@dataclass
class Content:
    """Everything the renderer needs, in presentation order."""

    lang: str
    title: str
    subtitle: str
    header: str
    footer: str
    toc_title: str
    toc_hint: str
    blocks: list[Block] = field(default_factory=list)


# ---------------------------------------------------------------------------
# rendering helpers
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
    fonts = run._element.rPr.rFonts
    for slot in ("w:ascii", "w:hAnsi", "w:cs"):
        # `w:cs` matters for Cyrillic: without it Word falls back to a proportional face
        # and the block stops looking like code.
        fonts.set(qn(slot), "Consolas")


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


def toc_field(paragraph) -> None:
    """Insert the Word field code that produces an auto-updating table of contents."""

    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-2" \h \z \u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, end):
        run._r.append(element)


def setup(document: Document, content: Content) -> None:
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.element.rPr.rFonts.set(qn("w:cs"), "Calibri")

    for name, size in (("Heading 1", 20), ("Heading 2", 15), ("Heading 3", 12.5)):
        style = styles[name]
        style.font.name = "Calibri Light"
        style.font.size = Pt(size)
        style.font.color.rgb = ACCENT
        style.element.rPr.rFonts.set(qn("w:cs"), "Calibri Light")

    section = document.sections[0]
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.9)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    header = section.header.paragraphs[0]
    header.text = content.header
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if header.runs:
        header.runs[0].font.size = Pt(9)
        header.runs[0].font.color.rgb = MUTED

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(content.footer).font.size = Pt(8)
    if footer.runs:
        footer.runs[0].font.color.rgb = MUTED


def render(document: Document, content: Content) -> None:
    """Draw the cover and every content block."""

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(content.title)
    run.font.size = Pt(30)
    run.font.bold = True
    run.font.color.rgb = ACCENT

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(content.subtitle)
    run.font.size = Pt(13)
    run.font.color.rgb = MUTED

    for block in content.blocks:
        kind = block[0]
        if kind == "h1":
            document.add_heading(block[1], level=1)
        elif kind == "h2":
            document.add_heading(block[1], level=2)
        elif kind == "p":
            document.add_paragraph(block[1])
        elif kind == "code":
            code(document, block[1])
        elif kind == "bullets":
            bullets(document, block[1])
        elif kind == "steps":
            numbered(document, block[1])
        elif kind == "table":
            table(document, block[1], block[2])
        elif kind == "callout":
            callout(document, block[1], kind=block[2] if len(block) > 2 else "note")
        elif kind == "callout_bold":
            callout(
                document,
                block[2],
                kind=block[3] if len(block) > 3 else "note",
                bold_prefix=block[1],
            )
        elif kind == "muted":
            paragraph = document.add_paragraph()
            run = paragraph.add_run(block[1])
            run.font.size = Pt(9)
            run.font.color.rgb = MUTED
        elif kind == "space":
            document.add_paragraph()
        elif kind == "toc":
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(content.toc_title)
            run.bold = True
            run.font.size = Pt(12)
            toc_field(paragraph)
            note = document.add_paragraph()
            note.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = note.add_run(content.toc_hint)
            run.font.size = Pt(9)
            run.font.color.rgb = MUTED
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        else:  # pragma: no cover - a typo in a content list
            raise ValueError(f"unknown block type {kind!r}")


# ---------------------------------------------------------------------------
# content — Russian
# ---------------------------------------------------------------------------
RU = Content(
    lang="ru",
    title="DueDil.Agent",
    subtitle=(
        "Как запустить проект, когда вы хотите с ним работать,\n"
        "и как остановить его, когда нужно переключиться на другой проект"
    ),
    header="DueDil.Agent — запуск и остановка",
    footer="Личная копия — не входит в репозиторий (Run_Stop_Project.docx)",
    toc_title="Содержание",
    toc_hint="(Если содержание пустое: щёлкните по нему и нажмите F9, либо «Ссылки → Обновить таблицу».)",
    blocks=[
        (
            "callout_bold",
            "Одним предложением: ",
            "в этом проекте ничего не запускается само. У контейнеров политика перезапуска «no», "
            "поэтому после перезагрузки сервера — или после перезапуска Docker Desktop — они остаются "
            "остановленными, пока вы не запустите их явно. Ничего отсюда не занимает порт и память, "
            "пока вы работаете над другим проектом.",
            "ok",
        ),
        ("space",),
        (
            "table",
            ["Где вы работаете", "Что нужно", "Самая короткая команда"],
            [
                ["Ноутбук Windows (VS Code)", "Запущен Docker Desktop", r".\start.cmd"],
                ["Сервер Linux (терминал / SSH)", "Запущен Docker Engine", "./start.sh"],
                [
                    "Любая машина, внутри VS Code",
                    "Расширение Dev Containers",
                    "Reopen in Container",
                ],
            ],
        ),
        ("toc",),
        # --- 1 -----------------------------------------------------------------
        ("h1", "1. Что именно запускается"),
        (
            "p",
            "В проекте один длительно работающий контейнер и одна разовая утилита. Оба описаны в "
            "docker-compose.yml, и ни один из них не стартует сам.",
        ),
        (
            "table",
            ["Имя", "Что это", "Когда запускается", "Адрес"],
            [
                [
                    "duedil-agent-ui",
                    "Веб-приложение Streamlit",
                    "./start.sh, Docker Desktop или VS Code",
                    "http://localhost:8501",
                ],
                [
                    "duedil-agent-cli",
                    "Запуски из командной строки (без сервера)",
                    "Только по вашему запросу; завершается вместе с прогоном",
                    "—",
                ],
                [
                    "duedil-agent_duedil-data",
                    "Том с готовыми меморандумами (живёт между остановками)",
                    "—",
                    "внутри Docker",
                ],
            ],
        ),
        (
            "p",
            "Базы данных, брокера сообщений и фоновых воркеров здесь нет: единственное, что может "
            "занять машину, — веб-приложение на порту 8501.",
        ),
        ("h2", "Почему ничего не стартует само"),
        (
            "p",
            "Docker умеет перезапускать контейнеры автоматически. Здесь это выключено намеренно — в "
            'compose-файле у обоих сервисов стоит restart: "no". Проверенное поведение:',
        ),
        (
            "bullets",
            [
                "После перезагрузки сервера контейнеры остаются остановленными: сам Docker может "
                "запуститься, но ни один контейнер этого проекта — нет.",
                "После перезапуска Docker Desktop в Windows действует то же правило.",
                "Порт 8501 освобождается сразу после остановки — его могут занять другие проекты.",
                "Два проекта с одинаковым портом не конфликтуют: порт держит только тот, который вы "
                "запустили.",
            ],
        ),
        # --- 2 -----------------------------------------------------------------
        ("h1", "2. Запуск и остановка в Windows (ноутбук)"),
        (
            "p",
            "Что нужно заранее: установленный и запущенный Docker Desktop. Если значок кита в панели "
            "задач анимирован — дождитесь, пока он успокоится: скрипты это проверяют и скажут, если "
            "Docker ещё не готов.",
        ),
        ("h2", "Запуск"),
        ("p", "Вариант А — один двойной клик, без набора команд:"),
        (
            "steps",
            [
                "Откройте папку проекта в Проводнике (ту, где лежит docker-compose.yml).",
                "Дважды щёлкните start.cmd.",
                "Дождитесь строки «ok app is up: http://localhost:8501» и откройте http://localhost:8501.",
            ],
        ),
        ("p", "Вариант Б — из терминала (PowerShell, рекомендую для ежедневной работы):"),
        ("code", "cd C:\\путь\\к\\duedil-agent\n.\\start.cmd"),
        ("p", "Вариант В — из встроенного терминала VS Code (PowerShell):"),
        ("code", "cd C:\\путь\\к\\duedil-agent\n.\\scripts\\project.ps1 start"),
        (
            "callout",
            "Если PowerShell блокирует скрипт, разрешите его только для текущего окна: "
            "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass — и повторите команду.",
        ),
        ("h2", "Остановка"),
        ("p", "Любая из этих команд полностью освобождает машину:"),
        (
            "code",
            "REM двойной клик или из терминала:\n"
            ".\\stop.cmd\n\n"
            "REM то же самое, явной командой:\n"
            ".\\scripts\\project.ps1 stop",
        ),
        (
            "p",
            "При остановке контейнеры удаляются, а том с готовыми меморандумами остаётся: следующий "
            "запуск будет быстрым, а отчёты — на месте.",
        ),
        ("h2", "Проверить, что сейчас работает"),
        ("code", ".\\scripts\\project.ps1 status"),
        (
            "p",
            "Команда показывает контейнеры проекта, их состояние, адрес и повторяет настройки "
            "автозапуска — чтобы можно было убедиться, что ничего не поднимется само.",
        ),
        # --- 3 -----------------------------------------------------------------
        ("h1", "3. Запуск и остановка на сервере Linux"),
        (
            "p",
            "Те же команды в синтаксисе bash. Выполняйте их из папки проекта (на этом сервере это "
            "/root/projects/duedil-agent/duedil-agent).",
        ),
        (
            "code",
            "cd /root/projects/duedil-agent/duedil-agent\n"
            "./start.sh                 # соберёт при необходимости, запустит, дождётся готовности\n"
            "./stop.sh                  # остановит и освободит порт\n"
            "./scripts/project.sh status",
        ),
        (
            "table",
            ["Команда", "Что делает"],
            [
                ["./start.sh", "Запускает всё и ждёт, пока приложение начнёт отвечать"],
                ["./stop.sh", "Останавливает и удаляет контейнеры; том с данными сохраняется"],
                ["./scripts/project.sh restart", "Остановить и запустить заново"],
                ["./scripts/project.sh logs", "Смотреть лог приложения (выход — Ctrl+C)"],
                [
                    "./scripts/project.sh status",
                    "Контейнеры, состояние, адрес, настройки автозапуска",
                ],
                ["./scripts/project.sh shell", "Оболочка внутри работающего контейнера"],
                [
                    "./scripts/project.sh cli <дек.pdf> [url]",
                    "Один прогон CLI во временном контейнере",
                ],
                ["./scripts/project.sh rebuild", "Пересобрать без кэша и перезапустить"],
                ["./scripts/project.sh clean", "Удалить контейнеры, тома и образ"],
            ],
        ),
        (
            "callout",
            "Стек запускается из терминала, поэтому закрытие SSH-сессии его не останавливает: "
            "контейнеры продолжат работать на сервере, пока вы не выполните ./stop.sh. После "
            "переподключения посмотрите ./scripts/project.sh status, чтобы понять, в каком состоянии "
            "вы всё оставили.",
        ),
        ("h2", "Дополнительно: запретить запуск самого Docker при загрузке"),
        (
            "p",
            "Контейнеры проекта и так не поднимаются сами. Если вы хотите, чтобы и сам демон Docker не "
            "стартовал до необходимости, скрипт умеет это настроить (потребуется sudo):",
        ),
        (
            "code",
            "./scripts/project.sh autostart off     # docker не будет стартовать при загрузке\n"
            "./scripts/project.sh autostart on      # вернуть обычное поведение\n"
            "./scripts/project.sh autostart status  # показать текущую настройку",
        ),
        (
            "p",
            "Компромисс, о котором стоит знать: при выключенном демоне после каждой перезагрузки его "
            "придётся запускать вручную (sudo systemctl start docker), иначе ./start.sh не сработает. "
            "Настройка по умолчанию — демон включён, контейнеры выключены — обычно удобнее.",
        ),
        # --- 4 -----------------------------------------------------------------
        ("h1", "4. Работа в VS Code: расширение Dev Containers"),
        (
            "p",
            "В репозитории уже есть настройка dev-контейнера, поэтому VS Code может работать внутри "
            "того же образа, который проект разворачивает. На ноутбуке больше ничего устанавливать не "
            "нужно — ни Python, ни менеджер зависимостей.",
        ),
        ("h2", "Разовая настройка"),
        (
            "steps",
            [
                "Установите в VS Code расширение «Dev Containers» (издатель: Microsoft).",
                "Убедитесь, что запущен Docker Desktop (Windows) или Docker Engine (Linux).",
                "Откройте папку проекта в VS Code: File → Open Folder…",
                "Нажмите F1 (или Ctrl+Shift+P) и выполните: Dev Containers: Reopen in Container.",
                "Первый запуск собирает образ и занимает несколько минут; последующие — секунды.",
            ],
        ),
        (
            "p",
            "Когда всё готово, в левом нижнем углу появится «Dev Container: DueDil.Agent», а "
            "приложение уже работает внутри контейнера — открывайте http://localhost:8501, VS Code "
            "пробрасывает порт сам.",
        ),
        ("h2", "Что вы получаете внутри контейнера"),
        (
            "bullets",
            [
                "Python 3.12 с теми же версиями зависимостей, что и в requirements.txt.",
                "ruff, pytest и pytest-cov в /app/.venv, подключённые в VS Code как интерпретатор.",
                "Тот же непривилегированный пользователь (duedil), что и в продакшене, поэтому "
                "проблемы с правами видны здесь, а не при развёртывании.",
                "Весь репозиторий смонтирован в /app: правки сразу видны на хосте.",
            ],
        ),
        ("h2", "Выход из контейнера"),
        (
            "p",
            "Закрытие окна VS Code останавливает контейнеры (в настройке указано, что Docker Compose "
            "нужно остановить) — это как раз то, что требуется при переключении на другой проект. "
            "Если нужно остаться в контейнере, но освободить машину, используйте в палитре команд "
            "пункт «Dev Containers: Reopen Folder Locally».",
        ),
        ("h2", "Как остановить всё, находясь внутри контейнера"),
        (
            "callout_bold",
            "Почему нельзя просто набрать stop внутри контейнера: ",
            "пока VS Code подключён, этот контейнер и есть контейнер приложения — тот самый, который "
            "команда остановки должна удалить. Просьба удалить себя и есть причина, по которой прямой "
            "путь не работает: Docker CLI внутри контейнера не установлен, а сокет Docker в него не "
            "смонтирован. Способы ниже занимают несколько секунд.",
        ),
        ("p", "Способ 1 — из VS Code (рекомендую; он же возвращает вас на ноутбук):"),
        (
            "steps",
            [
                "Нажмите F1 (или Ctrl+Shift+P), чтобы открыть палитру команд.",
                "Наберите и выполните: Dev Containers: Reopen Folder Locally.",
                "Дождитесь перезагрузки окна: в левом нижнем углу надпись «Dev Container» должна "
                "исчезнуть.",
                "Всё остановлено: VS Code сам выполнил остановку compose-проекта, и приложение больше "
                "не слушает порт 8501.",
                "Проверка (необязательно), уже в локальном терминале: .\\scripts\\project.ps1 status "
                "(Windows) или ./scripts/project.sh status (Linux) — команда должна ответить, что "
                "контейнеров проекта нет.",
            ],
        ),
        ("p", "Способ 2 — второй терминал, вне контейнера:"),
        (
            "steps",
            [
                "Откройте обычный терминал на хосте (Windows Terminal / PowerShell либо SSH-сессию к "
                "серверу Linux). Не терминал внутри VS Code — он живёт в контейнере.",
                "Выполните команду остановки: .\\stop.cmd в Windows или ./stop.sh на сервере.",
                "VS Code заметит, что контейнер исчез, и предложит вернуться к локальному окну (или "
                "сделает это сам). Контейнеры, включая тот, к которому был подключён VS Code, удалены.",
            ],
        ),
        (
            "p",
            "Способ 3 — закрыть окно. Крестик в окне VS Code тоже останавливает стек: в настройке "
            "указано shutdownAction: stopCompose. Удобно, когда уходите на день и подтверждать ничего "
            "не нужно.",
        ),
        (
            "muted",
            "Если когда-нибудь понадобится Docker CLI внутри контейнера, это делается монтированием "
            "/var/run/docker.sock и установкой клиента — но тогда контейнер получит управление всеми "
            "контейнерами на машине, а остановка стека всё равно оборвёт сессию, из которой вы "
            "печатаете. Способы выше существуют, чтобы этого не требовалось.",
        ),
        ("h2", "Переключение между проектами"),
        (
            "p",
            "У каждого проекта должно быть своё имя compose-проекта, чтобы контейнеры и тома не "
            "смешивались. Здесь используется имя duedil-agent (задано в docker-compose.yml). "
            "Практический порядок при переходе на другой проект:",
        ),
        (
            "steps",
            [
                "В проекте, который покидаете, выполните команду остановки (или закройте окно "
                "dev-контейнера VS Code).",
                "Убедитесь командой status, что от него не осталось контейнеров: "
                "./scripts/project.sh status.",
                "Откройте другой проект в VS Code и запустите его тем же способом.",
            ],
        ),
        (
            "p",
            "Если два проекта всё же конфликтуют, причина обычно в одном и том же порту на хосте. "
            "Измените публикуемый порт у одного из них (например, 8502:8501 в его docker-compose.yml) "
            "или остановите другой проект — команда status показывает, какой контейнер держит порт.",
        ),
        # --- 5 -----------------------------------------------------------------
        ("h1", "5. Команды на каждый день"),
        (
            "table",
            ["Хочу…", "Windows", "Сервер Linux"],
            [
                ["Начать работу", r".\start.cmd", "./start.sh"],
                ["Закончить на сегодня", r".\stop.cmd", "./stop.sh"],
                [
                    "Посмотреть, что запущено",
                    r".\scripts\project.ps1 status",
                    "./scripts/project.sh status",
                ],
                ["Смотреть лог", r".\scripts\project.ps1 logs", "./scripts/project.sh logs"],
                [
                    "Прогнать дек через CLI",
                    r".\scripts\project.ps1 cli examples\cursor_deck.pdf https://cursor.com",
                    "./scripts/project.sh cli examples/cursor_deck.pdf https://cursor.com",
                ],
                [
                    "Пересобрать после смены зависимостей",
                    r".\scripts\project.ps1 rebuild",
                    "./scripts/project.sh rebuild",
                ],
                [
                    "Удалить всё, что относится к проекту",
                    r".\scripts\project.ps1 clean",
                    "./scripts/project.sh clean",
                ],
            ],
        ),
        # --- 6 -----------------------------------------------------------------
        ("h1", "6. Если что-то не работает"),
        (
            "table",
            ["Симптом", "Что это значит", "Что делать"],
            [
                [
                    "«the Docker daemon is not running»",
                    "Docker Desktop закрыт (Windows) или демон остановлен (Linux).",
                    "Запустите Docker Desktop и дождитесь, пока значок успокоится; в Linux: "
                    "sudo systemctl start docker",
                ],
                [
                    "«port is already allocated»",
                    "Порт 8501 занят другим контейнером или программой — часто это тот же проект, "
                    "запущенный дважды.",
                    "Выполните status, затем остановите другой проект или этот; либо опубликуйте "
                    "другой порт.",
                ],
                [
                    "Страница не открывается, но контейнер «healthy»",
                    "Порт опубликован, но во вкладке браузера остался старый адрес.",
                    "Откройте http://localhost:8501 заново или сверьте адрес, который печатает status.",
                ],
                [
                    "Контейнер перезапускается снова и снова",
                    "Падение внутри приложения — политика перезапуска «no», значит это не Docker.",
                    "Посмотрите логи командой logs и прочитайте traceback; если меняли зависимости — "
                    "пересоберите (rebuild).",
                ],
                [
                    "Файлы, созданные в контейнере, принадлежат другому пользователю",
                    "В Linux идентификатор пользователя в контейнере отличается от вашего.",
                    "Работайте через VS Code — он согласует идентификаторы; либо выполните: "
                    "sudo chown -R $USER:$USER .",
                ],
                [
                    "Приложение показывает предупреждение об офлайн-режиме",
                    "Ключи API не настроены, поэтому языковая модель не запускается.",
                    "Для демонстрации это ожидаемо. Скопируйте env.example в .env, впишите ключи и "
                    "перезапустите — получите полный анализ.",
                ],
            ],
        ),
        ("h2", "Где искать подробности"),
        (
            "bullets",
            [
                "README.md — что делает проект и как он разворачивается.",
                "docs/wiki/Installation-and-Deployment.md — полные инструкции: локально, Docker, облако.",
                "docs/wiki/Troubleshooting.md — проблемы, встреченные на практике, и их решения.",
                "docker-compose.yml — сервисы, порты и тома, описанные в этом документе.",
            ],
        ),
        ("space",),
        (
            "callout_bold",
            "Об этом документе: ",
            "файл создаётся скриптом scripts/make_run_stop_doc.py и указан в .gitignore, поэтому "
            "остаётся на вашей машине и никогда не попадает в репозиторий. Пересоздать после правок "
            "скриптов: python scripts/make_run_stop_doc.py --lang ru.",
            "ok",
        ),
    ],
)


# ---------------------------------------------------------------------------
# content — English
# ---------------------------------------------------------------------------
EN = Content(
    lang="en",
    title="DueDil.Agent",
    subtitle=(
        "How to start the project when you want to work on it,\n"
        "and how to stop it when you switch to another project"
    ),
    header="DueDil.Agent — Run & Stop Guide",
    footer="Personal copy — not part of the repository (Run_Stop_Project.docx)",
    toc_title="Contents",
    toc_hint="(If the contents look empty: click it and press F9, or use References → Update Table.)",
    blocks=[
        (
            "callout_bold",
            "In one sentence: ",
            "nothing in this project starts by itself. The containers use the restart policy “no”, so "
            "after a server reboot — or after Docker Desktop restarts — they stay down until you "
            "explicitly start them. Nothing here holds a port or memory while you work on something "
            "else.",
            "ok",
        ),
        ("space",),
        (
            "table",
            ["Where you work", "What you need", "Shortest command"],
            [
                ["Windows laptop (VS Code)", "Docker Desktop running", r".\start.cmd"],
                ["Linux server (terminal / SSH)", "Docker Engine running", "./start.sh"],
                [
                    "Either machine, inside VS Code",
                    "Dev Containers extension",
                    "Reopen in Container",
                ],
            ],
        ),
        ("toc",),
        ("h1", "1. What actually runs"),
        (
            "p",
            "The project has one long-running container and one one-off tool. Both are defined in "
            "docker-compose.yml and neither starts on its own.",
        ),
        (
            "table",
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
        ),
        (
            "p",
            "There is no database, no message broker and no background worker: the only thing that can "
            "occupy this machine is the web application on port 8501.",
        ),
        ("h2", "Why nothing starts by itself"),
        (
            "p",
            "Docker can restart containers automatically. This project switched that off on purpose — "
            'the compose file sets restart: "no" for both services. Verified behaviour:',
        ),
        (
            "bullets",
            [
                "After a server reboot the containers stay stopped; the Docker service itself may "
                "start, but no container of this project does.",
                "After a Docker Desktop restart on Windows the same applies.",
                "Port 8501 is free for other projects as soon as you stop this one.",
                "Two projects that use the same port cannot collide: only the one you started holds it.",
            ],
        ),
        ("h1", "2. Start and stop on Windows (laptop)"),
        (
            "p",
            "Prerequisite: Docker Desktop is installed and running. If the whale icon in the task bar "
            "is animating, wait for it to settle — the scripts check this and tell you if it is not "
            "ready.",
        ),
        ("h2", "Start"),
        ("p", "Option A — one double-click, no typing:"),
        (
            "steps",
            [
                "Open the project folder in File Explorer (the one with docker-compose.yml).",
                "Double-click start.cmd.",
                "Wait for “ok app is up: http://localhost:8501”, then open http://localhost:8501.",
            ],
        ),
        ("p", "Option B — from a terminal (PowerShell, recommended for daily work):"),
        ("code", "cd C:\\path\\to\\duedil-agent\n.\\start.cmd"),
        ("p", "Option C — from VS Code's integrated terminal (PowerShell):"),
        ("code", "cd C:\\path\\to\\duedil-agent\n.\\scripts\\project.ps1 start"),
        (
            "callout",
            "If PowerShell blocks the script, allow it for this window only: "
            "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass — then run the command again.",
        ),
        ("h2", "Stop"),
        ("p", "Any of these frees the machine completely:"),
        (
            "code",
            "REM double-click, or from a terminal:\n"
            ".\\stop.cmd\n\n"
            "REM the same thing, explicitly:\n"
            ".\\scripts\\project.ps1 stop",
        ),
        (
            "p",
            "Stopping removes the containers but keeps the volume with the generated memos, so the next "
            "start is fast and your reports are still there.",
        ),
        ("h2", "Check what is running"),
        ("code", ".\\scripts\\project.ps1 status"),
        (
            "p",
            "The output lists this project's containers, their health, the address, and it repeats the "
            "auto-start settings so you can confirm that nothing is set to come back on its own.",
        ),
        ("h1", "3. Start and stop on the Linux server"),
        (
            "p",
            "Same commands, bash spelling. Run them from the project directory (on this server that is "
            "/root/projects/duedil-agent/duedil-agent).",
        ),
        (
            "code",
            "cd /root/projects/duedil-agent/duedil-agent\n"
            "./start.sh                 # build if needed, start, wait until healthy\n"
            "./stop.sh                  # stop and free the port\n"
            "./scripts/project.sh status",
        ),
        (
            "table",
            ["Command", "What it does"],
            [
                ["./start.sh", "Starts everything and waits until the app answers"],
                ["./stop.sh", "Stops and removes the containers; the data volume is kept"],
                ["./scripts/project.sh restart", "Stop, then start again"],
                ["./scripts/project.sh logs", "Follow the application log (Ctrl+C to leave)"],
                ["./scripts/project.sh status", "Containers, health, address, auto-start settings"],
                ["./scripts/project.sh shell", "A shell inside the running container"],
                [
                    "./scripts/project.sh cli <deck.pdf> [url]",
                    "One CLI run in a throwaway container",
                ],
                ["./scripts/project.sh rebuild", "Rebuild without cache, then restart"],
                ["./scripts/project.sh clean", "Remove containers, volumes and the image"],
            ],
        ),
        (
            "callout",
            "Because the stack is started from a terminal here, closing the SSH session does not stop "
            "it — the containers keep running on the server until you run ./stop.sh. Use "
            "./scripts/project.sh status after reconnecting to see where you left things.",
        ),
        ("h2", "Optional: keep Docker itself from starting at boot"),
        (
            "p",
            "The project's containers already never start by themselves. If you also want the Docker "
            "daemon itself to stay down until you need it, the script can do that (it asks for sudo):",
        ),
        (
            "code",
            "./scripts/project.sh autostart off     # docker will not start on reboot\n"
            "./scripts/project.sh autostart on      # back to the normal behaviour\n"
            "./scripts/project.sh autostart status  # show the current setting",
        ),
        (
            "p",
            "Trade-off worth knowing: with the daemon disabled you must start it by hand after every "
            "reboot (sudo systemctl start docker) before ./start.sh can work. The default — daemon on, "
            "containers off — is usually the comfortable middle ground.",
        ),
        ("h1", "4. Working in VS Code: the Dev Containers extension"),
        (
            "p",
            "The repository ships a dev container configuration, so VS Code can develop inside the very "
            "same image the project deploys. Nothing else needs to be installed on the laptop — no "
            "Python, no dependency management.",
        ),
        ("h2", "One-time setup"),
        (
            "steps",
            [
                "Install the extension “Dev Containers” (publisher: Microsoft) in VS Code.",
                "Make sure Docker Desktop (Windows) or Docker Engine (Linux) is running.",
                "Open the project folder in VS Code: File → Open Folder…",
                "Press F1 (or Ctrl+Shift+P) and run: Dev Containers: Reopen in Container.",
                "The first run builds the image and takes a few minutes; later runs take seconds.",
            ],
        ),
        (
            "p",
            "When it finishes, the bottom-left corner shows “Dev Container: DueDil.Agent”, and the "
            "application is already running inside the container — open http://localhost:8501, VS Code "
            "forwards the port for you.",
        ),
        ("h2", "What you get inside the container"),
        (
            "bullets",
            [
                "Python 3.12 with the exact pinned dependencies from requirements.txt.",
                "ruff, pytest and pytest-cov in /app/.venv, wired into VS Code as the interpreter.",
                "The same non-root user (duedil) as production, so permission problems surface here "
                "rather than in deployment.",
                "The whole repository mounted at /app: edits are visible on the host immediately.",
            ],
        ),
        ("h2", "Leaving the container"),
        (
            "p",
            "Closing the VS Code window stops the containers (the configuration asks Docker Compose to "
            "shut down), which is exactly what you want when switching projects. To stay in the "
            "container but free the machine, use the command palette entry “Dev Containers: Reopen "
            "Folder Locally”.",
        ),
        ("h2", "How to stop everything while you are inside the container"),
        (
            "callout_bold",
            "Why you cannot simply type stop in the container: ",
            "while VS Code is attached, this container IS the application container — the very one the "
            "stop command would remove. Asking it to remove itself is why the direct approach does not "
            "work: the Docker CLI is not installed inside the container and the Docker socket is not "
            "mounted into it. The ways below each take a few seconds.",
        ),
        ("p", "Way 1 — from VS Code (recommended; it also returns you to your laptop):"),
        (
            "steps",
            [
                "Press F1 (or Ctrl+Shift+P) to open the Command Palette.",
                "Type and run: Dev Containers: Reopen Folder Locally.",
                "Wait until the window reloads: the bottom-left corner should no longer say “Dev "
                "Container”.",
                "Everything is stopped now: VS Code ran the stop for the compose project, and the app "
                "no longer listens on port 8501.",
                "Optional confirmation in the local terminal: .\\scripts\\project.ps1 status (Windows) or "
                "./scripts/project.sh status (Linux) — it should report that no container of the project "
                "exists.",
            ],
        ),
        ("p", "Way 2 — a second terminal outside the container:"),
        (
            "steps",
            [
                "Open a normal terminal on the host (Windows Terminal / PowerShell, or an SSH session to "
                "the Linux server). Do not use the terminal inside VS Code — it lives in the container.",
                "Run the stop command: .\\stop.cmd on Windows, or ./stop.sh on the server.",
                "VS Code notices that the container is gone and offers to reopen the folder locally (or "
                "does it on its own). The containers, including the one VS Code was attached to, are "
                "removed.",
            ],
        ),
        (
            "p",
            "Way 3 — close the window. Clicking the X on the VS Code window also stops the stack, because "
            "the configuration sets shutdownAction: stopCompose. Use this when you are leaving for the "
            "day and do not need to confirm anything.",
        ),
        (
            "muted",
            "If you ever do want the Docker CLI inside the container, it can be added by mounting "
            "/var/run/docker.sock and installing the client — but that grants the container control "
            "over every container on the machine, and stopping the stack would still kill the session "
            "you are typing in. The ways above exist so that is unnecessary.",
        ),
        ("h2", "Switching between projects"),
        (
            "p",
            "Each project should have its own compose project name, so their containers and volumes are "
            "kept apart. This one uses the name duedil-agent (set in docker-compose.yml). Practical "
            "routine when moving to another project:",
        ),
        (
            "steps",
            [
                "In the project you are leaving, run the stop command (or close the VS Code dev "
                "container window).",
                "Confirm with status that no container of it is left: ./scripts/project.sh status.",
                "Open the other project in VS Code and start it the same way.",
            ],
        ),
        (
            "p",
            "If two projects still conflict, the usual cause is the same host port. Change the published "
            "port of one of them (for example 8502:8501 in its docker-compose.yml) or stop the other "
            "project — the status command shows which container holds a port.",
        ),
        ("h1", "5. Everyday recipes"),
        (
            "table",
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
        ),
        ("h1", "6. If something does not work"),
        (
            "table",
            ["Symptom", "What it means", "What to do"],
            [
                [
                    "“the Docker daemon is not running”",
                    "Docker Desktop is closed (Windows) or the daemon is stopped (Linux).",
                    "Start Docker Desktop and wait for the whale icon to settle; on Linux: "
                    "sudo systemctl start docker",
                ],
                [
                    "“port is already allocated”",
                    "Another container or program holds 8501 — often this project started twice.",
                    "Run the status command, then stop the other project or this one; or publish a "
                    "different port.",
                ],
                [
                    "The page does not open, but the container is “healthy”",
                    "The port is published but the browser has a stale tab.",
                    "Open http://localhost:8501 again, or check the address printed by status.",
                ],
                [
                    "The container restarts again and again",
                    "A crash inside the application — the restart policy is “no”, so this is not "
                    "Docker's doing.",
                    "Run the logs command and read the traceback; rebuild if you changed dependencies.",
                ],
                [
                    "Files created in the container belong to another user",
                    "On Linux, the container user id differs from yours.",
                    "Keep editing through VS Code, which matches the ids, or run: "
                    "sudo chown -R $USER:$USER .",
                ],
                [
                    "The app answers with the offline warning banner",
                    "No API keys are configured, so no language model runs.",
                    "Expected for a demo. Put your keys in .env (copy env.example) and restart to get "
                    "full analysis.",
                ],
            ],
        ),
        ("h2", "Where to look for more"),
        (
            "bullets",
            [
                "README.md — what the project does and how it is deployed.",
                "docs/wiki/Installation-and-Deployment.md — full local, Docker and cloud instructions.",
                "docs/wiki/Troubleshooting.md — problems seen in practice and how they were solved.",
                "docker-compose.yml — the services, ports and volumes described in this document.",
            ],
        ),
        ("space",),
        (
            "callout_bold",
            "About this document: ",
            "it is generated by scripts/make_run_stop_doc.py and listed in .gitignore, so it stays on "
            "your machine and never appears in the repository. Regenerate it with "
            "python scripts/make_run_stop_doc.py --lang en.",
            "ok",
        ),
    ],
)

CONTENT: dict[str, Content] = {"ru": RU, "en": EN}


def build(output: Path, content: Content) -> Path:
    document = Document()
    setup(document, content)
    render(document, content)
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the personal Run & Stop guide (docx).")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--lang",
        choices=sorted(CONTENT),
        default="ru",
        help="document language: ru (default) or en",
    )
    args = parser.parse_args(argv)
    path = build(Path(args.out), CONTENT[args.lang])
    print(f"Wrote {path} ({path.stat().st_size:,} bytes, {args.lang})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

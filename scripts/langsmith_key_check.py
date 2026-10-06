#!/usr/bin/env python3
"""Диагностика ключа LangSmith: к какому инстансу он привязан и работает ли он.

    python3 scripts/langsmith_key_check.py <API_KEY> [WORKSPACE_ID]

Только стандартная библиотека — ничего устанавливать не нужно.

Зачем: инстанс LangSmith (US / EU) определяется **организацией**, а не ключом. Если
организация живёт на EU-инстансе, а приложение ходит на US, то *любой* ключ — и
personal (`lsv2_pt_`), и service (`lsv2_sk_`) — получает `403 Forbidden`, потому что
US-инстанс такую организацию не знает. При этом публичный `/info` отвечает `200`, и
это выглядит как проблема с ключом.

Скрипт делает по одному GET-запросу на каждый инстанс и печатает вердикт.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

INSTANCES = {
    "US": "https://api.smith.langchain.com",
    "EU": "https://eu.api.smith.langchain.com",
}


def call(url: str, key: str, ws: str | None):
    headers = {"X-API-Key": key, "Accept": "application/json"}
    if ws:
        headers["X-Tenant-Id"] = ws
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            return r.status, r.read(300).decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode(errors="replace").strip()
    except Exception as e:  # сеть/DNS
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    key = sys.argv[1].strip()
    ws = sys.argv[2].strip() if len(sys.argv) > 2 else None

    print(f"key       : {key[:12]}…{key[-4:]} (len={len(key)})")
    print(f"workspace : {ws or '(не передан)'}\n")

    working: list[str] = []
    for name, base in INSTANCES.items():
        status, payload = call(f"{base}/sessions?limit=1", key, ws)
        marker = "OK " if status == 200 else "   "
        print(f"  {marker}{name}  {base:38} -> {status}  {payload[:90]}")
        if status == 200:
            working.append(name)

    print()
    if working:
        endpoint = INSTANCES[working[0]]
        print(f"ВЕРДИКТ: ключ работает на инстансе {', '.join(working)}.")
        print("  Пропиши в .env:")
        print(f"    LANGSMITH_ENDPOINT={endpoint}")
        print(f"    LANGCHAIN_ENDPOINT={endpoint}")
        if len(working) == 1 and working[0] == "EU":
            print("  (организация на EU-инстансе — US-эндпоинт для неё всегда отвечает 403)")
        # Listing projects is optional extra detail: the key already answered 200, so a
        # malformed or unexpected payload here must not change the verdict.
        try:
            projects = [
                p["name"] for p in json.loads(call(f"{endpoint}/sessions?limit=10", key, ws)[1])
            ]
        except (ValueError, KeyError, TypeError):
            projects = []
        print(f"  Проекты в воркспейсе: {projects or '(пока нет)'}")
        return 0

    print("ВЕРДИКТ: ключ не принят ни на одном инстансе. Что проверить:")
    print("  1. ключ не отозван и скопирован целиком (UI → Settings → API Keys);")
    print("  2. ключ создан в той организации, что открыта в UI (переключатель сверху слева);")
    print("  3. для приложения лучше SERVICE key (lsv2_sk_…), а не personal (lsv2_pt_…);")
    print("  4. если всё верно — писать в поддержку: support@langchain.dev")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

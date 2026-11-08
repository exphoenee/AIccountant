#!/usr/bin/env python3
"""Adónaptár (input/adonaptar/<év>.md) feldolgozása.

Használat:
    python -I .claude/skills/adonaptar/scripts/adonaptar.py              # új naptárfájlok feldolgozása
    python -I .claude/skills/adonaptar/scripts/adonaptar.py --lista      # a feldolgozott naptár kiírása
    python -I .claude/skills/adonaptar/scripts/adonaptar.py --lista --ev 2026 --napok 60

Folyamat (lásd .claude/rules/adatkezeles.md):
    input/adonaptar/<év>.md  ->  data/adonaptar/<év>.json            (gépi változat)
                             ->  .claude/memory/adonaptar-<év>.md    (olvasható kivonat + MEMORY.md index)
                             ->  archive/adonaptar/                  (csak sikeres feldolgozás után)

Elvárt formátum: Markdown táblázatsorok, amelyek dátuma félkövér:
    | **2026.01.12.** | SZJA | teendő | megjegyzés |      (adónemes táblák)
    | **2026.03.16.** | teendő | megjegyzés |              (IPA tábla, adónem oszlop nélkül)
Más sorokat (pl. az összesítő táblát) nem dolgoz fel.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "input" / "adonaptar"
DATA = ROOT / "data" / "adonaptar"
ARCHIVE = ROOT / "archive" / "adonaptar"
MEMORY = ROOT / ".claude" / "memory"

ROW = re.compile(r"^\|\s*\*\*(\d{4})\.(\d{2})\.(\d{2})\.\*\*\s*\|(.*)\|\s*$")
QUARTER_BY_DUE_MONTH = {1: (-1, 4), 4: (0, 1), 7: (0, 2), 10: (0, 3)}


def kind(adonem: str, teendo: str) -> str:
    a, t = adonem.upper(), teendo.lower()
    if a == "SZJA" and "előleg" in t:
        return "szja_eloleg"
    if "TBJ" in a:
        return "tb_szocho"
    if a == "SZJA" and "25szja" in t:
        return "szja_bevallas"
    if a == "IPA" and "bevallás" in t:
        return "ipa_bevallas"
    if a == "IPA" and "előleg" in t:
        return "ipa_eloleg"
    if "kamarai" in a.lower() or "kamarai" in t:
        return "kamara"
    return "egyeb"


def parse(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = ROW.match(line)
        if not m:
            continue
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        cols = [c.strip() for c in m.group(4).split("|")]
        if len(cols) == 3:
            adonem, teendo, megj = cols
        elif len(cols) == 2:
            adonem, (teendo, megj) = "IPA", cols
        else:
            raise ValueError(f"{path.name}:{n}: váratlan oszlopszám ({len(cols)}): {line[:80]}")
        k = kind(adonem, teendo)
        q = None
        if k in ("szja_eloleg", "tb_szocho"):
            if mo not in QUARTER_BY_DUE_MONTH:
                raise ValueError(f"{path.name}:{n}: negyedéves határidő váratlan hónapban: {y}.{mo:02d}")
            dy, qn = QUARTER_BY_DUE_MONTH[mo]
            q = {"ev": y + dy, "negyedev": qn}
        rows.append({"datum": f"{y:04d}-{mo:02d}-{d:02d}", "adonem": adonem, "teendo": teendo,
                     "megjegyzes": megj, "tipus": k, "negyedev": q})
    rows.sort(key=lambda r: (r["datum"], r["adonem"], r["teendo"]))
    return rows


def memory_md(ev: int, rows: list[dict], src: str) -> str:
    out = [
        "---",
        f"name: adonaptar-{ev}",
        f"description: A {ev}-os adónaptár feldolgozott kivonata (határidők, adónemek, teendők) átalányadózó egyéni vállalkozóra",
        "metadata:",
        "  type: reference",
        "---",
        "",
        f"# Adónaptár {ev} (feldolgozott kivonat)",
        "",
        f"Forrás: `archive/adonaptar/{src}` · feldolgozva: {datetime.now():%Y-%m-%d %H:%M} · gépi változat: `data/adonaptar/{ev}.json`",
        "Ezt a fájlt az `adonaptar` skill scriptje generálja; kézzel ne szerkeszd, futtasd újra a scriptet.",
        "",
        "| Határidő | Adónem | Teendő | Megjegyzés |",
        "|---|---|---|---|",
    ]
    for r in rows:
        esc = lambda s: s.replace("|", "\\|")
        out.append(f"| {r['datum'].replace('-', '.')}. | {esc(r['adonem'])} | {esc(r['teendo'])} | {esc(r['megjegyzes'])} |")
    out += ["", "Kapcsolódó szabályok: [[hataridok]] (`.claude/rules/hataridok.md`).", ""]
    return "\n".join(out)


def update_index(ev: int):
    MEMORY.mkdir(parents=True, exist_ok=True)
    idx = MEMORY / "MEMORY.md"
    line = f"- [Adónaptár {ev}](adonaptar-{ev}.md) — {ev}-os adóhatáridők, adónemek, teendők (feldolgozott kivonat)"
    lines = idx.read_text(encoding="utf-8").splitlines() if idx.exists() else []
    lines = [l for l in lines if not l.startswith(f"- [Adónaptár {ev}]")]
    lines.append(line)
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive_file(src: Path) -> Path:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE / src.name
    if dest.exists():
        dest = ARCHIVE / f"{datetime.now():%Y%m%dT%H%M%S}_{src.name}"
    shutil.move(str(src), str(dest))
    return dest


def process_new():
    for md in sorted(INPUT.glob("*.md")):
        try:
            if not re.fullmatch(r"\d{4}", md.stem):
                raise ValueError("a fájlnév nem ÉÉÉÉ.md (pl. 2026.md)")
            ev = int(md.stem)
            rows = parse(md)
            if not rows:
                raise ValueError("nem találtam egyetlen határidősort sem (félkövér dátumú táblázatsorokat keresek)")
            DATA.mkdir(parents=True, exist_ok=True)
            (DATA / f"{ev}.json").write_text(json.dumps(
                {"ev": ev, "eredeti_fajlnev": md.name, "feldolgozva": datetime.now().isoformat(timespec="seconds"),
                 "tetelek": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
            MEMORY.mkdir(parents=True, exist_ok=True)
            (MEMORY / f"adonaptar-{ev}.md").write_text(memory_md(ev, rows, md.name), encoding="utf-8")
            update_index(ev)
        except Exception as e:
            print(f"HIBA: {md.name} feldolgozása sikertelen: {e}. A fájl az input/-ban maradt.")
            continue
        a = archive_file(md)
        print(f"Feldolgozva: {md.name}: {len(rows)} határidősor")
        print(f"  -> {(DATA / f'{ev}.json').relative_to(ROOT)}")
        print(f"  -> {(MEMORY / f'adonaptar-{ev}.md').relative_to(ROOT)}")
        print(f"Archiválva:  {a.relative_to(ROOT)}")
        by = {}
        for r in rows:
            by[r["tipus"]] = by.get(r["tipus"], 0) + 1
        print("  típusok: " + ", ".join(f"{k}={v}" for k, v in sorted(by.items())))


def lista(ev: int, napok, ma: date):
    p = DATA / f"{ev}.json"
    if not p.exists():
        sys.exit(f"HIBA: nincs feldolgozott adónaptár ({p.relative_to(ROOT)}). Másold az {ev}.md-t az input/adonaptar/ mappába.")
    d = json.loads(p.read_text(encoding="utf-8"))
    print(f"== Adónaptár {ev} (forrás: {p.relative_to(ROOT)}, feldolgozva: {d['feldolgozva']}) ==")
    for r in d["tetelek"]:
        diff = (date.fromisoformat(r["datum"]) - ma).days
        if napok is not None and not (0 <= diff <= napok):
            continue
        rel = f"{diff} nap múlva" if diff >= 0 else f"{-diff} napja lejárt"
        print(f"{r['datum']}  ({rel:>16})  [{r['adonem']}] {r['teendo']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Adónaptár feldolgozása / listázása.")
    ap.add_argument("--lista", action="store_true", help="a feldolgozott naptár listázása (nem dolgoz fel új fájlt)")
    ap.add_argument("--ev", type=int, default=date.today().year)
    ap.add_argument("--napok", type=int, help="lista: csak a következő N nap határidői")
    ap.add_argument("--ma", type=date.fromisoformat, default=date.today(), help="teszteléshez")
    a = ap.parse_args()
    if a.lista:
        lista(a.ev, a.napok, a.ma)
        return
    if not list(INPUT.glob("*.md")):
        print("Nincs új feldolgozandó fájl az input/adonaptar/ mappában. (A feldolgozott naptár listázása: --lista)")
        return
    process_new()


if __name__ == "__main__":
    main()

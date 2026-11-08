#!/usr/bin/env python3
"""PDF -> tömör Markdown, tokentakarékos feldolgozással.

Feldolgozás:
    python -I .claude/skills/pdf-markdown/scripts/pdf_markdown.py
        input/pdf/*.pdf  ->  data/pdf/<név>.md + <név>.json   (a PDF ezután: archive/pdf/)
Célzott olvasás (a teljes szöveget ne töltsd be, csak ami kell):
    ... --lista                                  feldolgozott PDF-ek (név, oldal, szószám)
    ... --vazlat <név>                           címsorok oldalszámmal
    ... --kereses <név> <regex> [--max 20]       találatok: oldalszám + sor (rövidítve)
    ... --olvas <név> --oldalak 3-5 [--max-karakter 6000]   csak a kért oldalak szövege

Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md.
Kemény korlátok (nincs kitalálás): táblázatot és képet nem értelmez (a szöveg sorrendben, simán jön ki), szkennelt
(szövegréteg nélküli) PDF-et nem OCR-ez, hanem hibával megáll. Csak a PDF szövegrétegét használja (pdftotext).
A teljes szöveg a chatbe nem kerül ki: a feldolgozás csak összefoglalót ír a képernyőre.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "input" / "pdf"
DATA = ROOT / "data" / "pdf"
ARCHIVE = ROOT / "archive" / "pdf"
MARK = re.compile(r"^<!-- p:(\d+) -->$")
UP = "A-ZÁÉÍÓÖŐÚÜŰ"


# ----------------------------------------------------------------- kinyerés

def find_pdftotext() -> str:
    exe = shutil.which("pdftotext")
    if exe:
        return exe
    for c in (r"C:\Program Files\Git\mingw64\bin\pdftotext.exe", r"C:\Program Files\Git\usr\bin\pdftotext.exe"):
        if Path(c).exists():
            return c
    sys.exit("HIBA: nem találom a pdftotext programot (poppler/xpdf). Telepítsd, vagy mondd meg, hogy engedélyezed-e "
             "egy Python PDF-könyvtár (pl. pymupdf) telepítését; magamtól nem telepítek csomagot.")


def extract_pages(pdf: Path) -> list[str]:
    r = subprocess.run([find_pdftotext(), "-layout", "-enc", "UTF-8", "-eol", "unix", "-q", str(pdf), "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("pdftotext hiba: " + r.stderr.decode("utf-8", "replace").strip()[:200])
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


# --------------------------------------------------------------- konvertálás

PAGENUM = re.compile(r"^(?:oldal\s*|page\s*)?\d{1,4}(?:\s*/\s*\d{1,4})?$|^-\s*\d{1,4}\s*-$", re.I)
NUMHEAD = re.compile(rf"^(\d+(?:\.\d+){{0,3}})\.?\s+([{UP}].{{1,88}})$")
BULLET = re.compile(r"^[•●▪◦·▪■□\-–—*]\s+(.*)$")


def norm_key(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def repeating(pages_lines: list[list[str]]) -> set[str]:
    n = len(pages_lines)
    if n < 3:
        return set()
    cnt = Counter()
    for lines in pages_lines:
        for k in {norm_key(l) for l in lines if 0 < len(l.strip()) <= 90}:
            cnt[k] += 1
    thr = max(3, (n + 1) // 2)
    return {k for k, v in cnt.items() if v >= thr}


def heading_level(line: str):
    m = NUMHEAD.match(line)
    if m and not line.rstrip().endswith((".", ",", ";", ":")) and len(line.split()) <= 12:
        return min(1 + m.group(1).count("."), 4)
    letters = [ch for ch in line if ch.isalpha()]
    if (4 <= len(letters) and len(line) <= 80 and sum(ch.isupper() for ch in letters) / len(letters) >= 0.85
            and not re.search(r"\d{3,}", line)):
        return 1
    return 0


def tables_to_md(items):
    """Egymást követő táblázatsorokból Markdown táblázat; egyetlen sor ' | '-os szöveg."""
    res, i = [], 0
    while i < len(items):
        it = items[i]
        if isinstance(it, tuple):
            j = i
            while j < len(items) and isinstance(items[j], tuple):
                j += 1
            rows = [r for _, r in items[i:j]]
            if len(rows) >= 2:
                w = max(len(r) for r in rows)
                rows = [r + [""] * (w - len(r)) for r in rows]
                res.append("| " + " | ".join(rows[0]) + " |")
                res.append("|" + "---|" * w)
                res += ["| " + " | ".join(r) + " |" for r in rows[1:]]
            else:
                res.append(" | ".join(rows[0]))
            i = j
        else:
            res.append(it); i += 1
    return res


def convert(pages: list[str]):
    """-> (markdown, meta részek)."""
    raw = [[l.rstrip() for l in p.splitlines()] for p in pages]
    rep = repeating(raw)
    removed = Counter()
    body_pages, outline = [], []
    for pno, lines in enumerate(raw, 1):
        out, buf = [], ""

        def flush():
            nonlocal buf
            if buf:
                out.append(buf)
                buf = ""

        for line in lines:
            s = re.sub(r"[ \t]+", " ", line.strip())
            if not s:
                flush(); out.append(""); continue
            if PAGENUM.match(s):
                removed["oldalszám"] += 1; continue
            if norm_key(s) in rep:
                removed["fejléc/lábléc"] += 1; continue
            cells = [c for c in re.split(r"\s{3,}", line.strip()) if c.strip()]
            if len(cells) >= 2 and not BULLET.match(s):
                flush(); out.append(("T", [re.sub(r"[ \t]+", " ", c.strip()) for c in cells])); continue
            b = BULLET.match(s)
            lvl = heading_level(s)
            if lvl:
                flush(); out.append("#" * (lvl + 1) + " " + s.title() if (s.isupper() and not NUMHEAD.match(s)) else "#" * (lvl + 1) + " " + s)
                outline.append({"oldal": pno, "szint": lvl, "cim": s if not s.isupper() else s.title()})
                out.append(""); continue
            if b:
                flush(); buf = "- " + b.group(1); continue
            if buf and not buf.endswith((".", "!", "?", ":", ";")) and len(buf) >= 40 and not buf.startswith("#"):
                if buf.endswith("-") and s[:1].islower():
                    buf = buf[:-1] + s          # elválasztójel-összevonás
                else:
                    buf += " " + s
            else:
                flush(); buf = s
        flush()
        out = tables_to_md(out)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
        body_pages.append(text)
    md_parts = []
    for pno, t in enumerate(body_pages, 1):
        if t:
            md_parts.append(f"<!-- p:{pno} -->\n{t}")
    return "\n\n".join(md_parts) + "\n", outline, removed, [i + 1 for i, t in enumerate(body_pages) if not t]


# ------------------------------------------------------------- feldolgozás

def archive_file(src: Path) -> Path:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE / src.name
    if dest.exists():
        dest = ARCHIVE / f"{datetime.now():%Y%m%dT%H%M%S}_{src.name}"
    shutil.move(str(src), str(dest))
    return dest


def process_all():
    pdfs = sorted(INPUT.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    if not pdfs:
        print("Nincs feldolgozandó PDF az input/pdf/ mappában. (Feldolgozott PDF-ek: --lista)")
        return
    DATA.mkdir(parents=True, exist_ok=True)
    for pdf in pdfs:
        try:
            pages = extract_pages(pdf)
            chars = sum(len(p.strip()) for p in pages)
            if not pages or chars / max(len(pages), 1) < 30:
                raise RuntimeError("nincs értékelhető szövegréteg (valószínűleg szkennelt PDF); OCR-t nem végzek")
            md, outline, removed, empty = convert(pages)
            stem = re.sub(r"[^\w.-]+", "_", pdf.stem).strip("_") or "pdf"
            md_path = DATA / f"{stem}.md"
            md_path.write_text(md, encoding="utf-8", newline="\n")
            meta = {"forras_fajl": pdf.name, "feldolgozva": datetime.now().isoformat(timespec="seconds"),
                    "oldalak": len(pages), "ures_oldalak": empty, "karakter": len(md), "szo": len(md.split()),
                    "eltavolitva": dict(removed), "vazlat": outline, "md_fajl": md_path.name}
            (DATA / f"{stem}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            print(f"HIBA: {pdf.name}: {e}. A fájl az input/pdf/-ben maradt.")
            continue
        a = archive_file(pdf)
        print(f"Feldolgozva: {pdf.name} -> {md_path.relative_to(ROOT)}  (archiválva: {a.relative_to(ROOT)})")
        print(f"  {meta['oldalak']} oldal, {meta['szo']} szó, {meta['karakter']} karakter; címsor: {len(outline)}; "
              f"eltávolított ismétlődő sor: {sum(removed.values())}; üres oldal: {len(empty) or 'nincs'}")
        for h in outline[:12]:
            print(f"  {'  ' * (h['szint'] - 1)}p.{h['oldal']} {h['cim'][:70]}")
        if len(outline) > 12:
            print(f"  ... további {len(outline) - 12} címsor: --vazlat {stem}")
        print(f"  Olvasás célzottan: --kereses {stem} <regex> | --olvas {stem} --oldalak 1-2")


# --------------------------------------------------------------- mappa-mód

SAFE = re.compile(r'[<>:"|?*\x00-\x1f]')


def convert_pdf(pdf: Path, md_path: Path, shown_name: str, write_meta: bool = True) -> dict:
    pages = extract_pages(pdf)
    chars = sum(len(p.strip()) for p in pages)
    if not pages or chars / max(len(pages), 1) < 30:
        raise RuntimeError("nincs értékelhető szövegréteg (valószínűleg szkennelt PDF); OCR-t nem végzek")
    md, outline, removed, empty = convert(pages)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8", newline="\n")
    meta = {"forras_fajl": shown_name, "feldolgozva": datetime.now().isoformat(timespec="seconds"),
            "oldalak": len(pages), "ures_oldalak": empty, "karakter": len(md), "szo": len(md.split()),
            "eltavolitva": dict(removed), "vazlat": outline, "md_fajl": md_path.name}
    if write_meta:
        md_path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def process_single(pdf: Path, md: Path):
    """Egyetlen PDF -> megadott Markdown útvonal (pl. a PDF saját mappájába). Az eredeti PDF nem mozdul, meta-fájl nem készül."""
    pdf = pdf if pdf.is_absolute() else ROOT / pdf
    md = md if md.is_absolute() else ROOT / md
    if not pdf.is_file():
        sys.exit(f"HIBA: nincs ilyen PDF: {pdf}")
    try:
        meta = convert_pdf(pdf, md, pdf.name, write_meta=False)
    except Exception as e:
        sys.exit(f"HIBA: {pdf.name}: {e}")
    print(f"{pdf.name} -> {md.relative_to(ROOT)}: {meta['oldalak']} oldal, {meta['szo']} szó, címsor: {len(meta['vazlat'])}")


def process_folder(folder: Path):
    """Egy mappa összes PDF-je (rekurzívan) -> data/pdf/<mappanév>/<ugyanaz a részmappa-szerkezet>.md.
    Az eredeti PDF-ek a helyükön maradnak (a mappaszerkezet a felhasználó dolga, nem mozgatjuk)."""
    folder = folder if folder.is_absolute() else ROOT / folder
    if not folder.is_dir():
        sys.exit(f"HIBA: nincs ilyen mappa: {folder}")
    pdfs = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    out_root = DATA / SAFE.sub("_", folder.name)
    index, ok, bad, words, pages_n = [], 0, 0, 0, 0
    for pdf in pdfs:
        rel = pdf.relative_to(folder)
        md_path = out_root / rel.parent / (SAFE.sub("_", pdf.stem) + ".md")
        try:
            meta = convert_pdf(pdf, md_path, rel.as_posix())
            ok += 1; words += meta["szo"]; pages_n += meta["oldalak"]
            index.append({"forras": rel.as_posix(), "md": md_path.relative_to(DATA).as_posix(), "oldalak": meta["oldalak"], "szo": meta["szo"]})
        except Exception as e:
            bad += 1
            index.append({"forras": rel.as_posix(), "hiba": str(e)[:200]})
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "_index.json").write_text(json.dumps({"mappa": str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else str(folder),
        "feldolgozva": datetime.now().isoformat(timespec="seconds"), "tetelek": index}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{folder.name}: {len(pdfs)} PDF, sikeres: {ok}, hiba: {bad}; {pages_n} oldal, {words} szó")
    print(f"  Markdown: {out_root.relative_to(ROOT)}/ (index: _index.json); az eredeti PDF-ek a helyükön maradtak")
    for it in index:
        if "hiba" in it:
            print(f"  HIBA: {it['forras']}: {it['hiba']}")


# ----------------------------------------------------------- célzott olvasás

def resolve(name: str) -> Path:
    c = sorted(DATA.rglob("*.md"))
    key = lambda p: p.relative_to(DATA).with_suffix("").as_posix()
    n = name.lower().replace("\\", "/")
    exact = [p for p in c if key(p).lower() == n or p.stem.lower() == n]
    part = exact or [p for p in c if n in key(p).lower()]
    if len(part) != 1:
        sys.exit("HIBA: " + ("nincs ilyen feldolgozott PDF" if not part else f"{len(part)} találat, pontosítsd a nevet (pl. a mappa nevével): "
                 + ", ".join(key(p) for p in part[:8]))
                 + ". Lista: --lista")
    return part[0]


def split_pages(md_path: Path) -> dict[int, list[str]]:
    pages, cur = {}, None
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = MARK.match(line)
        if m:
            cur = int(m.group(1)); pages[cur] = []
        elif cur is not None:
            pages[cur].append(line)
    return pages


def parse_range(s: str, maxp: int) -> list[int]:
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        lo, hi = int(a), int(b or a)
        out += range(max(lo, 1), min(hi, maxp) + 1)
    return sorted(set(out))


def cmd_lista():
    ms = sorted(p for p in DATA.rglob("*.json") if p.name != "_index.json")
    if not ms:
        print("Nincs feldolgozott PDF a data/pdf/ mappában.")
    shown = 0
    for p in ms:
        shown += 1
        if shown > 60:
            print(f"... további {len(ms) - 60} fájl; szűkítéshez használd a mappa nevét a --kereses/--vazlat kapcsolóknál")
            break
        m = json.loads(p.read_text(encoding="utf-8"))
        print(f"{p.relative_to(DATA).with_suffix('').as_posix()}: {m['oldalak']} oldal, {m['szo']} szó")


def cmd_vazlat(name):
    p = resolve(name); m = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
    print(f"{p.stem}: {m['oldalak']} oldal, {m['szo']} szó")
    for h in m["vazlat"] or []:
        print(f"{'  ' * (h['szint'] - 1)}p.{h['oldal']} {h['cim']}")
    if not m["vazlat"]:
        print("Nincs felismert címsor; használd a --kereses kapcsolót.")


def cmd_kereses(name, rx, maxn):
    p = resolve(name); pages = split_pages(p)
    pat = re.compile(rx, re.I); n = 0
    for pno, lines in pages.items():
        for l in lines:
            if pat.search(l):
                n += 1
                if n <= maxn:
                    print(f"p.{pno}: {l.strip()[:200]}")
    print(f"-- {n} találat" + (f", az első {maxn} látható (--max növelhető)" if n > maxn else ""))


def cmd_olvas(name, oldalak, maxc):
    p = resolve(name); pages = split_pages(p)
    sel = parse_range(oldalak, max(pages) if pages else 0)
    out, used = [], 0
    for i, pno in enumerate(sel):
        text = "\n".join(pages.get(pno, [])).strip()
        chunk = f"[p.{pno}]\n{text}\n"
        if used + len(chunk) > maxc:
            keep = max(maxc - used, 0)
            out.append(chunk[:keep].rstrip() + f"\n[... levágva ({maxc} karakter korlát); folytatás: --oldalak {pno}-{sel[-1]} vagy nagyobb --max-karakter]")
            break
        out.append(chunk); used += len(chunk)
    print("\n".join(out) if out else "Nincs ilyen oldal / üres oldal.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="PDF -> tömör Markdown (tokentakarékos).")
    ap.add_argument("--mappa", metavar="ÚTVONAL", help="egy mappa összes PDF-je (rekurzívan) -> data/pdf/<mappa>/; az eredetik a helyükön maradnak")
    ap.add_argument("--fajl", metavar="PDF", help="egyetlen PDF konvertálása; a kimenet útvonalát a --ki adja")
    ap.add_argument("--ki", metavar="MD", help="--fajl: a Markdown kimenet útvonala (pl. a PDF saját mappája)")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--vazlat", metavar="NÉV")
    ap.add_argument("--kereses", nargs=2, metavar=("NÉV", "REGEX"))
    ap.add_argument("--olvas", metavar="NÉV")
    ap.add_argument("--oldalak", default="1", help="pl. 3, 2-4, 1,5-6 (alap: 1)")
    ap.add_argument("--max", type=int, default=20, help="--kereses: legfeljebb ennyi találat")
    ap.add_argument("--max-karakter", type=int, default=6000, help="--olvas: kimenet korlátja")
    a = ap.parse_args()
    if a.fajl:
        if not a.ki:
            sys.exit("HIBA: --fajl mellé kell a --ki (a Markdown útvonala)")
        process_single(Path(a.fajl), Path(a.ki))
    elif a.mappa: process_folder(Path(a.mappa))
    elif a.lista: cmd_lista()
    elif a.vazlat: cmd_vazlat(a.vazlat)
    elif a.kereses: cmd_kereses(a.kereses[0], a.kereses[1], a.max)
    elif a.olvas: cmd_olvas(a.olvas, a.oldalak, a.max_karakter)
    else: process_all()


if __name__ == "__main__":
    main()

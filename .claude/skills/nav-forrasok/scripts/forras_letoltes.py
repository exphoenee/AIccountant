#!/usr/bin/env python3
"""NAV- és jogszabály-források letöltése módosítás nélkül (torvenytar/forrasok.json alapján).

Használat:
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py                 # a még nem letöltött források
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --ujra          # mindet újra
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --hivatkozasok  # a NAV-szövegekben idézett jogszabályok listája

Minden forrásból három fájl készül a manifest `mappa` mezője szerint (NAV: torvenytar/NAV/<év>/, jogszabály: torvenytar/<törvény>/<év>/):
    <név>.<kiterjesztés>   az eredeti, bájtra azonos letöltés (html / pdf), SOHA nem módosítjuk
    <név>.txt              gépies szövegkivonat (HTML: a <main> tartalma; PDF: pdftotext -layout). A szavak nem változnak,
                           csak a jelölőnyelv (HTML) hiányzik és a szóközök/üres sorok vannak összevonva.
    <név>.forras.json      URL, letöltés ideje, HTTP-állapot, tartalomtípus, SHA-256, méret
A szöveg értelmezése (összefoglaló, "mi vonatkozik rám") külön dokumentumba kerül, a forrásfájlokba soha.

Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md. Csak szabványos Python; PDF-hez pdftotext.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "torvenytar"
MANIFEST = DOCS / "forrasok.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIccountant-forrasletoltes"
SKIP = {"script", "style", "noscript", "svg", "template", "head", "footer", "nav", "form", "button", "select"}
BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section", "article",
         "header", "dd", "dt", "dl", "blockquote", "pre", "hr", "caption"}


class Text(HTMLParser):
    """A <main> elem (ha van; különben a <body>) szöveges tartalma, blokkhatárokon sortöréssel."""

    def __init__(self, use_main: bool):
        super().__init__(convert_charrefs=True)
        self.use_main, self.out, self.skip, self.in_main, self.title, self._in_title = use_main, [], 0, False, "", False
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "body":
            self.in_body = True
        if tag == "main":
            self.in_main = True
        if tag in SKIP and tag != "head":
            self.skip += 1
        if tag in BLOCK:
            self.out.append("\n")
        if tag in ("td", "th"):
            self.out.append("\t")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "main":
            self.in_main = False
        if tag in SKIP and tag != "head" and self.skip:
            self.skip -= 1
        if tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self.skip:
            return
        if (self.use_main and self.in_main) or (not self.use_main and self.in_body):
            self.out.append(data)


def html_to_text(raw: bytes):
    src = raw.decode("utf-8", "replace")
    use_main = "<main" in src.lower()
    p = Text(use_main)
    p.feed(src)
    lines = [re.sub(r"[ \f\v\u00a0]+", " ", l).strip(" ") for l in "".join(p.out).splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(l.strip() for l in lines)).strip() + "\n"
    return text, re.sub(r"\s+", " ", p.title).strip()


def pdf_to_text(path: Path) -> str:
    exe = shutil.which("pdftotext") or r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"
    r = subprocess.run([exe, "-layout", "-enc", "UTF-8", "-eol", "unix", "-q", str(path), "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("pdftotext hiba: " + r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout.decode("utf-8", "replace")


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.status, r.headers.get("Content-Type", ""), r.headers.get("Last-Modified", ""), r.geturl()


def import_local(item: dict, force: bool) -> bool:
    """Helyi (a felhasználó által az input/ alá másolt) forrás importálása: az eredeti fájl bájtra azonosan a torvenytar/ alá kerül
    (az input/ ürül), mellé gépies szövegkivonat és forrásadat. A Markdown a pdf_md() lépésben készül."""
    out_dir = DOCS / item["mappa"]
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_p = out_dir / f"{item['nev']}.forras.json"
    if meta_p.exists() and not force:
        print(f"= már megvan: {item['mappa']}/{item['nev']}")
        return True
    src = ROOT / item["helyi_forras"]
    if not src.exists():
        print(f"HIBA: nincs ilyen helyi forrás: {item['helyi_forras']}")
        return False
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    ext = src.suffix.lower().lstrip(".") or "bin"
    raw_p = out_dir / f"{item['nev']}.{ext}"
    shutil.move(str(src), str(raw_p))
    after = hashlib.sha256(raw_p.read_bytes()).hexdigest()
    if before != after:
        print(f"HIBA: a másolat hash-e eltér: {raw_p.name}")
        return False
    text = pdf_to_text(raw_p) if ext == "pdf" else ""
    (out_dir / f"{item['nev']}.txt").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": item.get("id"), "url": None, "helyi_forras": item["helyi_forras"], "importalva": datetime.now().isoformat(timespec="seconds"),
            "hivatalos": item.get("hivatalos"), "bajt": raw_p.stat().st_size, "sha256": after, "eredeti_fajl": raw_p.name,
            "szovegkivonat": f"{item['nev']}.txt", "szovegkivonat_karakter": len(text), "megjegyzes": item.get("megjegyzes")}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"+ {item['mappa']}/{item['nev']}.{ext}: importálva az input/-ból, {meta['bajt']} bájt, szöveg {len(text)} karakter, SHA-256 egyezik")
    return True


def download(item: dict, force: bool) -> bool:
    if item.get("helyi_forras"):
        return import_local(item, force)
    out_dir = DOCS / item["mappa"]
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_p = out_dir / f"{item['nev']}.forras.json"
    if meta_p.exists() and not force:
        print(f"= már megvan: {item['mappa']}/{item['nev']}")
        return True
    try:
        data, status, ctype, lastmod, final = fetch(item["url"])
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"HIBA: {item['url']}: {e}")
        return False
    is_pdf = data[:5] == b"%PDF-" or "pdf" in ctype.lower()
    ext = "pdf" if is_pdf else "html"
    raw_p = out_dir / f"{item['nev']}.{ext}"
    raw_p.write_bytes(data)
    title = ""
    try:
        text, title = (pdf_to_text(raw_p), "") if is_pdf else html_to_text(data)
    except Exception as e:
        print(f"FIGYELEM: szövegkivonat nem készült ({e}); az eredeti fájl mentve.")
        text = ""
    (out_dir / f"{item['nev']}.txt").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": item.get("id"), "url": item["url"], "vegso_url": final, "letoltve": datetime.now().isoformat(timespec="seconds"),
            "http_allapot": status, "tartalomtipus": ctype, "last_modified": lastmod or None, "cim": title or None,
            "bajt": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eredeti_fajl": raw_p.name,
            "szovegkivonat": f"{item['nev']}.txt", "szovegkivonat_karakter": len(text), "megjegyzes": item.get("megjegyzes")}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"+ {item['mappa']}/{item['nev']}.{ext}: HTTP {status}, {len(data)} bájt, szöveg {len(text)} karakter"
          + (f", cím: {title[:60]}" if title else ""))
    if len(text) < 500:
        print("  FIGYELEM: a szövegkivonat nagyon rövid; az oldal lehet, hogy JavaScripttel tölti be a tartalmat.")
    return True


# ------------------------------------------------- PDF -> Markdown, korpusz

PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"
CORPUS = ROOT / "data" / "graphify" / "torvenyek"
SECTION_CUT = re.compile(r"^(\d+(/[A-Z])?\.[\s ]*§|[IVXLC]+\. (Fejezet|FEJEZET)|[A-ZÁÉÍÓÖŐÚÜŰ]+ RÉSZ$)")
PART_LINES = 1700


def pdf_md(item: dict) -> bool:
    """A forrás PDF-jéből Markdown a PDF saját mappájába (<név>.md), a pdf-markdown skill scriptjével. Az eredeti PDF nem módosul."""
    pdf = DOCS / item["mappa"] / f"{item['nev']}.pdf"
    if not pdf.exists():
        return True
    md = pdf.with_suffix(".md")
    r = subprocess.run([sys.executable, "-I", str(PDFMD), "--fajl", str(pdf), "--ki", str(md)], capture_output=True, text=True, encoding="utf-8")
    print(("+ " if r.returncode == 0 else "HIBA: ") + (r.stdout.strip() or r.stderr.strip()))
    return r.returncode == 0


def build_corpus():
    """A Graphify bemenete: data/graphify/torvenyek/. A forrásfájlok (torvenytar/) nem módosulnak, a korpusz másolat.
    - törvények: csak a hatályos szöveg (a végén álló lábjegyzet-blokk, azaz a módosítási történet kimarad), szakaszhatáron
      legfeljebb kb. 1700 soros részekre bontva (egy alügynök kontextusa miatt);
    - NAV-források: PDF-nél a Markdown, HTML-nél a szövegkivonat (hogy a NAV-útmutató és a törvények összekapcsolódjanak)."""
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))["forrasok"]
    CORPUS.mkdir(parents=True, exist_ok=True)
    for old in list(CORPUS.glob("*.txt")) + list(CORPUS.glob("*.md")):
        old.unlink()
    mapping, total = {}, 0
    for it in items:
        base = DOCS / it["mappa"] / it["nev"]
        if it["tipus"] == "hatteranyag":
            continue  # nem hivatalos háttéranyag: nem kerül a törvénytérkép korpuszába
        if it["tipus"] == "nav":
            src = base.with_suffix(".md") if base.with_suffix(".pdf").exists() else base.with_suffix(".txt")
            if not src.exists():
                continue
            dest = CORPUS / f"nav-{it['nev']}{src.suffix}"
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            mapping[dest.name] = {"forras": str(src.relative_to(ROOT)).replace("\\", "/")}
            total += 1
            continue
        txt = base.with_suffix(".txt")
        if not txt.exists():
            continue
        lines = txt.read_text(encoding="utf-8").splitlines()
        end = len(lines)
        if len(lines) > 400:  # a lábjegyzet-blokk kezdete: egy "1" számsor, amelyet sűrűn követnek további számsorok
            nums = [i for i, l in enumerate(lines) if re.fullmatch(r"\d{1,4}", l.strip())]
            for i in nums:
                if len([j for j in nums if i < j <= i + 12]) >= 2:
                    end = i
                    break
        body, parts, start = lines[:end], [], 0
        while len(body) - start > PART_LINES + 400:
            i = start + PART_LINES
            while i < len(body) and not SECTION_CUT.match(body[i]):
                i += 1
            if i >= len(body) - 50:
                break
            parts.append((start, i)); start = i
        parts.append((start, len(body)))
        names = []
        for n, (a, b) in enumerate(parts, 1):
            name = f"{it['nev']}.txt" if len(parts) == 1 else f"{it['nev']}_{n:02d}.txt"
            (CORPUS / name).write_text("\n".join(body[a:b]) + "\n", encoding="utf-8", newline="\n")
            names.append({"fajl": name, "forras_sorok": [a + 1, b]})
            total += 1
        mapping[it["nev"]] = {"forras": str(txt.relative_to(ROOT)).replace("\\", "/"), "forras_sorok_osszesen": len(lines),
                              "kihagyott_labjegyzet_sorok": [end + 1, len(lines)] if end < len(lines) else None, "reszek": names}
        print(f"  {it['nev']}: {len(lines)} sor, hatályos szöveg {end} sor, {len(parts)} rész"
              + (f", kihagyott lábjegyzet: {len(lines) - end} sor" if end < len(lines) else ""))
    (CORPUS.parent / "torvenyek_reszek.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    chars = sum(p.stat().st_size for p in CORPUS.iterdir() if p.is_file())
    print(f"Graphify-korpusz: {total} fájl, {chars} bájt -> {CORPUS.relative_to(ROOT)}")
    print("Következő lépés: a Graphify skill futtatása a korpuszon (lásd a SKILL.md 4. pontját).")


# ----------------------------------------------------------- hivatkozások

LAW_NUM = re.compile(r"(\d{4})\.\s*évi\s+([IVXLCDM]+)\.\s*törvény(?:\s*\(([^)]{2,25})\))?", re.I)
ABBR = re.compile(r"\b(Szja\.? tv\.?|Tbj\.?|Szocho\.? tv\.?|Szochotv\.?|Art\.|Áfa tv\.?|Htv\.?|Eht\.?|Mt\.|Ptk\.|Eker\.? tv\.?|"
                  r"Katv\.?|Kata tv\.?|Szt\.|Tao\.? tv\.?)", re.I)


def cmd_hivatkozasok():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    laws, abbrs = {}, {}
    for it in man["forrasok"]:
        if it["tipus"] != "nav":
            continue
        t = DOCS / it["mappa"] / f"{it['nev']}.txt"
        if not t.exists():
            continue
        text = re.sub(r"\s+", " ", t.read_text(encoding="utf-8"))
        for m in LAW_NUM.finditer(text):
            k = f"{m.group(1)}. évi {m.group(2).upper()}. törvény"
            laws.setdefault(k, {"nev": m.group(3), "forras": set()})["forras"].add(it["nev"])
            if m.group(3):
                laws[k]["nev"] = m.group(3)
        for m in ABBR.finditer(text):
            k = m.group(1).lower().replace("..", ".")
            abbrs.setdefault(k, set()).add(it["nev"])
    print("Számmal idézett törvények a NAV-szövegekben:")
    for k, v in sorted(laws.items()):
        print(f"  {k}" + (f" ({v['nev']})" if v["nev"] else "") + "  <- " + ", ".join(sorted(v["forras"])))
    print("Rövidítéssel idézett törvények (a szám nem szerepel a szövegben; a feloldást ellenőrizni kell):")
    for k, v in sorted(abbrs.items()):
        print(f"  {k}  <- " + ", ".join(sorted(v)))


# ------------------------------------------------------------------ bevétel az input/torveny/ mappából
INPUT_TORVENY = ROOT / "input" / "torveny"
ARCH_TORVENY = ROOT / "archive" / "torveny"
ALIASOK = {(2007, 127): "afa-tv", (1995, 117): "szja-tv", (2018, 52): "szocho-tv", (1990, 100): "htv"}  # (év, sorszám) -> rövid mappanév
RE_NJT = re.compile(r"https?://(?:www\.)?(?:njt\.hu|njt\.jog\.gov\.hu)/jogszabaly/(\d{4})-(\d+)-00-00(?:\.\d+)?", re.I)
RE_JOGTAR = re.compile(r"https?://net\.jogtar\.hu/jogszabaly\?docid=a(\d{2})(\d{5})\.tv", re.I)
RE_NAV = re.compile(r"https?://(?:www\.)?nav\.gov\.hu/(?:ado|szja|ugyfeliranytu|nezzen-utana)[^\s)\]\[>\"']*[A-Za-z0-9_/-]", re.I)


def roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, r in vals:
        while n >= v:
            out += r
            n -= v
    return out


def bevesz_input() -> int:
    """Az input/torveny/ mappába tett fájlokban (PDF, MD, TXT, HTML) szereplő HIVATALOS hivatkozásokat (njt.hu törvény, nav.gov.hu oldal)
    felveszi a torvenytar/forrasok.json-ba; a letöltés és feldolgozás a szokásos lépésekkel történik. A bemeneti fájl (általában egy jegyzet,
    nem maga a forrás) az archive/torveny/ mappába kerül. Hivatkozás nélküli fájl az input/-ban marad, jelzéssel."""
    fajlok = sorted(p for p in INPUT_TORVENY.glob("*") if p.is_file() and p.name != ".gitkeep") if INPUT_TORVENY.exists() else []
    if not fajlok:
        return 0
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ismert = {it.get("url", "").lower().rstrip("/") for it in man["forrasok"]}
    ido = datetime.now().year
    uj = 0
    for f in fajlok:
        if f.suffix.lower() == ".pdf":
            szoveg = pdf_to_text(f)
        else:
            szoveg = f.read_text(encoding="utf-8", errors="ignore")
        talalt = []
        for m in RE_NJT.finditer(szoveg):
            talalt.append(("torveny", int(m.group(1)), int(m.group(2))))
        for m in RE_JOGTAR.finditer(szoveg):
            talalt.append(("torveny", 2000 + int(m.group(1)) if int(m.group(1)) < 50 else 1900 + int(m.group(1)), int(m.group(2))))
        navok = sorted({m.group(0).rstrip(".,;") for m in RE_NAV.finditer(szoveg)})
        if not talalt and not navok:
            print(f"❓ input/torveny/{f.name}: nem találtam benne hivatalos hivatkozást (njt.hu törvény-URL, nav.gov.hu oldal); az input/-ban maradt. "
                  "Ha ez maga a forrásszöveg, vedd fel a torvenytar/forrasok.json-ba helyi_forras bejegyzéssel (lásd a SKILL.md-t).")
            continue
        for _, ev, sz in sorted(set(talalt)):
            url = f"https://njt.hu/jogszabaly/{ev}-{sz}-00-00"
            if url.lower() in ismert:
                print(f"= már a jegyzékben: {ev}. évi {roman(sz).upper()}. törvény")
                continue
            alias = ALIASOK.get((ev, sz)) or f"{ev}-{roman(sz)}-tv"
            man["forrasok"].append({"id": f"torveny-{alias}", "tipus": "torveny", "mappa": f"{alias}/{ido}", "nev": f"{ev}-evi-{roman(sz)}-torveny", "url": url,
                                    "megjegyzes": f"{ev}. évi {roman(sz).upper()}. törvény; felvéve az input/torveny/{f.name} hivatkozásából"})
            ismert.add(url.lower())
            uj += 1
            print(f"+ új forrás a jegyzékben: {ev}. évi {roman(sz).upper()}. törvény -> torvenytar/{alias}/{ido}/")
        for url in navok:
            if url.lower().rstrip("/") in ismert or url.lower().endswith(".pdf"):
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", url.lower().split("nav.gov.hu/", 1)[1]).strip("-")[:70]
            man["forrasok"].append({"id": f"nav-{slug}", "tipus": "nav", "mappa": f"NAV/{ido}", "nev": slug, "url": url,
                                    "megjegyzes": f"NAV-oldal; felvéve az input/torveny/{f.name} hivatkozásából"})
            ismert.add(url.lower().rstrip("/"))
            uj += 1
            print(f"+ új NAV-forrás a jegyzékben: {url}")
        ARCH_TORVENY.mkdir(parents=True, exist_ok=True)
        dst = ARCH_TORVENY / f.name
        if dst.exists():
            dst = ARCH_TORVENY / (datetime.now().strftime("%Y%m%dT%H%M%S_") + f.name)
        shutil.move(str(f), str(dst))
        print(f"  a bemeneti fájl archiválva (nem hivatalos háttéranyag, csak a hivatkozásait használtam): {dst.relative_to(ROOT)}")
    if uj:
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    return uj


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="NAV/jogszabály források letöltése módosítás nélkül.")
    ap.add_argument("--ujra", action="store_true", help="már letöltött forrásokat is újra letölti")
    ap.add_argument("--hivatkozasok", action="store_true", help="a NAV-szövegekben idézett törvények listája")
    ap.add_argument("--korpusz", action="store_true", help="csak a Graphify-korpusz újraépítése (nincs letöltés)")
    a = ap.parse_args()
    if not MANIFEST.exists():
        sys.exit(f"HIBA: nincs {MANIFEST.relative_to(ROOT)}")
    if a.hivatkozasok:
        cmd_hivatkozasok()
        return
    if not a.korpusz:
        bevesz_input()
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))["forrasok"]
    if not a.korpusz:
        ok = sum(download(it, a.ujra) for it in items)
        print(f"{ok}/{len(items)} forrás rendben.")
        print("PDF -> Markdown (a PDF saját mappájába):")
        for it in items:
            pdf_md(it)
    build_corpus()


if __name__ == "__main__":
    main()

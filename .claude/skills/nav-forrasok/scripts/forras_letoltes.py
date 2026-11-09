#!/usr/bin/env python3
"""NAV- és jogszabály-források letöltése módosítás nélkül (torvenytar/forrasok.json alapján).

Használat:
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py                 # a még nem letöltött források
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --ujra          # mindet újra
    python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --hivatkozasok  # a NAV-szövegekben idézett jogszabályok listája

Minden forrásból három fájl készül a manifest `mappa` mezője szerint (NAV: torvenytar/docs/NAV/<év>/, jogszabály: torvenytar/docs/<törvény>/<év>/):
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
TORV = ROOT / "torvenytar"
DOCS = TORV / "docs"  # a törvények és a NAV-oldalak szövegei: docs/<törvény>/<év>/, docs/NAV/<év>/
GRAPH = TORV / "graph"  # a Graphify törvénytérkép kész kimenete (verziózott; személyes adat nincs benne)
MANIFEST = TORV / "forrasok.json"
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


RE_ALLAPOT_NJT = re.compile(r"^(\d{4}\.\d{2}\.\d{2}\.)$")
RE_HATALY_JOGTAR = re.compile(r"^Hatály:\s*\(\s*(.+?)\s*\)\s*$")
RE_MELL_FEJ = re.compile(r"^(\d+(?:/[A-Z])?)\. számú melléklet (?:a|az) ")
RE_MELL_HIV = re.compile(r"(\d+(?:/[A-Z])?)\. számú melléklet")


def roman_upper(n: int) -> str:
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, r in vals:
        while n >= v:
            out += r
            n -= v
    return out


def njt_azonosito(url: str):
    """https://njt.hu/jogszabaly/<év>-<szám>-00-00 -> (év, szám); más URL-re None."""
    m = re.search(r"/jogszabaly/(\d{4})-(\d+)-00-00(?:\.\d+)?$", url or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def jogtar_url(item: dict):
    """A net.jogtar.hu (Hatályos Jogszabályok Gyűjteménye) ugyanazon törvényre: ez a MELLÉKLETEKET is tartalmazza, az njt.hu főoldali
    szövege nem. Azonosító: 1900-as évek: '9'+yy+5 jegyű sorszám, 2000-es évek: 'a'+yy+sorszám (pl. 1995/117 -> 99500117.tv, 2017/150 -> a1700150.tv).
    Kézzel felülírható: a jegyzék `jogtar_url` mezője; `jogtar_url: false` kikapcsolja."""
    if item.get("jogtar_url") is False:
        return None
    if item.get("jogtar_url"):
        return item["jogtar_url"]
    az = njt_azonosito(item.get("url", ""))
    if not az or item.get("tipus") != "torveny":
        return None
    ev, sz = az
    pre = "9" if ev < 2000 else "a"
    return f"https://net.jogtar.hu/jogszabaly?docid={pre}{ev % 100:02d}{sz:05d}.tv"


def hatalyos_allapot(text: str, forras: str):
    """A hatályos állapot jelzése a szövegből: njt.hu: a cím alatti dátum sor; net.jogtar.hu: a 'Hatály: ( ... )' sor. Nincs találat: None."""
    for l in text.splitlines()[:80]:
        l = l.strip()
        m = (RE_ALLAPOT_NJT if forras == "njt" else RE_HATALY_JOGTAR).match(l)
        if m:
            return m.group(1)
    return None


def melleklet_fejlecek(text: str):
    return {m.group(1) for l in text.splitlines() if (m := RE_MELL_FEJ.match(l.strip()))}


def melleklet_hivatkozasok(text: str):
    return {m.group(1) for m in RE_MELL_HIV.finditer(text)}


def elozo_mentes(out_dir: Path, nev: str) -> str:
    """--ujra előtt a régi változat (eredeti, txt, md, forrásadat, jogtar-kiegészítés) az elozo/<letöltés dátuma>/ mappába kerül: a forrást nem írjuk felül."""
    meta_p = out_dir / f"{nev}.forras.json"
    if not meta_p.exists():
        return ""
    try:
        mikor = json.loads(meta_p.read_text(encoding="utf-8")).get("letoltve", "")[:10] or "ismeretlen"
    except Exception:
        mikor = "ismeretlen"
    cel = out_dir / "elozo" / mikor
    cel.mkdir(parents=True, exist_ok=True)
    for f in sorted(out_dir.glob(f"{nev}.*")):
        if f.is_file():
            dst = cel / f.name
            if dst.exists():
                dst = cel / (datetime.now().strftime("%H%M%S_") + f.name)
            shutil.move(str(f), str(dst))
    return str(cel.relative_to(ROOT)).replace("\\", "/")


def jogtar_kiegeszites(item: dict, out_dir: Path, force: bool) -> None:
    """A törvény net.jogtar.hu-s változata (mellékletekkel): `<név>.jogtar.html/.txt` + `<név>.jogtar.forras.json`. Hiba nem állítja meg a fő letöltést."""
    url = jogtar_url(item)
    if not url:
        return
    meta_p = out_dir / f"{item['nev']}.jogtar.forras.json"
    if meta_p.exists() and not force:
        return
    try:
        data, status, ctype, lastmod, final = fetch(url)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  FIGYELEM: a mellékleteket tartalmazó net.jogtar.hu-változat nem érhető el ({e}); a mellékletek hiányozhatnak.")
        return
    raw_p = out_dir / f"{item['nev']}.jogtar.html"
    raw_p.write_bytes(data)
    text, title = html_to_text(data)
    (out_dir / f"{item['nev']}.jogtar.txt").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": item.get("id"), "url": url, "vegso_url": final, "letoltve": datetime.now().isoformat(timespec="seconds"), "http_allapot": status,
            "cim": title or None, "bajt": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eredeti_fajl": raw_p.name,
            "szovegkivonat": f"{item['nev']}.jogtar.txt", "szovegkivonat_karakter": len(text),
            "hatalyos_allapot": hatalyos_allapot(text, "jogtar"), "mellekletek": sorted(melleklet_fejlecek(text)),
            "megjegyzes": "kiegészítő forrás: a mellékleteket tartalmazza (az njt.hu főoldali szövege nem); állítás előtt az njt.hu szövegével is vesd össze"}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  + net.jogtar.hu kiegészítés: {len(text)} karakter, hatály: {meta['hatalyos_allapot']}, mellékletek: {', '.join(meta['mellekletek']) or 'nincs'}")


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
        jogtar_kiegeszites(item, out_dir, False)  # a régebbi letöltésekhez utólag hozzáteszi a mellékleteket
        return True
    try:
        data, status, ctype, lastmod, final = fetch(item["url"])
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"HIBA: {item['url']}: {e}")
        return False
    regi_sha = None
    if meta_p.exists():  # --ujra: a régi változat megmarad az elozo/ mappában; a változást kimondjuk
        try:
            regi_sha = json.loads(meta_p.read_text(encoding="utf-8")).get("sha256")
        except Exception:
            regi_sha = None
        print(f"  a korábbi változat megőrizve: {elozo_mentes(out_dir, item['nev'])}")
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
    sha = hashlib.sha256(data).hexdigest()
    meta = {"id": item.get("id"), "url": item["url"], "vegso_url": final, "letoltve": datetime.now().isoformat(timespec="seconds"),
            "http_allapot": status, "tartalomtipus": ctype, "last_modified": lastmod or None, "cim": title or None,
            "bajt": len(data), "sha256": sha, "eredeti_fajl": raw_p.name,
            "szovegkivonat": f"{item['nev']}.txt", "szovegkivonat_karakter": len(text), "megjegyzes": item.get("megjegyzes")}
    if item.get("tipus") == "torveny" and not is_pdf:
        meta["hatalyos_allapot"] = hatalyos_allapot(text, "njt")
        az = njt_azonosito(item["url"])
        if az:  # a letöltött szöveg tényleg a kért törvény-e: a számot a címből ellenőrizzük, nem a jegyzékből hisszük el
            vart = f"{az[0]}. évi {roman_upper(az[1])}. törvény"
            meta["varhato_cim"] = vart
            meta["cim_egyezik"] = vart in (title or "") or vart in text[:3000]
            if not meta["cim_egyezik"]:
                print(f"  🔴 FIGYELEM: a letöltött oldal címe nem egyezik a várt törvénnyel ({vart}); a forrást ne használd, amíg nincs ellenőrizve.")
        if not meta["hatalyos_allapot"]:
            print("  FIGYELEM: a hatályos állapot dátumát nem találtam a szövegben (az oldal szerkezete változhatott).")
    if regi_sha:
        meta["elozo_sha256"] = regi_sha
        meta["valtozott_az_elozohoz_kepest"] = regi_sha != sha
        print("  " + ("🔴 A FORRÁS VÁLTOZOTT az előző letöltéshez képest: a szabályfájlokat és a hivatkozott szakaszokat újra ellenőrizni kell (--ellenoriz)."
                      if regi_sha != sha else "A forrás bájtra azonos az előző letöltéssel."))
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"+ {item['mappa']}/{item['nev']}.{ext}: HTTP {status}, {len(data)} bájt, szöveg {len(text)} karakter"
          + (f", cím: {title[:60]}" if title else ""))
    if len(text) < 500:
        print("  FIGYELEM: a szövegkivonat nagyon rövid; az oldal lehet, hogy JavaScripttel tölti be a tartalmat.")
    jogtar_kiegeszites(item, out_dir, force)
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
    korpusz_szabalyok_ir()
    print("Következő lépés: a Graphify skill futtatása a korpuszon (lásd a SKILL.md 4. pontját).")


REFS = ROOT / ".claude" / "skills" / "nav-forrasok" / "references"


def korpusz_szabalyok_ir():
    """A Graphify alügynökeinek közös azonosító-szótára: references/korpusz-szabalyok.md sablon + references/torvenyek-aliasok.json
    -> data/graphify/torvenyek/graphify-out/.graphify_corpus_rules.md. Minden alügynök prompthoz ezt kell adni (SKILL.md 4. pont)."""
    d = json.loads((REFS / "torvenyek-aliasok.json").read_text(encoding="utf-8"))
    tv = " | ".join(f"{k} = {v['nev']}" for k, v in d["torvenyek"].items())
    nav = " | ".join(d["nav_forrasok"])
    fog = ", ".join("fogalom_" + x for x in d["fogalmak"])
    alias = [f"- " + ", ".join(f'"{a}"' for a in v["alias_szoveg"]) + f" -> {k}" for k, v in d["torvenyek"].items() if v.get("alias_szoveg")]
    alias += [f"- {x}" for x in d.get("alias_kiegeszites", [])]
    szoveg = (REFS / "korpusz-szabalyok.md").read_text(encoding="utf-8")
    szoveg = szoveg.replace("{{TORVENYEK}}", tv).replace("{{NAV}}", nav).replace("{{FOGALMAK}}", fog).replace("{{ALIASOK}}", "\n".join(alias))
    ki = CORPUS / "graphify-out" / ".graphify_corpus_rules.md"
    ki.parent.mkdir(parents=True, exist_ok=True)
    ki.write_text(szoveg, encoding="utf-8", newline="\n")
    print(f"Korpusz-szabályfájl (közös azonosítók, alias-tábla): {ki.relative_to(ROOT)}")


def cmd_graf_ellenoriz():
    """A Graphify gráf INFERRED éleinek szöveges ellenőrzése (graf_ellenorzes.py)."""
    return subprocess.run([sys.executable, "-I", str(Path(__file__).resolve().parent / "graf_ellenorzes.py")]).returncode


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
ALIASOK = {(2007, 127): "afa-tv", (1995, 117): "szja-tv", (2018, 52): "szocho-tv", (1990, 100): "htv", (2017, 150): "art", (2019, 122): "tbj",
           (2009, 115): "evectv", (1999, 121): "kamarai-tv", (2022, 13): "kata-tv"}  # (év, sorszám) -> rövid mappanév
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
            print(f"+ új forrás a jegyzékben: {ev}. évi {roman(sz).upper()}. törvény -> torvenytar/docs/{alias}/{ido}/")
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


# ------------------------------------------------------------------ ellenőrzés: források és szabályhivatkozások
# A szabályfájlokban (.claude/rules, SKILL.md) idézett törvényhelyek (pl. "Szja tv. 47. § (5)", "Áfa tv. 4/A. melléklet") léteznek-e a letöltött
# szövegben. CSAK a szakasz/melléklet MEGLÉTÉT ellenőrzi, a tartalmi egyezést nem: azt a hivatkozott szakasz elolvasásával kell eldönteni.
TORVENY_MAPPA = {"szja tv.": "szja-tv", "szocho tv.": "szocho-tv", "tbj.": "tbj", "htv.": "htv", "áfa tv.": "afa-tv", "art.": "art",
                 "evectv.": "evectv", "kata tv.": "kata-tv", "kamarai tv.": "kamarai-tv"}
RE_TORVENY_HIV = re.compile(r"\b(Szja tv\.|Szocho tv\.|Tbj\.|Htv\.|Áfa tv\.|Art\.|Evectv\.|Kata tv\.|Kamarai tv\.|1999\. évi CXXI\. tv\.)", re.I)
RE_PAR = re.compile(r"(?<![\d/])(\d+(?:/[A-Z])?)\.\s*§")
RE_MELL = re.compile(r"(?<![\d/])(\d+(?:/[A-Z])?)\.\s*(?:számú\s+)?melléklet")
REF_FAJLOK = [".claude/rules/*.md", ".claude/skills/*/SKILL.md", "CLAUDE.md"]
# a törvényrövidítés UTÁN közvetlenül következő szakasz/melléklet-hivatkozások (pl. "Szja tv. 29. § és 47. § (5)", "Áfa tv. 4/A. melléklet");
# a távolabbi említéseket nem tulajdonítjuk a törvénynek
_ELEM = r"(?:\d+(?:/[A-Z])?\.\s*§(?:\s*\(\d+[a-z]?\))*|\d+(?:/[A-Z])?\.\s*(?:számú\s+)?melléklet)"
RE_HIV_FUTAM = re.compile(rf"\s*{_ELEM}(?:\s*(?:,|;|–|és|valamint|vagy)\s*{_ELEM})*")


def torveny_szovegek(mappa: str) -> list:
    """A törvény minden letöltött szövege (njt.hu főszöveg + net.jogtar.hu kiegészítés), a legutóbbi évmappából."""
    d = DOCS / mappa
    if not d.exists():
        return []
    ev = sorted(p for p in d.iterdir() if p.is_dir())
    return [] if not ev else [t.read_text(encoding="utf-8") for t in sorted(ev[-1].glob("*.txt"))]


def cmd_ellenoriz() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))["forrasok"]
    hibak, figy, jegyzek = 0, 0, []
    print("== Források állapota ==")
    for it in man:
        if it["tipus"] != "torveny":
            continue
        d = DOCS / it["mappa"]
        meta_p, jt_p = d / f"{it['nev']}.forras.json", d / f"{it['nev']}.jogtar.forras.json"
        if not meta_p.exists():
            print(f"🔴 {it['mappa']}: nincs letöltve (futtasd: forras_letoltes.py)")
            hibak += 1
            continue
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        jt = json.loads(jt_p.read_text(encoding="utf-8")) if jt_p.exists() else None
        kor = (datetime.now() - datetime.fromisoformat(m["letoltve"])).days if m.get("letoltve") else None
        njt_hatal = m.get("hatalyos_allapot")
        if not njt_hatal and (d / m.get("szovegkivonat", "")).is_file():  # a javítás előtti letöltésekhez: a szövegből olvassuk ki
            njt_hatal = hatalyos_allapot((d / m["szovegkivonat"]).read_text(encoding="utf-8"), "njt")
        sor = [f"hatály (njt.hu, állapot-dátum): {njt_hatal or 'nem állapítható meg'}" + (f"; net.jogtar.hu: {jt['hatalyos_allapot']}" if jt and jt.get("hatalyos_allapot") else ""),
               f"letöltve {kor} napja" if kor is not None else "letöltés ideje ismeretlen"]
        jel = "✅"
        if m.get("cim_egyezik") is False:
            jel, hibak = "🔴", hibak + 1
            sor.append("a cím NEM egyezik a várt törvénnyel")
        if kor is not None and kor > 30:
            jel = "🟡" if jel == "✅" else jel
            figy += 1
            sor.append("30 napnál régebbi: a törvény módosulhatott, `--ujra` és a változás-jelzés ellenőrzése")
        if jt:
            sor.append(f"mellékletek (jogtar): {', '.join(jt.get('mellekletek') or []) or 'nincs'}")
        text = "\n".join(torveny_szovegek(it["mappa"].split("/")[0]))
        hiv = melleklet_hivatkozasok(text) if text else set()
        jelen = melleklet_fejlecek(text) if text else set()
        hianyzo = sorted(hiv - jelen, key=lambda x: (int(re.match(r"\d+", x).group()), x))
        if hianyzo:
            sor.append(f"hivatkozott, de a szövegben nem található melléklet: {', '.join(hianyzo)} (lehet másik törvény melléklete)")
        if not jt and jogtar_url(it):
            jel = "🟡" if jel == "✅" else jel
            figy += 1
            sor.append("a mellékleteket tartalmazó kiegészítés nincs letöltve (futtasd újra a letöltést)")
        print(f"{jel} {it['mappa'].split('/')[0]}: " + "; ".join(sor))
        jegyzek.append({"torveny": it["mappa"].split("/")[0], "hatalyos_allapot": m.get("hatalyos_allapot"), "letoltve": m.get("letoltve"),
                        "mellekletek": (jt or {}).get("mellekletek"), "hianyzo_mellekletek": hianyzo})
    print("\n== Szabályfájlokban idézett törvényhelyek ==")
    talalt, hianyzik, ismeretlen = 0, [], []
    szoveg_cache = {}
    for minta in REF_FAJLOK:
        for f in sorted(ROOT.glob(minta)):
            t = f.read_text(encoding="utf-8").replace("*", "").replace("`", "")
            poz = [(m.start(), m.end(), m.group(1)) for m in RE_TORVENY_HIV.finditer(t)]
            for i, (a, b, nev) in enumerate(poz):
                fm = RE_HIV_FUTAM.match(t, b)
                szak = fm.group(0) if fm else ""
                kulcs = "kamarai tv." if "1999" in nev else nev.lower()
                mappa = TORVENY_MAPPA.get(kulcs)
                for tipus, rx in (("§", RE_PAR), ("melléklet", RE_MELL)):
                    for mm in rx.finditer(szak):
                        n = mm.group(1)
                        if mappa not in szoveg_cache:
                            szoveg_cache[mappa] = "\n".join(torveny_szovegek(mappa))
                        sz = szoveg_cache[mappa]
                        if not sz:
                            if (nev, "nincs törvényszöveg") not in ismeretlen:
                                ismeretlen.append((nev, "nincs törvényszöveg"))
                            continue
                        if tipus == "§":
                            ok = re.search(rf"^{re.escape(n)}\. ?§", sz, re.M) is not None
                        else:
                            ok = re.search(rf"^{re.escape(n)}\. számú melléklet (a|az) ", sz, re.M) is not None
                        if ok:
                            talalt += 1
                        else:
                            hianyzik.append((str(f.relative_to(ROOT)).replace("\\", "/"), nev, f"{n}. {tipus}"))
    for fnev, nev, hely in sorted(set(hianyzik)):
        print(f"🔴 {fnev}: {nev} {hely}: nincs meg a letöltött szövegben (hibás hivatkozás, hiányzó melléklet vagy elavult szabály)")
    for nev, ok in ismeretlen:
        print(f"🟡 {nev}: {ok} (nem ellenőrizhető)")
    print(f"Megtalált hivatkozás: {talalt}; hiányzó: {len(set(hianyzik))}. Csak a szakasz/melléklet MEGLÉTÉT ellenőrzi, a tartalmi egyezést nem: azt a szakasz elolvasásával kell megállapítani.")
    out = ROOT / "data" / "torvenytar"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ellenorzes.json").write_text(json.dumps({"ellenorzes": datetime.now().isoformat(timespec="seconds"), "torvenyek": jegyzek,
                                                     "hianyzo_hivatkozasok": sorted(set(hianyzik)), "megtalalt": talalt}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if (hibak or hianyzik) else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="NAV/jogszabály források letöltése módosítás nélkül.")
    ap.add_argument("--graf-ellenoriz", action="store_true", help="a Graphify gráf INFERRED éleinek szöveges ellenőrzése (a gráf felépítése után)")
    ap.add_argument("--ellenoriz", action="store_true", help="a letöltött források állapota és a szabályfájlok törvényhivatkozásainak ellenőrzése (nincs letöltés)")
    ap.add_argument("--ujra", action="store_true", help="már letöltött forrásokat is újra letölti")
    ap.add_argument("--hivatkozasok", action="store_true", help="a NAV-szövegekben idézett törvények listája")
    ap.add_argument("--korpusz", action="store_true", help="csak a Graphify-korpusz újraépítése (nincs letöltés)")
    a = ap.parse_args()
    if not MANIFEST.exists():
        sys.exit(f"HIBA: nincs {MANIFEST.relative_to(ROOT)}")
    if a.graf_ellenoriz:
        sys.exit(cmd_graf_ellenoriz())
    if a.ellenoriz:
        sys.exit(cmd_ellenoriz())
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

#!/usr/bin/env python3
"""NAV-bevallások és adószámla-kivonatok (PDF) feldolgozása duplikáció nélkül (input/nav-egyenleg/*.pdf).

Használat:
    python -I .claude/skills/adofizetes/scripts/bevallasok.py            # új PDF-ek feldolgozása
    python -I .claude/skills/adofizetes/scripts/bevallasok.py --lista    # a nyilvántartott bevallások listája

Minden PDF-ről megállapítja a típust és a bevallási időszakot (a szövegéből, nem a fájlnevéből), majd a nyilvántartással
(data/nav-egyenleg/bevallasok.json; a könyvelői iratokból is előtöltve) veti össze:
  - azonos típus + időszak + azonos tartalom (vagy azonos kulcsadatok) -> DUPLIKÁTUM: nem dolgozza fel újra, az
    archive/nav-egyenleg/duplikatumok/ mappába kerül (nem törlődik);
  - azonos típus + időszak, de ELTÉRŐ kulcsadat -> ELLENTMONDÁS: a fájl az input/-ban marad, a script megáll (3-as kilépési kód),
    és a felhasználónak kell dönteni;
  - új -> az archive/vallalkozas-iratok/<év>/04-adozas/ alá kerül, Markdown a data/vallalkozas/iratok-md/ alá, nyilvántartásba vétel.
Szabályok: .claude/rules/adatkezeles.md, .claude/rules/nincs-becsles.md. Az összegeket a script olvassa ki, nem az AI.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
import azonosito  # noqa: E402
IN = ROOT / "input" / "nav-egyenleg"
import bemenet  # noqa: E402
bemenet.takarit_kilepeskor(IN)
REG = ROOT / "data" / "nav-egyenleg" / "bevallasok.json"
KONYVELO = ROOT / "data" / "konyvelo" / "konyvelo_adatok.json"
DUP = ROOT / "archive" / "nav-egyenleg" / "duplikatumok"
ARCHIVE = ROOT / "archive" / "vallalkozas-iratok"  # <év>/04-adozas/<mappa>: az iratok az évük szerint csoportosítva
MD = ROOT / "data" / "vallalkozas" / "iratok-md"
PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"


def ft(n):
    return f"{int(n):,}".replace(",", " ") + " Ft"


def pdftotext():
    exe = shutil.which("pdftotext")
    if exe:
        return exe
    for c in (r"C:\Program Files\Git\mingw64\bin\pdftotext.exe", r"C:\Program Files\Git\usr\bin\pdftotext.exe"):
        if Path(c).exists():
            return c
    sys.exit("HIBA: nincs pdftotext")


def text_of(p: Path) -> str:
    return subprocess.run([pdftotext(), "-raw", "-enc", "UTF-8", "-q", str(p), "-"], capture_output=True, text=True,
                          encoding="utf-8").stdout


def tail_int(line):
    m = re.search(r"(\d{1,3}(?: \d{3})+|\d+)\s*$", line)
    return int(m.group(1).replace(" ", "")) if m else None


def classify(txt: str):
    """-> (tipus, idoszak, kulcsadatok, mappa) vagy None, ha ismeretlen."""
    m = re.search(r"Bevallási időszak (\d{4})\.(\d\d)\.(\d\d) - (\d{4})\.(\d\d)\.(\d\d)", txt)
    if m and re.search(r"^2658\s*$", txt, re.M):
        ev, hv = int(m.group(4)), int(m.group(5))
        q = (hv - 1) // 3 + 1
        szocho = tbj = alap = 0
        for l in txt.splitlines():
            if "(258-as adónem)" in l:
                szocho += tail_int(l) or 0
            elif "(406-os adónem)" in l:
                tbj += tail_int(l) or 0
            elif l.startswith("1. Szociális hozzájárulási adó alapja"):
                alap += tail_int(l) or 0
        return ("2658", f"{ev}-Q{q}", {"tbj": tbj, "szocho": szocho, "jarulekalap": alap}, f"nav/{ev}/q{q}-jarulekbevallas")
    m = re.search(r"25SZJA BEVALLÁS a (\d{4})\. évre", txt)
    if m:
        return ("25SZJA", m.group(1), {}, f"nav/{int(m.group(1)) + 1}/25szja-bevallas")
    m = re.search(r"^(\d\d)EGYSZA\s*$", txt, re.M)
    if m:  # az űrlapkód első két számjegye az adóév (pl. 25 -> 2025); a beküldés a következő évben történik
        ev = 2000 + int(m.group(1))
        return (f"{m.group(1)}EGYSZA", str(ev), {}, f"nav/{ev + 1}/{m.group(1)}egysza-nyilatkozat")
    if "ADÓSZÁMLA KIVONAT" in txt:
        d = re.search(r"(\d{4})\.(\d\d)\.(\d\d)\.", txt)
        return ("helyi-ado-kivonat", f"{d.group(1)}-{d.group(2)}-{d.group(3)}" if d else "ismeretlen", {},
                "helyi-adok/adoszamla-kivonatok")
    return None


def content_hash(txt: str) -> str:
    t = re.sub(r"Nyomtatvány verzió:.*", "", txt)
    t = re.sub(r"Nyomtatva: [\d. ]+", "", t)
    return hashlib.sha256(re.sub(r"\s+", "", t).encode()).hexdigest()


def load_reg():
    reg = json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {"bevallasok": {}}
    # előtöltés: a könyvelői iratokból az már feldolgozott 2658-ak (az összeg az utalandó iratokból jön)
    if KONYVELO.exists():
        k = json.loads(KONYVELO.read_text(encoding="utf-8"))
        for x in k["iratok"]:
            if x["tipus"] == "2658" and x.get("ev"):
                key = f"2658|{x['ev']}-Q{x['negyedev']}"
                if key not in reg["bevallasok"]:
                    tbj = sum(t["osszeg"] for y in k["iratok"] if y["tipus"] == "utalando" and y.get("ev") == x["ev"]
                              and y.get("negyedev") == x["negyedev"] for t in y["tetelek"] if t["adonem"] == "TBJ")
                    szocho = sum(t["osszeg"] for y in k["iratok"] if y["tipus"] == "utalando" and y.get("ev") == x["ev"]
                                 and y.get("negyedev") == x["negyedev"] for t in y["tetelek"] if t["adonem"] == "SZOCHO")
                    reg["bevallasok"][key] = {"forras": "konyvelo/" + x["fajl"], "sha256": [x["sha256"]], "tartalom_hash": [],
                                              "kulcsadatok": {"tbj": tbj, "szocho": szocho} if tbj or szocho else {},
                                              "kulcsadat_forras": "a könyvelő 'Utalandó' irataiból"}
    return reg


def process():
    pdfs = bemenet.fajlok(IN, (".pdf",))  # almappákkal együtt, kis/nagybetű független
    if not pdfs:
        print("Nincs feldolgozandó PDF az input/nav-egyenleg/ mappában.")
        return 0
    reg = load_reg()
    konfliktus = 0
    for p in pdfs:
        raw = hashlib.sha256(p.read_bytes()).hexdigest()
        txt = text_of(p)
        try:
            azonosito.ellenoriz(txt, p.name, "adofizetes", "NAV-irat")
        except azonosito.AzonositoHiba as e:
            print(f"🔴 {e}")
            konfliktus += 1
            continue
        c = classify(txt)
        if not c:
            print(f"❓ {p.name}: ismeretlen irattípus; nem dolgoztam fel, az input/-ban maradt. Mi ez a dokumentum?")
            konfliktus += 1
            continue
        tipus, per, kulcs, mappa = c
        key = f"{tipus}|{per}"
        ch = content_hash(txt)
        e = reg["bevallasok"].get(key)
        if e is not None:
            same = raw in e.get("sha256", []) or ch in e.get("tartalom_hash", [])
            if not same and kulcs and e.get("kulcsadatok"):
                kozos = [k for k in kulcs if k in e["kulcsadatok"]]
                if kozos and all(kulcs[k] == e["kulcsadatok"][k] for k in kozos):
                    same = True
                elif kozos:
                    r = "; ".join(f"{k}: új {ft(kulcs[k])} ≠ korábbi {ft(e['kulcsadatok'][k])}" for k in kozos if kulcs[k] != e["kulcsadatok"][k])
                    print(f"🔴 ELLENTMONDÁS: {p.name} ({tipus}, {per}) eltér a korábban nyilvántartottól ({e['forras']}): {r}. "
                          f"A fájl az input/-ban maradt; kérdés a felhasználónak: melyik a helyes/érvényes?")
                    konfliktus += 1
                    continue
            if same or (e is not None and not kulcs and ch in e.get("tartalom_hash", [])):
                DUP.mkdir(parents=True, exist_ok=True)
                dst = DUP / p.name
                if dst.exists():
                    dst = DUP / (datetime.now().strftime("%Y%m%dT%H%M%S_") + p.name)
                shutil.move(str(p), str(dst))
                e.setdefault("sha256", []).append(raw)
                e.setdefault("tartalom_hash", []).append(ch)
                if kulcs and not e.get("kulcsadatok"):
                    e["kulcsadatok"] = kulcs
                e.setdefault("duplikatumok", []).append(p.name)
                print(f"= DUPLIKÁTUM: {p.name} ({tipus}, {per}) már nyilvántartva ({e['forras']}); nem dolgoztam fel újra, "
                      f"áthelyezve: archive/nav-egyenleg/duplikatumok/")
                continue
            print(f"❓ {p.name} ({tipus}, {per}): azonos időszakról már van irat ({e['forras']}), de a tartalom nem hasonlítható össze "
                  f"(nincs közös kulcsadat). Az input/-ban maradt; kérdés a felhasználónak.")
            konfliktus += 1
            continue
        # új irat
        ev_dir = re.search(r"(?<!\d)((?:19[89]|20[0-4])\d)(?!\d)", mappa) or re.search(r"(?<!\d)((?:19[89]|20[0-4])\d)(?!\d)", per)
        ev_dir = ev_dir.group(1) if ev_dir else str(datetime.now().year)
        rel_mappa = f"{ev_dir}/04-adozas/{mappa}"
        dest = ARCHIVE / rel_mappa
        dest.mkdir(parents=True, exist_ok=True)
        name = f"{tipus}_{per}_{p.name}".replace("_download.pdf", "_adoszamla-kivonat.pdf")
        dst = dest / name
        shutil.move(str(p), str(dst))
        if hashlib.sha256(dst.read_bytes()).hexdigest() != raw:
            print(f"HIBA: hash eltérés áthelyezés után: {name}")
            return 1
        mdp = MD / rel_mappa / (dst.stem + ".md")
        mdp.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-I", str(PDFMD), "--fajl", str(dst), "--ki", str(mdp)], capture_output=True, text=True, encoding="utf-8")
        reg["bevallasok"][key] = {"forras": str(dst.relative_to(ROOT)).replace("\\", "/"), "sha256": [raw], "tartalom_hash": [ch],
                                  "kulcsadatok": kulcs, "feldolgozva": datetime.now().isoformat(timespec="seconds")}
        ki = ", ".join(f"{k}: {ft(v)}" for k, v in kulcs.items())
        print(f"+ ÚJ: {tipus}, {per} -> archive/vallalkozas-iratok/{rel_mappa}/" + (f" ({ki})" if ki else ""))
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return 3 if konfliktus else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--lista", action="store_true")
    a = ap.parse_args()
    if a.lista:
        for k, v in sorted(load_reg()["bevallasok"].items()):
            print(k, "|", v["forras"], "|", v.get("kulcsadatok"))
        return
    sys.exit(process())


if __name__ == "__main__":
    main()

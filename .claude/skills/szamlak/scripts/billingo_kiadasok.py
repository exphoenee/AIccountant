#!/usr/bin/env python3
"""Billingo bejövő számlák / kiadások (spendings) lekérése (csak olvasás).

Használat:
    python -I .claude/skills/szamlak/scripts/billingo_kiadasok.py 2026-01-01 2026-12-31

Az API kulcsot a repo gyökerében lévő .env fájlból olvassa (BILLING_API_KEY); nem írja ki.
Kimenet: data/kiadasok/kiadasok_<tol>_<ig>.json

Fontos (nem ellenőrzött): a /spendings végpont dátumszűrő paramétereit és a tételek mezőneveit nem tudtam
ellenőrizni, mert a Billingóban jelenleg nincs rögzített bejövő számla (total = 0). Ezért a script SZŰRÉS NÉLKÜL
kéri le az összes tételt, és a nyers adatot menti; az időszakra szűrést a feldolgozó (adoreport) végzi a
tételben megtalált dátummezők alapján, és jelzi, ha ilyet nem talál.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

API = "https://api.billingo.hu/v3"
ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "data" / "kiadasok"


def load_key() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("BILLING_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    sys.exit(0)  # nincs kulcs: csendben átugorjuk az adatok beszerzését


def get(path: str, key: str, params: dict) -> dict:
    url = f"{API}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-API-KEY": key, "Accept": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** attempt)
                continue
            if e.code in (401, 403):
                sys.exit(f"Hiba: hitelesítés sikertelen (HTTP {e.code}). Ellenőrizd a BILLING_API_KEY-t.")
            sys.exit(f"Hiba: HTTP {e.code} – {e.read().decode('utf-8', 'replace')[:300]}")
        except urllib.error.URLError:
            time.sleep(2 ** attempt)
    sys.exit(f"Hiba: a Billingo nem elérhető ({path}).")


def azonosito_ellenorzes(key: str) -> None:
    """Az API-kulcs ugyanahhoz a vállalkozáshoz tartozik-e, mint a vállalkozói profil (adószám törzse)? Eltérésnél megáll."""
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import azonosito
    import re as _re
    try:
        d = azonosito.megvan_vagy_leall("szamlak")
    except azonosito.AzonositoHiba as e:
        print(e)
        sys.exit(4)
    org = get("/organization", key, {})
    if _re.sub(r"\D", "", org.get("tax_code") or "")[:8] != _re.sub(r"\D", "", d["adoszam"])[:8]:
        print("MEGÁLLTAM (szamlak): a BILLING_API_KEY másik vállalkozás Billingo-fiókjához tartozik, mint a vállalkozói profilod "
              f"(a fiók adószáma {azonosito.maszk(org.get('tax_code') or '')}, a profilé {azonosito.maszk(d['adoszam'])}). Mit tegyél: "
              "ellenőrizd a .env fájlban a BILLING_API_KEY-t (a saját Billingo-fiókod kulcsa kell), majd futtasd újra. Számlát nem mentettem.")
        sys.exit(4)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Billingo bejövő számlák (spendings) lekérése.")
    ap.add_argument("tol", type=date.fromisoformat, help="kezdő dátum (ÉÉÉÉ-HH-NN)")
    ap.add_argument("ig", type=date.fromisoformat, help="záró dátum (ÉÉÉÉ-HH-NN)")
    a = ap.parse_args()
    if a.tol > a.ig:
        sys.exit("Hiba: a kezdő dátum későbbi, mint a záró dátum.")
    key = load_key()
    azonosito_ellenorzes(key)
    items, page, total = [], 1, 0
    while True:
        r = get("/spendings", key, {"page": page, "per_page": 100})
        items.extend(r.get("data", []))
        total = r.get("total", len(items))
        if page >= int(r.get("last_page", 1)):
            break
        page += 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"kiadasok_{a.tol}_{a.ig}.json"
    p.write_text(json.dumps({
        "lekerve": datetime.now().isoformat(timespec="seconds"), "tol": a.tol.isoformat(), "ig": a.ig.isoformat(),
        "total_a_billingoban": total, "szures": "nincs (a végpont szűrőit nem ellenőriztem)", "tetelek": items,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(items)} bejövő számla/kiadás a Billingóban (szűrés nélkül).")
    print(f"Mentve: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

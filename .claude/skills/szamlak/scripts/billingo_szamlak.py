#!/usr/bin/env python3
"""Billingo számlák lekérése egy megadott időszakra (csak olvasás).

Használat:
    python .claude/skills/szamlak/scripts/billingo_szamlak.py 2026-01-01 2026-03-31

Az API kulcsot a repo gyökerében lévő .env fájlból olvassa (BILLING_API_KEY).
Kimenet: data/szamlak/szamlak_<tol>_<ig>.json (teljes nyers adat, tételekkel)
        és .csv (összefoglaló, HUF-értékekkel)
Csak GET kéréseket küld, külső csomag nem kell.
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.billingo.hu/v3"
ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "data" / "szamlak"
PER_PAGE = 100


def load_key() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BILLING_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    sys.exit(0)  # nincs kulcs: csendben átugorjuk az adatok beszerzését


def get(path: str, key: str, params: dict | None = None) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
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
        except urllib.error.URLError as e:
            time.sleep(2 ** attempt)
            last = e
    sys.exit(f"Hiba: a Billingo nem elérhető ({path}).")


def parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Érvénytelen dátum: {s} (formátum: ÉÉÉÉ-HH-NN)")


def fetch_documents(key: str, tol: date, ig: date) -> list[dict]:
    docs, page = [], 1
    while True:
        r = get("/documents", key, {
            "page": page, "per_page": PER_PAGE,
            "start_date": tol.isoformat(), "end_date": ig.isoformat(),
        })
        docs.extend(r.get("data", []))
        if page >= int(r.get("last_page", 1)):
            return docs
        page += 1


def flat(d: dict) -> dict:
    partner = d.get("partner") or {}
    return {
        "id": d.get("id"),
        "szamlaszam": d.get("invoice_number"),
        "tipus": d.get("type"),
        "kelt": d.get("invoice_date"),
        "teljesites": d.get("fulfillment_date"),
        "fizetesi_hatarido": d.get("due_date"),
        "fizetes_modja": d.get("payment_method"),
        "fizetesi_statusz": d.get("payment_status"),
        "fizetve_datum": d.get("paid_date"),
        "deviza": d.get("currency"),
        "arfolyam": d.get("conversion_rate"),
        "netto": (d.get("summary") or {}).get("net_amount"),
        "brutto": d.get("gross_total"),
        "netto_huf": (d.get("summary") or {}).get("net_amount_local"),
        "brutto_huf": (d.get("summary") or {}).get("gross_amount_local"),
        "vevo": partner.get("name"),
        "vevo_adoszam": partner.get("taxcode"),
        "megjegyzes": d.get("comment"),
        "storno": d.get("cancelled"),
        "tetelek_szama": len(d.get("items") or []),
    }


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
    ap = argparse.ArgumentParser(description="Billingo számlák lekérése időszakra.")
    ap.add_argument("tol", type=parse_date, help="kezdő dátum (ÉÉÉÉ-HH-NN)")
    ap.add_argument("ig", type=parse_date, help="záró dátum (ÉÉÉÉ-HH-NN)")
    args = ap.parse_args()
    if args.tol > args.ig:
        sys.exit("Hiba: a kezdő dátum későbbi, mint a záró dátum.")

    key = load_key()
    azonosito_ellenorzes(key)
    docs = fetch_documents(key, args.tol, args.ig)
    print(f"{len(docs)} számla az időszakban ({args.tol} – {args.ig}).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"szamlak_{args.tol}_{args.ig}"
    base.with_suffix(".json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [flat(d) for d in docs]
    with base.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(flat({}).keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)

    print(f"Mentve: {base.with_suffix('.json').relative_to(ROOT)}")
    print(f"        {base.with_suffix('.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()

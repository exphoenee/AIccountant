#!/usr/bin/env python3
"""Közös konfig-betöltő: a config/ fájlok megléte és érthető hibaüzenet hiányuk esetén.

Importálás: sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig
- vallalkozas_ut(): a config/vallalkozas.json útvonala; ha hiányzik, a config/vallalkozas.example.json sablonból létrehozza
  (a null mezőket a felhasználónak kell kitöltenie; a script nem tölt ki értéket).
- szabalyok_ut(ev): a config/szabalyok_<év>.json útvonala; ha hiányzik, megáll (nem becsül).
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"


def vallalkozas_ut() -> Path:
    p = CFG / "vallalkozas.json"
    if not p.exists():
        ex = CFG / "vallalkozas.example.json"
        if not ex.exists():
            sys.exit("HIBA: nincs config/vallalkozas.json és config/vallalkozas.example.json sem. Másold vissza a sablont a repóból.")
        CFG.mkdir(exist_ok=True)
        shutil.copyfile(ex, p)
        print("INFO: a config/vallalkozas.json a sablonból jött létre; a null mezőket (tb_statusz, min_alap_tipus, "
              "vallalkozas_kezdete, ...) a vállalkozó adataiból kell kitölteni. Értéket nem találtam ki.", file=sys.stderr)
    return p


def szabalyok_ut(ev) -> Path:
    p = CFG / f"szabalyok_{ev}.json"
    if not p.exists():
        sys.exit(f"HIBA: nincs config/szabalyok_{ev}.json. Évente új fájl kell: másold a legutóbbit, és a .claude/rules/atalanyado.md és "
                 f"jarulek-szocho.md alapján frissítsd az {ev}. évi értékeket (minimálbér, adómentes keret, bevételi határ, költséghányad).")
    return p

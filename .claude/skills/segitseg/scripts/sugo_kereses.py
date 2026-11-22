"""Súgókeresés: kulcsszavas keresés a repó használati dokumentációjában.

Csak olvas, nem számol, nem ír. Forrás: docs/**/*.md (az Archify HTML/JSON nem), usage.md, README.md, CLAUDE.md,
.claude/skills/*/SKILL.md, .claude/rules/*.md. Használat:
  python -I .claude/skills/segitseg/scripts/sugo_kereses.py "kérdés vagy kulcsszavak" [--max 8]
  python -I .claude/skills/segitseg/scripts/sugo_kereses.py --forrasok
"""
import argparse
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BLOKK_SOR = 14
STOP = {"a", "az", "es", "hogy", "mi", "mit", "hol", "hogyan", "van", "egy", "is", "meg", "nem",
        "de", "ha", "le", "el", "ki", "be", "fel", "kell", "lehet", "ez", "azt", "mert", "vagy",
        "the", "hogyne", "szeretnem", "tudom", "tudnam", "kerlek", "segits"}


def forrasok():
    lista = [ROOT / n for n in ("usage.md", "README.md", "CLAUDE.md")]
    lista += sorted((ROOT / "docs").rglob("*.md"))
    lista += sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    lista += sorted((ROOT / ".claude" / "rules").glob("*.md"))
    return [p for p in lista if p.is_file()]


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


class _Szoveg(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sorok, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr", "section"):
            self.sorok.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.sorok.append(d.strip() + " ")


def sorok_beolvas(p):
    szoveg = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".html":
        k = _Szoveg()
        k.feed(szoveg)
        szoveg = "".join(k.sorok)
    return [s.strip() for s in szoveg.splitlines() if s.strip()]


def blokkok(sorok):
    """Címsor vagy BLOKK_SOR hosszúság szerint darabol; (kezdősor, szöveg)."""
    out, cur, start = [], [], 1
    for i, s in enumerate(sorok, 1):
        if (s.startswith("#") and cur) or len(cur) >= BLOKK_SOR:
            out.append((start, cur))
            cur, start = [], i
        cur.append(s)
    if cur:
        out.append((start, cur))
    return out


def tokenek(kerdes):
    t = [w for w in re.findall(r"[a-z0-9_.\-]+", norm(kerdes)) if w not in STOP and len(w) > 2]
    return list(dict.fromkeys(t))


def pontoz(szoveg_n, toks):
    pont = 0
    for t in toks:
        gyok = t[:max(4, len(t) - 2)]
        n = szoveg_n.count(gyok)
        if n:
            pont += 2 + min(n, 4)
    return pont


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("kerdes", nargs="?")
    ap.add_argument("--max", type=int, default=8)
    ap.add_argument("--forrasok", action="store_true")
    a = ap.parse_args()
    if a.forrasok:
        for p in forrasok():
            print(p.relative_to(ROOT).as_posix())
        return 0
    if not a.kerdes:
        ap.error("add meg a kérdést vagy kulcsszavakat")
    toks = tokenek(a.kerdes)
    if not toks:
        print("Nincs használható kulcsszó a kérdésben.")
        return 1
    talalatok = []
    for p in forrasok():
        rel = p.relative_to(ROOT).as_posix()
        elony = 3 if rel in ("usage.md", "README.md") else 0
        for kezd, bl in blokkok(sorok_beolvas(p)):
            szoveg = "\n".join(bl)
            pt = pontoz(norm(szoveg), toks)
            fej = pontoz(norm(rel + " " + bl[0]), toks)
            if pt:
                talalatok.append((pt + 2 * fej + elony, rel, kezd, szoveg))
    talalatok.sort(key=lambda x: -x[0])
    print(f"Kulcsszavak: {', '.join(toks)}")
    if not talalatok:
        print("Nincs találat a dokumentációban: ezt nem tudom.")
        return 0
    for pt, rel, kezd, szoveg in talalatok[:a.max]:
        print(f"\n=== {rel}:{kezd} (pontszám {pt}) ===")
        print(szoveg[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())

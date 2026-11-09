#!/usr/bin/env bash
# AIccountant telepítő (Linux, macOS, Git Bash): mappák, függőség-ellenőrzés, .env létrehozása API-kulcsokkal.
#
# Használat:
#   ./install.sh                  # interaktív: rákérdez a Billingo és a Számlázz.hu API-kulcsra (Enter = kihagyás)
#   BILLING_API_KEY=... SZAMLAZZ_API_KEY=... ./install.sh --nem-interaktiv
#
# A kulcsokat nem írja ki a képernyőre, és a .env fájl csak a tulajdonos számára olvasható (chmod 600).
# Meglévő .env esetén a már kitöltött értékeket megtartja, csak a hiányzókra kérdez rá.
# Nincs hálózati letöltés, nincs csomagtelepítés: a scriptek csak a Python standard könyvtárát használják.
set -u
cd "$(dirname "$0")" || exit 1

NEM_INTERAKTIV=0
[ "${1:-}" = "--nem-interaktiv" ] && NEM_INTERAKTIV=1

echo "== AIccountant telepítés =="

# 1) Python 3.10+
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "HIBA: Python 3.10 vagy újabb szükséges (python3 nem található)."
  echo "  Linux: sudo apt install python3 | macOS: brew install python | Windows: https://www.python.org/downloads/"
  exit 1
fi
echo "OK   Python: $($PY --version 2>&1)"

# 2) pdftotext (PDF-ek feldolgozásához)
if command -v pdftotext >/dev/null 2>&1; then
  echo "OK   pdftotext: megvan"
else
  echo "FIGYELEM: a pdftotext (poppler) nincs telepítve; PDF-ek feldolgozásához kell."
  echo "  Linux: sudo apt install poppler-utils | macOS: brew install poppler | Windows (Git Bash): a Git for Windows tartalmazza"
fi

# 3) mappák
for d in input/vallalkozas-adatok input/nav-egyenleg input/adonaptar input/konyvelo input/kiadasok input/bevetelek input/torveny input/pdf \
         data archive tax-reports audits docs config torvenytar .claude/memory; do
  mkdir -p "$d"
done
for d in input/vallalkozas-adatok input/nav-egyenleg input/adonaptar input/konyvelo input/kiadasok input/bevetelek input/torveny input/pdf archive tax-reports; do
  [ -e "$d/.gitkeep" ] || : > "$d/.gitkeep"
done
echo "OK   mappák létrehozva"

# 4) .gitignore: az érzékeny mappák ne kerüljenek verziókezelésbe
touch .gitignore
for e in ".env" "data/" "archive/" "input/" "tax-reports/" "config/vallalkozas.json" "config/konyvelo-dontesek.json" "config/ipa_telepulesek.json" ".claude/memory/vallalkozasi-profil.md" ".claude/memory/adonaptar-*.md" "__pycache__/" "*.pyc"; do
  grep -qxF "$e" .gitignore || echo "$e" >> .gitignore
done
echo "OK   .gitignore ellenőrizve"

# 4/b) config/vallalkozas.json a sablonból (a null mezőket a vállalkozónak kell kitöltenie; a fájl nincs verziókezelve)
if [ ! -f config/vallalkozas.json ] && [ -f config/vallalkozas.example.json ]; then
  cp config/vallalkozas.example.json config/vallalkozas.json
  echo "OK   config/vallalkozas.json létrehozva a sablonból (a null mezőket töltsd ki; lásd usage.md)"
fi

# 5) .env
ertek() { # ertek NÉV: a .env-ben lévő érték (üres, ha nincs)
  [ -f .env ] && grep -E "^$1=" .env | head -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}
BILLING="$(ertek BILLING_API_KEY)"
SZAMLAZZ="$(ertek SZAMLAZZ_API_KEY)"
SOROZAT="$(ertek SZAMLAZZ_SOROZAT)"

if [ "$NEM_INTERAKTIV" = "1" ]; then
  BILLING="${BILLING:-${BILLING_API_KEY:-}}"
  SZAMLAZZ="${SZAMLAZZ:-${SZAMLAZZ_API_KEY:-}}"
  SOROZAT="${SOROZAT:-${SZAMLAZZ_SOROZAT:-}}"
else
  echo
  echo "API-kulcsok (Enter = kihagyás; kulcs nélkül az adott forrás adatait a rendszer kihagyja (az adóellenőrzés kiírja, mely források hiányoznak)):"
  if [ -z "$BILLING" ]; then
    printf "  Billingo API-kulcs (csak olvasási jogosultság, Billingo > Beállítások > API): "
    read -r -s BILLING; echo
  else echo "  Billingo API-kulcs: már megvan a .env-ben"; fi
  if [ -z "$SZAMLAZZ" ]; then
    printf "  Számlázz.hu Számla Agent kulcs (Számlázz.hu > Beállítások > Számla Agent): "
    read -r -s SZAMLAZZ; echo
  else echo "  Számlázz.hu kulcs: már megvan a .env-ben"; fi
  if [ -n "$SZAMLAZZ" ] && [ -z "$SOROZAT" ]; then
    printf "  Számlázz.hu számlaszám-minta a lekéréshez, pl. ABC-2026-{n} (Enter = később): "
    read -r SOROZAT
  fi
fi

# a .env egyéb (általunk nem ismert) sorai megmaradnak: csak a három ismert változót és a fejléc-megjegyzést írjuk újra
EXTRA=""
[ -f .env ] && EXTRA="$(grep -vE '^(BILLING_API_KEY|SZAMLAZZ_API_KEY|SZAMLAZZ_SOROZAT)=|^# AIccountant titkok' .env)"
( umask 077
  {
    echo "# AIccountant titkok: NEM verziózott, ne oszd meg."
    echo "BILLING_API_KEY=$BILLING"
    echo "SZAMLAZZ_API_KEY=$SZAMLAZZ"
    echo "SZAMLAZZ_SOROZAT=$SOROZAT"
    [ -n "$EXTRA" ] && printf '%s\n' "$EXTRA"
  } > .env )
chmod 600 .env 2>/dev/null || true
[ -n "$BILLING" ] && echo "OK   .env: BILLING_API_KEY megadva" || echo "INFO .env: BILLING_API_KEY üres (a Billingo-adatok kimaradnak)"
[ -n "$SZAMLAZZ" ] && echo "OK   .env: SZAMLAZZ_API_KEY megadva" || echo "INFO .env: SZAMLAZZ_API_KEY üres (a Számlázz.hu-adatok kimaradnak)"

# 6) önellenőrzés (nem igényel kulcsot)
if [ -f ".claude/skills/adoszamitas/scripts/teszt_nav_peldak.py" ]; then
  if "$PY" -I .claude/skills/adoszamitas/scripts/teszt_nav_peldak.py >/dev/null 2>&1; then
    echo "OK   számítás-önteszt (NAV-példák): megfelelt"
  else
    echo "FIGYELEM: a számítás-önteszt nem futott le; lásd: $PY -I .claude/skills/adoszamitas/scripts/teszt_nav_peldak.py"
  fi
fi

cat <<'KESZ'

Kész. Következő lépések (részletesen: usage.md):
  1. Másold a vállalkozás iratait az input/vallalkozas-adatok/ mappába, majd kérd a Claude-tól a vallalkozas-dokumentumok skillt (ez az ELSŐ lépés).
  2. Utána: input/konyvelo, input/kiadasok, input/bevetelek, input/nav-egyenleg, input/adonaptar mappák.
  3. Adóellenőrzés: "python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py" (csak a vállalkozói profil elkészülte után fut).
KESZ

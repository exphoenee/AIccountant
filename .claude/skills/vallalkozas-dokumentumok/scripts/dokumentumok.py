#!/usr/bin/env python3
"""Vállalkozói iratok feldolgozása: leltár, PDF -> Markdown, besorolási terv, áthelyezés, visszaállítás, vállalkozói profil.

Használat (az input/ alatti `v*adatok` mappára; sorrendben):
    python -I .claude/skills/vallalkozas-dokumentumok/scripts/dokumentumok.py --leltar       # fájlok, méret, SHA-256, duplikátumok
    python -I ... --konvertal                                                              # PDF -> Markdown (pdf-markdown skill)
    python -I ... --terv                                                                   # besorolási terv (NEM módosít semmit)
    python -I ... --vegrehajt                                                              # áthelyezés a terv szerint + napló
    python -I ... --profil                                                                 # vállalkozói profil a config és a tények alapján
    python -I ... --visszaallit                                                            # az áthelyezés visszavonása a naplóból

Folyamat és helyek (lásd .claude/rules/adatkezeles.md):
    input/<v...adatok>/        eredeti iratok            ->  archive/vallalkozas-iratok/<logikus struktúra>/   (feldolgozott nyers fájlok)
    PDF-ek Markdown változata  data/pdf/<v...adatok>/    ->  data/vallalkozas/iratok-md/<ugyanaz a struktúra>/
    napló, terv, leltár, profil                              data/vallalkozas/
A besorolás kizárólag az útvonal (mappa- és fájlnév) alapján történik a config/iratrend.json szabályaival; tartalom alapján nem.
Amit nem tud besorolni, az a 99-ellenorizendo/ mappába kerül. Semmit nem töröl; az áthelyezés visszaállítható.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
INPUT_BASE = ROOT / "input"
DATA = ROOT / "data" / "vallalkozas"
PDFDATA = ROOT / "data" / "pdf"
RULES = ROOT / "config" / "iratrend.json"
PDFMD = ROOT / ".claude" / "skills" / "pdf-markdown" / "scripts" / "pdf_markdown.py"
SAFE = re.compile(r'[<>:"|?*\x00-\x1f]')  # ugyanaz, mint a pdf-markdown mappa-módjában
REST = r"(?:(?P<rest>.*)/)?[^/]+$"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def find_input() -> Path:
    c = [p for p in INPUT_BASE.iterdir() if p.is_dir() and nfc(p.name).lower().startswith("v") and nfc(p.name).lower().endswith("adatok")]
    if len(c) != 1:
        sys.exit("HIBA: az input/ alatt nem találok egyértelműen egy 'v…adatok' mappát: " + ", ".join(p.name for p in c))
    return c[0]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(src: Path):
    for p in sorted(src.rglob("*")):
        if p.is_file():
            yield p, nfc(p.relative_to(src).as_posix())


def load_rules():
    cfg = json.loads(RULES.read_text(encoding="utf-8"))
    rules = [{"nev": r["nev"], "re": re.compile(r["minta"].replace("{REST}", REST), re.I), "cel": r["cel"]} for r in cfg["szabalyok"]]
    return cfg["alap"], rules


def classify(rel: str, rules):
    for r in rules:
        m = r["re"].search(rel)
        if m:
            g = defaultdict(str, {k: (v or "") for k, v in m.groupdict().items()})
            cel = re.sub(r"/{2,}", "/", r["cel"].format_map(g)).strip("/")
            return r["nev"], cel
    parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
    return "nincs-szabaly", "99-ellenorizendo/" + parent


# ------------------------------------------------------------------ parancsok

def cmd_leltar(src: Path):
    DATA.mkdir(parents=True, exist_ok=True)
    items, by_hash = [], defaultdict(list)
    for p, rel in walk(src):
        st = p.stat()
        h = sha256(p)
        items.append({"rel": rel, "kit": p.suffix.lower().lstrip("."), "bajt": st.st_size, "sha256": h,
                      "modositva": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
        by_hash[h].append(rel)
    dups = [v for v in by_hash.values() if len(v) > 1]
    out = {"forras": src.name, "keszult": datetime.now().isoformat(timespec="seconds"), "fajlok": items, "duplikatum_csoportok": dups}
    (DATA / "leltar.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ext = Counter(i["kit"] for i in items)
    print(f"Leltár: {len(items)} fájl, {sum(i['bajt'] for i in items) / 1e6:.1f} MB -> data/vallalkozas/leltar.json")
    print("  kiterjesztés szerint: " + ", ".join(f"{k or '(nincs)'}={v}" for k, v in ext.most_common()))
    print(f"  tartalmilag azonos fájlok (SHA-256): {len(dups)} csoport, {sum(len(v) - 1 for v in dups)} felesleges másolat")
    nonpdf = [i for i in items if i["kit"] != "pdf"]
    print(f"  nem PDF (Markdownná nem alakítható, csak áthelyezhető): {len(nonpdf)} fájl")


def cmd_konvertal(src: Path):
    r = subprocess.run([sys.executable, "-I", str(PDFMD), "--mappa", str(src)], capture_output=True, text=True, encoding="utf-8")
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    print("PDF -> Markdown (pdf-markdown skill):")
    for l in lines[:3]:
        print("  " + l.strip())
    err = [l for l in lines if l.strip().startswith("HIBA")]
    if err:
        print(f"  {len(err)} PDF nem konvertálható (valószínűleg szkennelt kép, OCR nincs): lásd data/pdf/{SAFE.sub('_', src.name)}/_index.json")
    if r.returncode != 0:
        print("  HIBA: " + (r.stderr or "").strip()[:300])


def cmd_terv(src: Path):
    if not (DATA / "leltar.json").exists():
        cmd_leltar(src)
    lt = json.loads((DATA / "leltar.json").read_text(encoding="utf-8"))
    alap, rules = load_rules()
    plan, used, seen = [], Counter(), set()
    for it in lt["fajlok"]:
        szab, cel = classify(it["rel"], rules)
        name = it["rel"].rsplit("/", 1)[-1]
        dest = f"{cel}/{name}"
        n = 2
        while dest.lower() in seen:  # névütközés: sosem írunk felül
            stem, dot, ext = name.rpartition(".")
            dest = f"{cel}/{stem}__{n}.{ext}" if dot else f"{cel}/{name}__{n}"
            n += 1
        seen.add(dest.lower())
        used[szab] += 1
        plan.append({"forras": it["rel"], "cel": dest, "szabaly": szab, "sha256": it["sha256"]})
    (DATA / "athelyezesi-terv.json").write_text(json.dumps({"alap": alap, "keszult": datetime.now().isoformat(timespec="seconds"),
                                                           "tetelek": plan}, ensure_ascii=False, indent=1), encoding="utf-8")
    top, second = Counter(), Counter()
    for p in plan:
        parts = p["cel"].split("/")
        top[parts[0]] += 1
        second["/".join(parts[:2])] += 1
    print(f"Besorolási terv: {len(plan)} fájl -> {alap}/ (NEM történt áthelyezés) -> data/vallalkozas/athelyezesi-terv.json")
    for k in sorted(top):
        print(f"  {k}/  ({top[k]} fájl)")
        for kk in sorted(x for x in second if x.startswith(k + "/")):
            print(f"      {kk.split('/', 1)[1]}  ({second[kk]})")
    unk = [p for p in plan if p["szabaly"] == "nincs-szabaly" or p["cel"].startswith("99-")]
    print(f"  Ellenőrizendő (99-…): {len(unk)} fájl")
    for p in unk[:25]:
        print(f"      {p['forras']}")
    if len(unk) > 25:
        print(f"      ... további {len(unk) - 25}")


def md_pair(src: Path, rel: str):
    """A PDF Markdown-ja a pdf-markdown mappa-módjának helyén: data/pdf/<mappa>/<rel mappa>/<tisztított név>.md (+ .json)."""
    if not rel.lower().endswith(".pdf"):
        return None
    fold = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    # a mappa neve lehet ékezetes vagy ékezet nélküli (az input mappát át lehet nevezni): ékezetfüggetlenül keresünk
    bases = [d for d in PDFDATA.iterdir() if d.is_dir() and fold(d.name) == fold(SAFE.sub("_", src.name))] if PDFDATA.exists() else []
    parent, _, name = rel.rpartition("/")
    stem = SAFE.sub("_", name[:-4])
    for base in bases:
        cand = base / parent / (stem + ".md")
        if cand.exists():
            return cand
    return (bases[0] if bases else PDFDATA / SAFE.sub("_", src.name)) / parent / (stem + ".md")


def prune_empty(root: Path):
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass


def cmd_vegrehajt(src: Path):
    pf = DATA / "athelyezesi-terv.json"
    if not pf.exists():
        sys.exit("HIBA: nincs terv. Előbb: --terv")
    elozo = json.loads((DATA / "athelyezes.json").read_text(encoding="utf-8"))["tetelek"] if (DATA / "athelyezes.json").exists() else []  # újabb iratcsomag: a napló bővül, nem íródik felül
    plan = json.loads(pf.read_text(encoding="utf-8"))
    base = ROOT / plan["alap"]
    todo = []
    for t in plan["tetelek"]:
        s = next((p for p, rel in [(q, nfc(q.relative_to(src).as_posix())) for q in src.rglob("*") if q.is_file()] if rel == t["forras"]), None) \
            if False else None
        todo.append(t)
    existing = {nfc(q.relative_to(src).as_posix()): q for q in src.rglob("*") if q.is_file()}
    missing = [t["forras"] for t in todo if t["forras"] not in existing]
    if missing:
        sys.exit(f"HIBA: {len(missing)} tervezett forrásfájl nincs meg (változott az input?). Futtasd újra: --leltar, --terv. Első: {missing[0]}")
    manifest, moved_md = [], 0
    for t in todo:
        s = existing[t["forras"]]
        d = base / t["cel"]
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            sys.exit(f"HIBA: a cél már létezik, nem írom felül: {d}")
        shutil.move(str(s), str(d))
        entry = {"uj": f"{plan['alap']}/{t['cel']}", "regi": t["forras"], "sha256": t["sha256"]}
        m = md_pair(src, t["forras"])
        if m and m.exists():
            mdest = DATA / "iratok-md" / Path(t["cel"]).parent / (Path(t["cel"]).stem + ".md")
            mdest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(m), str(mdest))
            j = m.with_suffix(".json")
            if j.exists():
                shutil.move(str(j), str(mdest.with_suffix(".json")))
            entry["md_uj"] = str(mdest.relative_to(ROOT)).replace("\\", "/")
            entry["md_regi"] = str(m.relative_to(ROOT)).replace("\\", "/")
            moved_md += 1
        manifest.append(entry)
    (DATA / "athelyezes.json").write_text(json.dumps({"keszult": datetime.now().isoformat(timespec="seconds"), "forras_mappa": src.name,
                                                      "tetelek": elozo + manifest}, ensure_ascii=False, indent=1), encoding="utf-8")
    # ellenőrzés: darabszám és SHA-256 a célon
    bad = [e["uj"] for e in manifest if sha256(ROOT / e["uj"]) != e["sha256"]]
    prune_empty(src)
    left = [p for p in src.rglob("*") if p.is_file()]
    print(f"Áthelyezve: {len(manifest)} fájl -> {plan['alap']}/ ; Markdown átkerült: {moved_md} -> data/vallalkozas/iratok-md/")
    print(f"Ellenőrzés: SHA-256 eltérés: {len(bad)}; az input mappában maradt fájl: {len(left)}")
    print("Napló: data/vallalkozas/athelyezes.json (visszaállítás: --visszaallit)")
    if bad:
        print("  FIGYELEM: eltérő hash: " + ", ".join(bad[:5]))


def cmd_md_rendez(src: Path):
    """Utólag a naplóban szereplő PDF-ek Markdown-ját (és meta .json-ját) a data/vallalkozas/iratok-md/ alá költözteti."""
    mf = DATA / "athelyezes.json"
    if not mf.exists():
        sys.exit("HIBA: nincs áthelyezési napló.")
    man = json.loads(mf.read_text(encoding="utf-8"))
    n = missing = 0
    for e in man["tetelek"]:
        if "md_uj" in e or not e["regi"].lower().endswith(".pdf"):
            continue
        m = md_pair(src, e["regi"])
        if not m or not m.exists():
            missing += 1
            continue
        cel = Path(e["uj"].split("/", 2)[2])  # a plan alap (archive/vallalkozas-iratok) utáni rész
        dest = DATA / "iratok-md" / cel.parent / (cel.stem + ".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(m), str(dest))
        j = m.with_suffix(".json")
        if j.exists():
            shutil.move(str(j), str(dest.with_suffix(".json")))
        e["md_uj"] = str(dest.relative_to(ROOT)).replace("\\", "/")
        e["md_regi"] = str(m.relative_to(ROOT)).replace("\\", "/")
        n += 1
    mf.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Markdown áthelyezve: {n} -> data/vallalkozas/iratok-md/ ; nincs Markdown-ja (szkennelt vagy nem konvertált PDF): {missing}")


def cmd_visszaallit(src: Path):
    mf = DATA / "athelyezes.json"
    if not mf.exists():
        sys.exit("HIBA: nincs áthelyezési napló, nincs mit visszaállítani.")
    man = json.loads(mf.read_text(encoding="utf-8"))
    src.mkdir(parents=True, exist_ok=True)
    n = 0
    for e in man["tetelek"]:
        a, b = ROOT / e["uj"], src / e["regi"]
        if not a.exists():
            print(f"  hiányzik: {e['uj']}")
            continue
        b.parent.mkdir(parents=True, exist_ok=True)
        if b.exists():
            print(f"  a cél már létezik, kihagyva: {e['regi']}")
            continue
        shutil.move(str(a), str(b))
        n += 1
        if "md_uj" in e and (ROOT / e["md_uj"]).exists():
            mr = ROOT / e["md_regi"]
            mr.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(ROOT / e["md_uj"]), str(mr))
            j = (ROOT / e["md_uj"]).with_suffix(".json")
            if j.exists():
                shutil.move(str(j), str(mr.with_suffix(".json")))
    mf.rename(DATA / f"athelyezes.visszaallitva-{datetime.now():%Y%m%dT%H%M%S}.json")
    prune_empty(ROOT / "archive" / "vallalkozas-iratok")
    print(f"Visszaállítva: {n} fájl az input/{src.name}/ alá.")



MEMORY = ROOT / ".claude" / "memory"
CAT = [("jogi", "Jogállás és a vállalkozás időrendje"), ("adozas", "Adózás (adózási mód, ÁFA, bevallások)"),
       ("helyi-ado-kamara", "Helyi adó és kamara"), ("szerzodes", "Szerződések, ügyfelek, szolgáltatók"), ("egyeb", "Egyéb")]
LABEL = {"jogallas": "Jogállás", "adozasi_mod": "Adózási mód", "tevekenyseg": "Főtevékenység", "koltseghanyad": "Költséghányad",
         "tb_statusz": "TB-státusz", "min_alap_tipus": "Minimális járulékalap típusa", "vallalkozas_kezdete": "A vállalkozás folytatásának első napja",
         "ipa_telepules": "Iparűzési adó illetékességi helye (települési önkormányzat)"}
EXTRA_ALAP = lambda cfg: [  # noqa: E731
    ("Kamarai hozzájárulás", ("köteles, " + str(cfg.get("kamara_hozzajarulas_ft")) + " Ft/év, határidő " + str(cfg.get("kamara_hatarido")) + (", befizetés igazolva" if cfg.get("kamara_befizetes_igazolva") else ", befizetés NEM igazolt")) if cfg.get("kamara_koteles") else ("nem köteles" if cfg.get("kamara_koteles") is False else None)),
    ("Adó- és járulékkedvezmények", None if cfg.get("kedvezmenyek") is None else ("nincs" if cfg["kedvezmenyek"].get("nincs") else ", ".join(k for k, v in cfg["kedvezmenyek"].items() if v and k != "nincs"))),
]


def write_memory(cfg, tenyek, nyitott):
    """A vállalkozói profil a repó memóriájába (.claude/memory/): adózási és jogi szempontból fontos, forrással igazolt adatok.
    Generált fájl; személyes azonosítót (adószám, TAJ, cím, bankszámla) nem tartalmaz."""
    L = ["---", "name: vallalkozasi-profil",
         "description: Az átalányadózó egyéni vállalkozó adózási és jogi szempontból fontos, forrással igazolt adatai (jogállás, adózási mód, ÁFA, szünetelés, kamara, nyitott pontok); a vallalkozas-dokumentumok skill generálja",
         "metadata:", "  type: project", "---", "",
         "# Vállalkozói profil (generált, kézzel ne szerkeszd)", "",
         f"Generálta a `vallalkozas-dokumentumok` skill (`--profil`), {datetime.now():%Y-%m-%d %H:%M}. Forrás: `config/vallalkozas.json` és `data/vallalkozas/profil-tenyek.json`; a részletes profil: `data/vallalkozas/profil.md`. "
         "Személyes azonosítót (adószám, TAJ, cím, bankszámla) nem tartalmaz.", "",
         f"**Igazolt tények száma: {len(tenyek)}**", "", "## Alapbeállítások", ""]
    cfg = dict(cfg)
    if cfg.get("koltseghanyad") is None:  # a költséghányad az év szabályfájljából jön (évente változik), nem a vallalkozas.json-ból
        try:
            cfg["koltseghanyad"] = json.loads(konfig.szabalyok_ut(cfg.get("ev") or datetime.now().year).read_text(encoding="utf-8")).get("koltseghanyad")
        except (SystemExit, OSError, ValueError):
            pass
    for k, lab in LABEL.items():
        if cfg.get(k) is None:
            continue
        v = cfg[k]
        if k == "min_alap_tipus" and cfg.get("min_alap_tipus_megerositve") is False:
            v = f"{v} (NEM megerősített)"
        L.append(f"- **{lab}:** {v}")
    for lab, v in EXTRA_ALAP(cfg):
        if v:
            L.append(f"- **{lab}:** {v}")
    for key, title in CAT:
        if key == "szerzodes":
            # ügyfelek, szolgáltatók, könyvelő NEVE nem kerül a memóriába (adatkezeles.md 9.): csak a data/vallalkozas/profil.md-ben van
            n = sum(1 for t in tenyek if t.get("kategoria", "egyeb") == key)
            if n:
                L += ["", f"## {title}", "", f"- {n} igazolt tény (nevek nélkül; részletek: `data/vallalkozas/profil.md`)."]
            continue
        items = [t for t in tenyek if t.get("kategoria", "egyeb") == key]
        if not items:
            continue
        L += ["", f"## {title}", ""]
        for t in sorted(items, key=lambda x: x.get("datum") or "9999"):
            d = (t.get("datum") or "dátum nélkül").replace("-", ".")
            L.append(f"- **{d}** – {t['allitas']} _({t.get('ellenorzes', '?')})_")
    if nyitott:
        L += ["", "## Nyitott, nem ellenőrzött pontok", ""] + [f"- {x}" for x in nyitott]
    L += ["", "Kapcsolódó szabályok: `.claude/rules/atalanyado.md`, `jarulek-szocho.md`, `bevetel-nyilvantartas.md`, `hataridok.md`.", ""]
    MEMORY.mkdir(parents=True, exist_ok=True)
    (MEMORY / "vallalkozasi-profil.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    idx = MEMORY / "MEMORY.md"
    line = "- [Vállalkozói profil](vallalkozasi-profil.md) — adózási és jogi szempontból fontos, forrással igazolt adatok (generált)"
    lines = idx.read_text(encoding="utf-8").splitlines() if idx.exists() else []
    lines = [x for x in lines if not x.startswith("- [Vállalkozói profil]")] + [line]
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_profil(elfogad=False):
    hiany = kerdesek_hianyoznak()
    if hiany:
        print("❓ A profilkészítéshez még kérdezni kell a felhasználót (AskUserQuestion), majd rögzíteni a választ:")
        for h in hiany:
            print("   - " + h)
    if not elfogad:
        rc = cmd_billingo()
        if rc == 4:
            sys.exit(4)
    cfg = json.loads((konfig.vallalkozas_ut()).read_text(encoding="utf-8"))
    facts_p = DATA / "profil-tenyek.json"
    facts = json.loads(facts_p.read_text(encoding="utf-8"))["tenyek"] if facts_p.exists() else []
    man = DATA / "athelyezes.json"
    docs = json.loads(man.read_text(encoding="utf-8"))["tetelek"] if man.exists() else []
    cnt = Counter(e["uj"].split("/")[2] for e in docs) if docs else Counter()
    # a tényeknek forrása kell legyen, és a forrásfájl létezzen: különben nem kerül a profilba "ellenőrzött"-ként
    checked, unchecked = [], []
    for f in facts:
        ok = f.get("forras") and all((ROOT / s).exists() for s in f["forras"])
        (checked if ok else unchecked).append(f)
    prof = {"keszult": datetime.now().isoformat(timespec="seconds"),
            "beallitasok": {k: v for k, v in cfg.items() if not k.startswith("_")},
            "tenyek": sorted(checked, key=lambda f: f.get("datum") or "9999"),
            "forras_nelkuli_tenyek": unchecked,
            "iratok_szama_temakoronkent": dict(sorted(cnt.items())),
            "megjegyzes": "Személyes azonosítót (adószám, adóazonosító, cím, bankszámla) szándékosan nem tartalmaz."}
    (DATA / "profil.json").write_text(json.dumps(prof, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# Vállalkozói profil", "", f"Készült: {prof['keszult'][:16].replace('T', ' ')} · forrás: config/vallalkozas.json, data/vallalkozas/profil-tenyek.json",
          "A profil nem tartalmaz adószámot, adóazonosítót, címet vagy bankszámlát. Minden tény mellett ott a forrásdokumentum.", "", "## Beállítások (config/vallalkozas.json)", ""]
    for k, v in prof["beallitasok"].items():
        md.append(f"- **{k}**: {v}")
    md += ["", "## Időrend és tények (forrásokkal)", ""]
    for f in prof["tenyek"]:
        md.append(f"- **{f.get('datum') or 'dátum nélkül'}** – {f['allitas']} _({f.get('ellenorzes', '?')}; forrás: " + ", ".join(f"`{s}`" for s in f["forras"]) + ")_")
    if not prof["tenyek"]:
        md.append("_Még nincs forrással igazolt tény; a `data/vallalkozas/profil-tenyek.json` kitöltése után futtasd újra a `--profil` parancsot._")
    if unchecked:
        md += ["", "## Forrás nélküli vagy hiányzó forrású tények (nem ellenőrzött)", ""] + [f"- {f.get('allitas')}" for f in unchecked]
    md += ["", "## Iratok témakörönként (archive/vallalkozas-iratok/)", ""] + [f"- `{k}`: {v} fájl" for k, v in sorted(cnt.items())]
    (DATA / "profil.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    nyitott = json.loads(facts_p.read_text(encoding="utf-8")).get("nyitott", []) if facts_p.exists() else []
    write_memory(cfg, prof["tenyek"], nyitott)
    print(f"Profil: {len(checked)} igazolt tény, {len(unchecked)} forrás nélküli -> data/vallalkozas/profil.md, profil.json")
    print("Memória: .claude/memory/vallalkozasi-profil.md (a gate ezt várja az adoellenorzes futtatásához)")


def billingo_get(path, key):
    import urllib.request
    rq = urllib.request.Request("https://api.billingo.hu/v3" + path, headers={"X-API-KEY": key, "Accept": "application/json"})
    return json.load(urllib.request.urlopen(rq, timeout=25))


def cmd_billingo():
    """A vállalkozás adatai a Billingóból (csak olvasás) és összevetésük az iratokból kiolvasottakkal. Eltérésnél 4-es kilépési kód:
    a felhasználót kérdezni kell (a --profil addig nem fut le). Személyes adat (adószám, név, cím, számlaszám) nem kerül a kimenetre."""
    import re
    key = None
    envp = ROOT / ".env"
    if envp.exists():
        for l in envp.read_text(encoding="utf-8").splitlines():
            if l.startswith("BILLING_API_KEY"):
                key = l.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        print("❓ Billingo-ellenőrzés kimarad: nincs BILLING_API_KEY a .env-ben.")
        return 1
    try:
        org = billingo_get("/organization", key)
        inv = None
        for f in sorted((ROOT / "data" / "szamlak").glob("szamlak_*.json")):
            for x in json.loads(f.read_text(encoding="utf-8")):
                if inv is None or (x.get("invoice_date") or "") > (inv.get("invoice_date") or ""):
                    inv = x
        if inv is None:
            print("❓ Billingo-ellenőrzés kimarad: nincs letöltött számla (futtasd a szamlak skillt), a cégadatok a számlán szerepelnek.")
            return 1
        o = billingo_get(f"/documents/{inv['id']}", key)["organization"]
        banks = billingo_get("/bank-accounts", key)
    except Exception as e:
        print(f"❓ A Billingo nem érhető el ({type(e).__name__}); az ellenőrzés kimarad.")
        return 1
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "billingo-szervezet.json").write_text(json.dumps({"lekerdezve": datetime.now().isoformat(timespec="seconds"), "organization": org,
        "szamla_szervezet": o, "szamla_datuma": inv.get("invoice_date"), "bankszamlak_szama": len(banks.get("data", banks))}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = DATA / "iratok-md"
    corpus = chr(10).join(f.read_text(encoding="utf-8", errors="ignore") for f in md.rglob("*.md")) if md.exists() else ""
    low = corpus.casefold()
    eltérések, rows = [], []

    def chk(nev, ok):
        rows.append(("✅ egyezik" if ok else "🔴 ELTÉRÉS / nincs az iratokban") + f": {nev}")
        if not ok:
            eltérések.append(nev)

    d = re.sub(r"\D", "", o.get("tax_number") or "")
    if len(d) >= 11:
        chk("adószám (a Billingo számláján) szerepel az iratokban", bool(re.search(d[:8] + r"[-\s]?" + d[8] + r"[-\s]?" + d[9:11], corpus)))
        chk("a Billingo /organization adószáma azonos a számlán lévővel", re.sub(r"\D", "", org.get("tax_code") or "")[:8] == d[:8])
    ev = (o.get("ev_number") or "").strip()
    if ev:
        chk("egyéni vállalkozói nyilvántartási szám szerepel az iratokban", ev.casefold() in low)
    name = (o.get("name") or "").casefold()
    if name:
        chk("a vállalkozó neve szerepel az iratokban", all(t in low for t in name.split()))
    ad = o.get("address") or {}
    if ad.get("city"):
        chk("a Billingóban megadott székhely települése (irányítószámmal) szerepel az iratokban", f"{ad.get('post_code', '')} {ad['city']}".casefold() in low)
    if o.get("eu_tax_number"):
        chk("közösségi adószám szerepel az iratokban", re.sub(r"\s", "", o["eu_tax_number"]).casefold() in re.sub(r"\s", "", low))
    # ÁFA-státusz: a dokumentumokból igazolt tényekkel (alanyi adómentesség)
    facts = json.loads((DATA / "profil-tenyek.json").read_text(encoding="utf-8"))["tenyek"] if (DATA / "profil-tenyek.json").exists() else []
    aam = [f for f in facts if "alanyi adómentes" in f.get("allitas", "").casefold()]
    if aam:
        chk(f"ÁFA-státusz: az iratok szerint alanyi adómentes ({len(aam)} tény), a Billingo is alanyi adómentesként tartja nyilván (small_taxpayer={o.get('small_taxpayer')})", bool(o.get("small_taxpayer")))
    try:
        sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
        import azonosito
        azonosito.frissit()
    except Exception as e:  # az azonosító hiánya nem állítja meg az egyeztetést, de a többi skill megáll nélküle
        print(f"ℹ️ A vállalkozás azonosítója nem készült el: {e}")
    print("=== Billingo vs. iratok (az értékeket nem írom ki; részletek: data/vallalkozas/billingo-szervezet.json)")
    for r in rows:
        print("  " + r)
    print(f"  ℹ️ Billingo: pénzforgalmi elszámolás (cash_settled) = {o.get('cash_settled')}; közösségi adószám megadva: {bool(o.get('eu_tax_number'))}")
    if eltérések:
        print(f"{chr(10)}🔴 ÁLLJ MEG: {len(eltérések)} eltérés a Billingo és az iratok között. Kérdezd meg a felhasználót, melyik a helyes "
              "(javítandó a Billingo, vagy hiányzik/elavult az irat); a profil készítése addig nem folytatódik "
              "(tudomásul vétel után: --billingo-eltereseket-elfogadom).")
        return 4
    return 0


def cmd_ipa_javaslat():
    """A helyi iparűzési adó (IPA) illetékességi településének jelöltjei a dokumentumokból: irányítószám + település előfordulások
    (csak a településnév kerül ki, utca/házszám nem) és a helyi-adok mappák nevei. A végleges választ a felhasználó adja (ipa-beallit)."""
    import re
    from collections import Counter
    cnt = Counter()
    md = DATA / "iratok-md"
    for f in md.rglob("*.md") if md.exists() else []:
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r"[1-9]\d{3} ([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]+(?:-[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]+)?)", t):
            cnt[m.group(1)] += 1
    helyi = ROOT / "archive" / "vallalkozas-iratok" / "04-adozas" / "helyi-adok"
    mappak = sorted(d.name for d in helyi.iterdir() if d.is_dir()) if helyi.exists() else []
    print("Az IPA illetékességi helye (székhely/telephely szerinti önkormányzat) a dokumentumokból nem állapítható meg biztosan.")
    print("Jelöltek (irányítószám utáni településnév, előfordulás a Markdown-okban; a legtöbbször előfordulók között lehet a vállalkozás székhelye, de ez NEM bizonyíték):")
    for n, c in cnt.most_common(6):
        print(f"  - {n}: {c}")
    print("Helyi adó mappák az iratok között: " + (", ".join(mappak) if mappak else "nincs"))
    print("KÉRDÉS A FELHASZNÁLÓNAK: a székhely települése az iparűzési adó illetékességi helye? Van telephely más településen? (egyéb válasz is megadható)")
    print('Rögzítés: ... dokumentumok.py --ipa-beallit "<település>"   (több telephelyhez: --ipa-telephely "<település>" többször)')


def cmd_kamara_kedvezmeny(kamara, osszeg, kedvezmeny):
    """A felhasználó válaszainak rögzítése: kamarai hozzájárulás és kedvezmények (a profilkészítéskor ezekre kérdezni kell)."""
    cfgp = konfig.vallalkozas_ut()
    c = json.loads(cfgp.read_text(encoding="utf-8"))
    ma = f"{datetime.now():%Y-%m-%d}"
    if kamara:
        c["kamara_koteles"] = {"igen": True, "nem": False}.get(kamara)
        if kamara == "igen":
            c["kamara_hozzajarulas_ft"] = osszeg if osszeg is not None else c.get("kamara_hozzajarulas_ft", 5000)
            c.setdefault("kamara_hatarido", f"{c.get('ev', datetime.now().year)}-03-31")
            c.setdefault("kamara_befizetes_igazolva", False)
        c["_kamara_forras"] = (f"A felhasználó megadta ({ma}). Összeg és határidő: 1999. évi CXXI. törvény 34/A. § (2)-(3) "
                               "(torvenytar/docs/kamarai-tv/): évi 5000 Ft, a tárgyév március 31-ig; mentes, aki a teljes naptári évben szünetel és ezt bejelenti.")
    if kedvezmeny:
        kulcsok = ("csaladi", "szemelyi", "elso_hazasok", "huszonot_ev_alatti", "anyak")
        kd = {"nincs": kedvezmeny == ["nincs"]}
        for k in kulcsok:
            kd[k] = True if k in kedvezmeny else (False if kd["nincs"] else None)
        c["kedvezmenyek"] = kd
        c["_kedvezmenyek_forras"] = f"A felhasználó megadta ({ma})."
    cfgp.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rögzítve: kamarai hozzájárulás köteles: {c.get('kamara_koteles')}; kedvezmények: {c.get('kedvezmenyek')}")


def kerdesek_hianyoznak():
    """A profilkészítéskor kötelező kérdések, amelyekre még nincs válasz. Üres lista = minden megválaszolt."""
    c = json.loads((konfig.vallalkozas_ut()).read_text(encoding="utf-8"))
    h = []
    if c.get("kamara_koteles") is None:
        h.append("kamarai hozzájárulás: köteles-e a vállalkozó? (--kamara igen|nem)")
    if c.get("kedvezmenyek") is None:
        h.append("adó- és járulékkedvezmények: melyikre jogosult? (--kedvezmeny nincs | csaladi szemelyi elso_hazasok huszonot_ev_alatti anyak)")
    if not c.get("ipa_telepules"):
        h.append("iparűzési adó illetékességi helye (--ipa-beallit \"<település>\")")
    return h


def cmd_ipa_beallit(telepules, telephelyek):
    cfgp = konfig.vallalkozas_ut()
    c = json.loads(cfgp.read_text(encoding="utf-8"))
    c["ipa_telepules"] = telepules
    c["_ipa_telepules_forras"] = f"A felhasználó megadta ({datetime.now():%Y-%m-%d}); az IPA illetékességi helye (székhely szerinti önkormányzat)."
    c["ipa_telephelyek"] = telephelyek
    c.setdefault("ipa_adozasi_mod", None)
    cfgp.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"IPA illetékességi hely: {telepules}; további telephelyek: {', '.join(telephelyek) if telephelyek else 'nincs'}. "
          "Következő lépés: helyi-ipa skill (az önkormányzati szabályok beszerzése).")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Vállalkozói iratok feldolgozása és rendezése.")
    for k, h in (("leltar", "fájlleltár + duplikátumok"), ("konvertal", "PDF -> Markdown"), ("terv", "besorolási terv (nem módosít)"),
                 ("vegrehajt", "áthelyezés a terv szerint"), ("md_rendez", "a Markdown-ok utólagos áthelyezése a napló szerint"),
                 ("visszaallit", "az áthelyezés visszavonása"), ("profil", "vállalkozói profil")):
        ap.add_argument("--" + k.replace("_", "-"), action="store_true", help=h)
    ap.add_argument("--ipa-javaslat", action="store_true", help="az IPA illetékességi hely jelöltjei a dokumentumokból")
    ap.add_argument("--ipa-beallit", metavar="TELEPÜLÉS", help="az IPA illetékességi helyének rögzítése (a felhasználó válasza)")
    ap.add_argument("--ipa-telephely", action="append", default=[], metavar="TELEPÜLÉS", help="további telephely (ismételhető)")
    ap.add_argument("--kamara", choices=["igen", "nem", "nem-tudom"], help="köteles-e kamarai hozzájárulást fizetni (a profilkészítéskor kérdezd meg)")
    ap.add_argument("--kamara-osszeg", type=int, help="a kamarai hozzájárulás összege Ft-ban (alapértelmezés: 5000, 1999. évi CXXI. tv. 34/A. § (2))")
    ap.add_argument("--kedvezmeny", nargs="+", metavar="KEDVEZMÉNY",
                    help="nincs | csaladi szemelyi elso_hazasok huszonot_ev_alatti anyak (a profilkészítéskor kérdezd meg)")
    ap.add_argument("--billingo", action="store_true", help="a cégadatok lekérése a Billingóból és összevetés az iratokkal (eltérésnél megáll)")
    ap.add_argument("--billingo-eltereseket-elfogadom", action="store_true", help="a felhasználó tudomásul vette a Billingo-eltéréseket, a profil elkészülhet")
    a = ap.parse_args()
    if a.kamara or a.kedvezmeny:
        cmd_kamara_kedvezmeny(a.kamara, a.kamara_osszeg, a.kedvezmeny)
        return
    if a.billingo:
        sys.exit(cmd_billingo())
    if a.ipa_javaslat:
        cmd_ipa_javaslat(); return
    if a.ipa_beallit:
        cmd_ipa_beallit(a.ipa_beallit, a.ipa_telephely); return
    if a.profil:
        cmd_profil(a.billingo_eltereseket_elfogadom); return
    src = find_input() if not a.visszaallit else (find_input() if any(INPUT_BASE.iterdir()) else INPUT_BASE / "vallalkozas-adatok")
    for flag, fn in (("leltar", cmd_leltar), ("konvertal", cmd_konvertal), ("terv", cmd_terv), ("vegrehajt", cmd_vegrehajt),
                     ("md_rendez", cmd_md_rendez), ("visszaallit", cmd_visszaallit)):
        if getattr(a, flag):
            fn(src)
            return
    ap.print_help()


if __name__ == "__main__":
    main()

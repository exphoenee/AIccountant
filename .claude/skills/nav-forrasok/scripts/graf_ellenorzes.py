#!/usr/bin/env python3
"""A Graphify törvénytérkép INFERRED éleinek ellenőrzése a forrásszövegben (nincs LLM, nincs hálózat).

Minden INFERRED élnél megnézi, hogy a hivatkozó szakasz (vagy NAV-dokumentum) szövege KIFEJEZETTEN idézi-e a célt:
  - cél = szakasz (pl. szja_tv_47_par): azonos törvényen belül "47. §", más törvénynél "Rövidítés 47. §" (pl. "Tbj. 43. §") kell a szövegben;
  - cél = törvény (pl. anya2_tv): a törvény rövidítése vagy száma ("2025. évi XIV.") kell a szövegben;
  - cél = melléklet: "N. számú melléklet" (más törvénynél a rövidítéssel).
Ha van ilyen szövegrészlet, az él EXTRACTED-re léptethető elő (a bizonyíték és az eredeti jelzés az élen marad). Ha nincs, az él INFERRED marad.
Ha a szöveg a törvényt csak NEVÉVEL említi (pl. "két gyermeket nevelő anyák kedvezménye"), az él INFERRED marad, de `nev_alapjan` jelzést kap
(az alias-tábla pontosítja a célt, de nem teszi kifejezetté a hivatkozást). Fogalmi (fogalom_*) élt a script nem léptet elő: az értelmezés.

Használat (a repó gyökeréből; standard könyvtár, `-I`):
    python -I .claude/skills/nav-forrasok/scripts/graf_ellenorzes.py            # ellenőrzés + graph.json frissítése + jelentés
    python -I .claude/skills/nav-forrasok/scripts/graf_ellenorzes.py --szaraz   # csak kiírja, nem módosít
Bemenet: data/graphify/torvenyek/ (korpusz) és graphify-out/graph.json. Kimenet: graph.json (confidence frissítve), graphify-out/inferred_ellenorzes.json.
A HTML-t és a GRAPH_REPORT.md összegző sorát a script maga frissíti (a HTML-hez a Graphify venv Pythonja kell: .claude/skills/graphify/.venv).
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
KORPUSZ = ROOT / "data" / "graphify" / "torvenyek"
OUT = KORPUSZ / "graphify-out"
GRAPH_DIR = ROOT / "torvenytar" / "graph"  # a közzétett (verziózott) gráf

# törvény-azonosító -> (fájlnév-előtagok, rövidítés/szám minta, név-alias minta): a references/torvenyek-aliasok.json-ból (új törvényt ott kell felvenni)
def _betolt_torvenyek():
    p = Path(__file__).resolve().parents[1] / "references" / "torvenyek-aliasok.json"
    d = json.loads(p.read_text(encoding="utf-8"))["torvenyek"]
    return {k: (v["fajl_elotag"], v["rovidites"], v["nev_alias"]) for k, v in d.items()}


TORVENYEK = _betolt_torvenyek()
RE_FEJ = re.compile(r"^(\d+(?:/[A-Z])?)\.\s?§")
_cache = {}


def szoveg(fajl: Path) -> list:
    if fajl not in _cache:
        _cache[fajl] = fajl.read_text(encoding="utf-8", errors="replace").splitlines()
    return _cache[fajl]


def torveny_fajlok(tv):
    return sorted(p for p in KORPUSZ.iterdir() if p.is_file() and any(p.name.startswith(e) for e in TORVENYEK[tv][0]))


def szakasz_szoveg(tv, szam):
    """A törvény adott szakaszának szövege a korpusz fájljaiból (a fejléctől a következő szakaszfejlécig)."""
    for f in torveny_fajlok(tv):
        sorok = szoveg(f)
        for i, l in enumerate(sorok):
            m = RE_FEJ.match(l)
            if m and m.group(1) == szam:
                j = i + 1
                while j < len(sorok) and not RE_FEJ.match(sorok[j]):
                    j += 1
                return "\n".join(sorok[i:j])
    return None


def csomopont_info(nid):
    """(típus, törvény, szám): típus: 'par' | 'melleklet' | 'nav' | 'torveny' | 'egyeb'."""
    if nid in TORVENYEK:
        return "torveny", nid, None
    if nid.startswith("nav_"):
        return "nav", None, None
    m = re.match(r"^(" + "|".join(sorted(TORVENYEK, key=len, reverse=True)) + r")_(\d+(?:_[a-z])?)_(par|melleklet)$", nid)
    if m:
        szam = m.group(2).replace("_", "/").upper() if "_" in m.group(2) else m.group(2)
        return ("par" if m.group(3) == "par" else "melleklet"), m.group(1), szam
    return "egyeb", None, None


def hivatkozo_szoveg(nid, node):
    t, tv, szam = csomopont_info(nid)
    if t == "par":
        return szakasz_szoveg(tv, szam)
    if t == "nav":
        f = KORPUSZ / (node.get("source_file") or "")
        if f.is_file():
            return "\n".join(szoveg(f))
    return None


def bizonyitek(szov, hiv_tv, cel_id):
    """(eredmeny, részlet): 'kifejezett' | 'nev_alapjan' | 'nincs' | 'nem_ellenorizheto'."""
    t, tv, szam = csomopont_info(cel_id)
    if t == "egyeb":
        return "nem_ellenorizheto", "fogalmi kapcsolat: az értelmezést a script nem igazolja"
    abbr = TORVENYEK[tv][1] if tv else None
    if t == "par":
        n = re.escape(szam)
        pat = rf"(?<![\d/]){n}\.\s?§" if tv == hiv_tv else rf"(?:{abbr})\W{{0,15}}{n}\.\s?§"
    elif t == "melleklet":
        n = re.escape(szam)
        pat = rf"(?<![\d/]){n}\.\s(?:számú\s)?melléklet" if tv == hiv_tv else rf"(?:{abbr})\W{{0,15}}{n}\.\s(?:számú\s)?melléklet"
    elif t == "torveny":
        if tv == hiv_tv:
            return "nem_ellenorizheto", "önhivatkozás"
        pat = rf"(?:{abbr})"
    else:  # nav célpont
        return "nem_ellenorizheto", "NAV-dokumentum a cél"
    # a fejlécsor (a szakasz saját száma) nem bizonyíték: az első sort kihagyjuk
    torzs = "\n".join(szov.splitlines()[1:]) if szov.count("\n") else szov
    m = re.search(pat, torzs)
    if m:
        a, b = max(0, m.start() - 40), min(len(torzs), m.end() + 40)
        return "kifejezett", re.sub(r"\s+", " ", torzs[a:b]).strip()
    if t == "torveny" and re.search(TORVENYEK[tv][2], torzs, re.I):
        return "nev_alapjan", "a törvényt a szöveg csak nevével említi, száma/rövidítése nélkül"
    return "nincs", "a szövegben nincs kifejezett idézet"


def publikal(statisztika=None):
    """A kész gráf közzététele a torvenytar/graph/ mappába (verziózott): graph.json, graph.html, GRAPH_REPORT.md, inferred_ellenorzes.json,
    korpusz-szabalyok.md, forras-terkep.json (a korpusz-fájlok -> torvenytar/docs forrás-megfeleltetés) és egy README.md.
    A munkamappa (data/graphify/, nem verziózott) gyorsítótárát, alügynök-fájljait és a .graphify_* segédfájlokat nem másolja.
    A helyi (abszolút) elérési utakat a szövegekből kiveszi: a gráf csak nyilvános jogszabályszöveg és relatív útvonalak."""
    import shutil
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    gyoker = str(ROOT).replace("\\", "/")
    gyoker_bs = str(ROOT)
    kopi = [(OUT / "graph.json", "graph.json"), (OUT / "graph.html", "graph.html"), (OUT / "GRAPH_REPORT.md", "GRAPH_REPORT.md"),
            (OUT / "inferred_ellenorzes.json", "inferred_ellenorzes.json"), (OUT / ".graphify_corpus_rules.md", "korpusz-szabalyok.md"),
            (KORPUSZ.parent / "torvenyek_reszek.json", "forras-terkep.json")]
    db = 0
    for src, nev in kopi:
        if not src.exists():
            print(f"FIGYELEM: nincs {src.relative_to(ROOT)}, kihagyva a közzétételből")
            continue
        szoveg = src.read_text(encoding="utf-8")
        for t in (gyoker_bs, gyoker, gyoker_bs.replace("\\", "\\\\")):
            szoveg = szoveg.replace(t, ".")
        (GRAPH_DIR / nev).write_text(szoveg, encoding="utf-8", newline="\n")
        db += 1
    gp = OUT / "graph.json"
    st = ""
    if gp.exists():
        g = json.loads(gp.read_text(encoding="utf-8"))
        el = g.get("links") or g.get("edges") or []
        from collections import Counter
        c = Counter(e.get("confidence") for e in el)
        st = (f"- Csomópont: {len(g['nodes'])}, él: {len(el)}; EXTRACTED {c['EXTRACTED']}, INFERRED {c['INFERRED']}, AMBIGUOUS {c['AMBIGUOUS']}.\n")
    readme = ("# Törvénytérkép (Graphify tudásgráf)\n\n"
              "Generált mappa: a `nav-forrasok` skill állítja elő (`graf_ellenorzes.py`), kézzel ne szerkeszd. A gráf a `torvenytar/docs/` hivatalos jogszabályszövegeiből és NAV-tájékoztatóiból készült; "
              "**személyes adatot nem tartalmaz** (csak nyilvános szöveg), ezért verziózott.\n\n"
              f"Utolsó közzététel: {datetime.now().isoformat(timespec='seconds')}\n{st}\n"
              "| Fájl | Tartalom |\n|---|---|\n"
              "| `graph.html` | interaktív gráf (böngészőben nyitható) |\n"
              "| `graph.json` | a nyers gráfadat (csomópontok, élek, közösségek) |\n"
              "| `GRAPH_REPORT.md` | a jelentés (központi csomópontok, meglepő kapcsolatok, kérdések) |\n"
              "| `inferred_ellenorzes.json` | az INFERRED élek szöveges ellenőrzésének eredménye |\n"
              "| `korpusz-szabalyok.md` | a kinyeréshez használt közös azonosító-szótár és alias-tábla |\n"
              "| `forras-terkep.json` | a gráf `source_file` mezőjében szereplő korpusz-fájlok megfeleltetése a `torvenytar/docs/` forrásfájloknak |\n\n"
              "## Hogyan olvasd\n"
              "- Az él **EXTRACTED**, ha a hivatkozó szakasz szövege kifejezetten idézi a célt; **INFERRED**, ha a kapcsolat értelmezés; **AMBIGUOUS**, ha bizonytalan. Az INFERRED/AMBIGUOUS élek nem tények: állítás előtt a hivatkozott szakaszt a `torvenytar/docs/` forrásszövegben kell elolvasni (`.claude/rules/nincs-becsles.md`).\n"
              "- A csomópont-azonosító: `<törvény>_<szakasz>_par` (pl. `szja_tv_29_a_par`), `fogalom_<név>`, `nav_<forrás>`. A törvények rövid nevei: `korpusz-szabalyok.md`.\n"
              "- A gráf a **törzsszöveget** fedi; a törvények mellékletei (`*.jogtar.txt`) nincsenek benne.\n"
              "- Frissítés: `python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --korpusz`, a Graphify futtatása, majd `--graf-ellenoriz`.\n")
    (GRAPH_DIR / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    print(f"Közzétéve: {GRAPH_DIR.relative_to(ROOT)} ({db} fájl + README.md)")


def hianyzo_torvenyek():
    """A gráfban hivatkozott, de a törvénytárban (alias-tábla + jegyzék) nem szereplő törvények: azok a csomópontok, amelyek azonosítója
    `<előtag>_<szakasz>_par` alakú, de az előtag nem ismert törvény. Ezek csonkok: a törvény szövegét be kell szerezni (forrasok.json + references/torvenyek-aliasok.json)."""
    from collections import Counter
    gp = OUT / "graph.json"
    if not gp.exists():
        sys.exit(f"HIBA: nincs {gp.relative_to(ROOT)}; előbb építsd fel a gráfot.")
    g = json.loads(gp.read_text(encoding="utf-8"))
    ismert = set(TORVENYEK)
    c, pelda, hivatk = Counter(), {}, Counter()
    for n in g["nodes"]:
        m = re.match(r"^([a-z0-9_]+?)_(\d+(?:_[a-z])?)_(par|melleklet)$", n["id"])
        if m and m.group(1) not in ismert:
            c[m.group(1)] += 1
            pelda.setdefault(m.group(1), n.get("label", n["id"]))
    for n in g["nodes"]:  # törvény-szintű csonkok: nincs szakasz-csomópontjuk, csak maga a törvény (pl. jovedeki_tv, tv_2025_xvi)
        i = n["id"]
        if i in ismert or i.startswith(("fogalom_", "nav_")):
            continue
        if re.match(r"^tv_[0-9]{4}_[a-z]+$", i) or i.endswith("_tv"):
            c.setdefault(i, 0)
            pelda.setdefault(i, n.get("label", i))
    for e in g.get("links") or g.get("edges") or []:
        for v in (e["source"], e["target"]):
            if v in c or any(v.startswith(k + "_") for k in c):
                for k in c:
                    if v == k or v.startswith(k + "_"):
                        hivatk[k] += 1
    print("A gráfban hivatkozott, de a törvénytárban nem szereplő törvények (csonk-csomópontok):")
    if not c:
        print("  nincs")
    for k, db in c.most_common():
        print(f"  {k}: {db} szakasz-csomópont, {hivatk[k]} él, példa: {pelda[k][:70]}")
    print("Felvétel: torvenytar/forrasok.json (id, tipus, mappa, nev, url) + references/torvenyek-aliasok.json; majd forras_letoltes.py.")


def _norm(t):
    """Kisbetű, ékezetek nélkül, a nem betű/szám karakterek szóközzé."""
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _tovek(fogalom_nev):
    """A fogalom tőszavai: a hosszabb (>= 4 betűs) szavak, ragozáshoz csonkolva (az utolsó 2 betű nélkül, legalább 4 betű)."""
    szavak = [w for w in _norm(fogalom_nev).split() if len(w) >= 4]
    return [w[: max(4, len(w) - 2)] for w in szavak]


def fogalom_szaraz():
    """SZÁRAZ elemzés (nem módosít): a fogalom <-> szakasz/NAV INFERRED éleken megnézi, hogy a fogalom kifejezése ténylegesen szerepel-e a szövegben.
    pontos: a fogalom teljes neve (normalizálva) szó szerint szerepel; toszavak: minden tőszava szerepel (nem feltétlenül egymás mellett); nincs: nem szerepel.
    Csak a `pontos` találat lenne ténymegállapítás ("a szöveg szerepelteti a fogalmat"), amit külön, szerepelteti relációval lehetne EXTRACTED-nek tárolni."""
    from collections import Counter
    gp = OUT / "graph.json"
    g = json.loads(gp.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in g["nodes"]}
    links = g.get("links") or g.get("edges")
    osszes = len(links)
    ext0 = sum(1 for e in links if e.get("confidence") == "EXTRACTED")
    inf0 = sum(1 for e in links if e.get("confidence") == "INFERRED")
    res = Counter()
    pelda = {"pontos": [], "toszavak": [], "nincs": []}
    pontos_db_tip = Counter()
    for e in links:
        if e.get("confidence") != "INFERRED":
            continue
        a, b = e["source"], e["target"]
        fa, fb = a.startswith("fogalom_"), b.startswith("fogalom_")
        if fa == fb:
            continue  # nem fogalom-szakasz/NAV él (fogalom-fogalom vagy fogalom nélküli): nem ennek a lépésnek a tárgya
        fog, masik = (a, b) if fa else (b, a)
        t, _, _ = csomopont_info(masik)
        if t not in ("par", "melleklet", "nav"):
            continue
        szov = hivatkozo_szoveg(masik, nodes.get(masik, {}))
        tip = "NAV" if t == "nav" else "szakasz"
        if not szov:
            res[(tip, "nincs szöveg")] += 1
            continue
        nev = nodes.get(fog, {}).get("label") or fog.replace("fogalom_", "").replace("_", " ")
        torzs = _norm(szov)
        teljes = _norm(nev)
        # a fogalom nevében zárójeles magyarázat is lehet: a zárójel előtti rész a fogalom neve
        alap = _norm(re.split(r"[(:]", nev)[0])
        if (alap and alap in torzs) or (teljes and teljes in torzs):
            k = "pontos"
        else:
            tv = _tovek(nev)
            k = "toszavak" if tv and all(re.search(r"\b" + re.escape(x), torzs) for x in tv) else "nincs"
        res[(tip, k)] += 1
        if k == "pontos":
            pontos_db_tip[tip] += 1
        if len(pelda[k]) < 6:
            pelda[k].append((fog, masik, nev[:50]))
    print("FOGALOM ↔ SZAKASZ/NAV INFERRED élek (szöveges kifejezés-keresés, SZÁRAZ FUTÁS: nem módosít)")
    for tip in ("szakasz", "NAV"):
        o = sum(v for (t, k), v in res.items() if t == tip)
        print(f"  {tip}: {o} él")
        for k in ("pontos", "toszavak", "nincs", "nincs szöveg"):
            v = res.get((tip, k), 0)
            if v:
                print(f"     {k:13} {v}")
    pontos = sum(v for (t, k), v in res.items() if k == "pontos")
    vizsgalt = sum(res.values())
    print(f"\nVizsgált élek: {vizsgalt}; ebből a fogalom pontos neve szó szerint szerepel a szövegben: {pontos} ({100 * pontos / max(1, vizsgalt):.0f}%)")
    print(f"Ha ezek `szerepelteti` (EXTRACTED) relációra váltanának: EXTRACTED {ext0} -> {ext0 + pontos} ({100 * (ext0 + pontos) / osszes:.1f}%), INFERRED {inf0} -> {inf0 - pontos} ({100 * (inf0 - pontos) / osszes:.1f}%)")
    print("(Az arány a relációváltás és az élszám változatlansága mellett számolt; ez nem a kész gráf eredménye.)")
    for k in ("pontos", "toszavak", "nincs"):
        print(f"\nPéldák ({k}):")
        for f_, m_, n_ in pelda[k]:
            print(f"   {f_}  <->  {m_}   [{n_}]")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="A Graphify INFERRED éleinek szöveges ellenőrzése.")
    ap.add_argument("--szaraz", action="store_true", help="nem módosít semmit")
    ap.add_argument("--fogalom-szaraz", action="store_true", help="SZÁRAZ elemzés: a fogalom-élek mennyire igazolhatók a szöveg kifejezéseivel (nem módosít)")
    ap.add_argument("--hianyzo", action="store_true", help="a gráfban hivatkozott, de a törvénytárban nem szereplő törvények listája")
    ap.add_argument("--publikal", action="store_true", help="csak a közzététel (torvenytar/graph/), ellenőrzés nélkül")
    a = ap.parse_args()
    if a.publikal:
        publikal()
        return
    if a.hianyzo:
        hianyzo_torvenyek()
        return
    if a.fogalom_szaraz:
        fogalom_szaraz()
        return
    gp = OUT / "graph.json"
    if not gp.exists():
        sys.exit(f"HIBA: nincs {gp.relative_to(ROOT)}; előbb építsd fel a gráfot (graphify skill).")
    g = json.loads(gp.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in g["nodes"]}
    links = g.get("links") or g.get("edges")
    eredmeny, jelentes = {"kifejezett": 0, "nev_alapjan": 0, "nincs": 0, "nem_ellenorizheto": 0}, []
    ma = datetime.now().isoformat(timespec="seconds")
    for e in links:
        if e.get("confidence") != "INFERRED":
            continue
        s, t = e["source"], e["target"]
        legjobb = ("nem_ellenorizheto", "nincs ellenőrizhető hivatkozó szöveg", None)
        rang = {"kifejezett": 3, "nev_alapjan": 2, "nincs": 1, "nem_ellenorizheto": 0}
        for hiv, cel in ((s, t), (t, s)):
            szov = hivatkozo_szoveg(hiv, nodes.get(hiv, {}))
            if not szov:
                continue
            _, hiv_tv, _ = csomopont_info(hiv)
            res, reszlet = bizonyitek(szov, hiv_tv, cel)
            if rang[res] > rang[legjobb[0]]:
                legjobb = (res, reszlet, (hiv, cel))
        res, reszlet, irany = legjobb
        eredmeny[res] += 1
        jelentes.append({"source": s, "target": t, "relation": e.get("relation"), "eredeti_confidence": e.get("confidence_score"), "eredmeny": res, "reszlet": reszlet,
                         "hivatkozo": irany[0] if irany else None})
        if a.szaraz:
            continue
        e["ellenorzes"] = {"modszer": "szoveg_hivatkozas", "eredmeny": res, "reszlet": reszlet, "datum": ma}
        if res == "kifejezett":
            e["confidence_eredeti"] = {"confidence": "INFERRED", "confidence_score": e.get("confidence_score")}
            e["confidence"], e["confidence_score"] = "EXTRACTED", 1.0
    os_ = sum(eredmeny.values())
    print(f"INFERRED élek: {os_}")
    print(f"  kifejezett hivatkozás a szövegben (EXTRACTED-re léptethető): {eredmeny['kifejezett']}")
    print(f"  csak névvel említett törvény (marad INFERRED, nev_alapjan): {eredmeny['nev_alapjan']}")
    print(f"  nincs kifejezett idézet (marad INFERRED): {eredmeny['nincs']}")
    print(f"  nem ellenőrizhető automatikusan (fogalmi/önhivatkozás/nincs szöveg; marad INFERRED): {eredmeny['nem_ellenorizheto']}")
    if a.szaraz:
        return
    (OUT / "inferred_ellenorzes.json").write_text(json.dumps({"ellenorzes": ma, "osszesen": os_, "eredmeny": eredmeny, "elek": jelentes}, ensure_ascii=False, indent=1), encoding="utf-8")
    gp.write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    # a jelentés összegző sora
    rp = OUT / "GRAPH_REPORT.md"
    if rp.exists():
        db = {k: sum(1 for e in links if e.get("confidence") == k) for k in ("EXTRACTED", "INFERRED", "AMBIGUOUS")}
        ossz = sum(db.values()) or 1
        sor = (f"- Extraction: {round(100 * db['EXTRACTED'] / ossz)}% EXTRACTED · {round(100 * db['INFERRED'] / ossz)}% INFERRED · {round(100 * db['AMBIGUOUS'] / ossz)}% AMBIGUOUS "
               f"(szöveges ellenőrzés után, {ma[:10]}: {eredmeny['kifejezett']} INFERRED él kifejezett hivatkozás miatt EXTRACTED-re lépett elő; részletek: inferred_ellenorzes.json)")
        szov = rp.read_text(encoding="utf-8")
        szov = re.sub(r"^- Extraction:.*$", sor.replace("\\", "\\\\"), szov, count=1, flags=re.M)
        rp.write_text(szov, encoding="utf-8")
    print(f"Frissítve: {gp.relative_to(ROOT)}, {(OUT / 'inferred_ellenorzes.json').relative_to(ROOT)}, GRAPH_REPORT.md")
    # HTML újragenerálása a Graphify venv Pythonjával
    py = OUT / ".graphify_python"
    if py.exists():
        kod = ("import json;from pathlib import Path;from networkx.readwrite import json_graph;from graphify.export import to_html\n"
               "g=json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8'))\n"
               "G=json_graph.node_link_graph(g, edges='links')\ncomm={}\n"
               "for n,d in G.nodes(data=True):\n    if d.get('community') is not None: comm.setdefault(int(d['community']),[]).append(n)\n"
               "lab={int(k):v for k,v in json.loads(Path('graphify-out/.graphify_labels.json').read_text(encoding='utf-8')).items()}\n"
               "print('graph.html:', to_html(G, comm, 'graphify-out/graph.html', community_labels=lab))\n")
        r = subprocess.run([py.read_text(encoding="utf-8").strip(), "-c", kod], cwd=str(KORPUSZ), capture_output=True, text=True, encoding="utf-8")
        print((r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else "graph.html: nem frissült")
    publikal()


if __name__ == "__main__":
    main()

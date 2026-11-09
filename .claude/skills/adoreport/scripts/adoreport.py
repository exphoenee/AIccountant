#!/usr/bin/env python3
"""HTML adóreport a feldolgozott adatokból (bevétel, kiadás, adó, határidők), Chart.js diagramokkal.

Használat:
    python -I .claude/skills/adoreport/scripts/adoreport.py [--ev 2026]

Bemenet (mind a data/ alól, lásd .claude/rules/adatkezeles.md):
    data/szamitas/adoszamitas_<év>.json   kötelező (skill: adoszamitas)
    data/szamitas/ellenorzes_<év>.json    ajánlott (skill: adoellenorzes) – határidők állapota
    data/nav-egyenleg/                    NAV befizetések (skill: adofizetes)
    data/szamlak/, data/kiadasok/         Billingo számlák és bejövő számlák (skill: szamlak)
Kimenet: tax-reports/adoreport_<év>.html  (egyetlen, önálló fájl)

A Python itt csak összegez és csoportosít a már kiszámolt adatokból (hónap, ügyfél, negyedév), adót nem számol újra, és
JSON-ban átadja a böngészőnek. A diagramokat a böngészőben a beágyazott Chart.js (assets/chart.umd.js, MIT, v4.4.7)
rajzolja; nincs külső betöltés (se CDN, se webfont), a riport offline és privát. A stílus az assets/report.css, a
viselkedés az assets/report.js. Arculat: design-taste-frontend skill (Frost and slate paletta, egy térköz-skála,
egy kártya-recept, hero-belépő, hover-réteg, világos/sötét mód).
Ami hiányzik vagy nem számolható, azt a report is kimondja (nincs becslés).
"""
import argparse
import html
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
ASSETS = Path(__file__).resolve().parents[1] / "assets"
NB = " "
MONTHS = ["jan", "feb", "márc", "ápr", "máj", "jún", "júl", "aug", "szept", "okt", "nov", "dec"]
ADONEM = {"103": "SZJA", "406": "TBJ", "258": "SZOCHO"}
E = html.escape

HEAD_JS = ('<script>(function(){var t=null;try{t=localStorage.getItem("adoreport-theme")}catch(e){}'
           'if(t!=="light"&&t!=="dark"){t=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}'
           'document.documentElement.setAttribute("data-theme",t)})()</script>')


def D(x):
    return Decimal(str(x))


def ft(n) -> str:
    return f"{int(round(float(n))):,}".replace(",", NB) + NB + "Ft"


def pct(x) -> str:
    return f"{float(x)*100:.2f}".replace(".", ",") + NB + "%"


def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def latest(dirp: Path, pattern: str):
    fs = sorted(dirp.glob(pattern), key=lambda p: p.stat().st_mtime)
    return fs[-1] if fs else None


# ---------------------------------------------------------------------- adatok

def collect(ev: int) -> dict:
    sdir = ROOT / "data" / "szamitas"
    if not (sdir / f"adoszamitas_{ev}.json").exists():
        sys.exit(f"HIBA: nincs data/szamitas/adoszamitas_{ev}.json. Futtasd az 'adoszamitas' vagy 'adoellenorzes' skillt.")
    sz = loadj(sdir / f"adoszamitas_{ev}.json")
    ell = loadj(sdir / f"ellenorzes_{ev}.json") if (sdir / f"ellenorzes_{ev}.json").exists() else None
    navp = latest(ROOT / "data" / "nav-egyenleg", "jelentes_*.json")
    rules = loadj(konfig.szabalyok_ut(ev))
    szf = ROOT / "data" / "szamlak" / sz["szamlak_forras"]
    kp = latest(ROOT / "data" / "kiadasok", "kiadasok_*.json")
    return {"sz": sz, "ell": ell, "rep": loadj(navp) if navp else None, "rules": rules,
            "docs": loadj(szf) if szf.exists() else [], "kiad": loadj(kp) if kp else None}


def monthly_income(sz, ev):
    m = [D(0)] * 12
    for s in sz["bevetelkent_szamolt_szamlak"]:
        d = date.fromisoformat(s["kifizetve"])
        if d.year == ev:
            m[d.month - 1] += D(s["netto_huf"])
    return m


def income_by_client(sz, docs):
    names = {d.get("invoice_number"): ((d.get("partner") or {}).get("name") or "ismeretlen") for d in docs}
    acc = {}
    for s in sz["bevetelkent_szamolt_szamlak"]:
        n = names.get(s["szamlaszam"], "ismeretlen")
        acc[n] = acc.get(n, D(0)) + D(s["netto_huf"])
    return sorted(acc.items(), key=lambda kv: -kv[1])


def expenses(kiad, ev):
    """Bejövő számlák. A mezőnevek NEM ellenőrzöttek (nincs rögzített tétel); amit nem talál, azt jelzi."""
    if not kiad:
        return {"allapot": "nincs_fajl"}
    if not kiad["tetelek"]:
        return {"allapot": "ures", "total": kiad.get("total_a_billingoban", 0), "lekerve": kiad["lekerve"]}
    date_keys = ["paid_at", "invoice_date", "fulfillment_date", "due_date"]
    amt_keys = ["total_gross_local", "gross_total_local", "total_gross", "gross_total", "amount"]
    months, unmapped = [D(0)] * 12, 0
    for t in kiad["tetelek"]:
        dk = next((k for k in date_keys if t.get(k)), None)
        ak = next((k for k in amt_keys if t.get(k) is not None), None)
        if not dk or not ak:
            unmapped += 1
            continue
        if str(t[dk])[:4] == str(ev):
            months[int(str(t[dk])[5:7]) - 1] += D(t[ak])
    return {"allapot": "van", "honapok": months, "nem_ertelmezett": unmapped, "lekerve": kiad["lekerve"]}


def dtable(summary, headers, rows):
    th = "".join(f"<th{' class=num' if i else ''}>{E(h)}</th>" for i, h in enumerate(headers))
    trs = "".join("<tr>" + "".join(f"<td{' class=num' if i else ''}>{E(str(c))}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return (f'<details class="dt"><summary>{E(summary)}</summary><div class="tablewrap"><table><thead><tr>{th}</tr></thead>'
            f"<tbody>{trs}</tbody></table></div></details>")


# ------------------------------------------------------------------------ HTML

def build(ev: int) -> str:
    d = collect(ev)
    sz, ell, rep, rules = d["sz"], d["ell"], d["rep"], d["rules"]
    today = date.fromisoformat(sz["szamitas_datuma"])
    kh = D(sz["beallitasok"]["koltseghanyad"])
    qs = sz["negyedevek"]
    last = qs[-1] if qs else None
    ytd = D(last["bevetel_gongyolt_pontos"]) if last else D(0)
    warns = list(sz["figyelmeztetesek"])
    miss = sz["hianyzo_beallitasok"]
    jar_ok = bool(qs) and qs[0]["tbj_eloleg"] is not None
    P = {"months": MONTHS}

    # ---- bevétel
    inc = monthly_income(sz, ev)
    upto = today.month if today.year == ev else 12
    cum, run = [], D(0)
    for i in range(12):
        run += inc[i]
        cum.append(float(run) if i < upto else None)
    thr = D(rules["adomentes_jovedelem_eves"]) / (D(1) - kh)
    P.update(income=[float(x) for x in inc], cum=cum, thr=float(thr),
             thr_label=f"Adómentes jövedelemhatár bevételben: {ft(thr)}",
             spark={"labels": MONTHS[:upto], "values": cum[:upto]})
    clients = income_by_client(sz, d["docs"])
    total_c = sum((v for _, v in clients), D(0)) or D(1)
    P["clients"] = [{"name": n, "value": float(v), "share": pct(v / total_c)} for n, v in clients]
    inc_table = dtable("Adatok táblázatban", ["Hónap", "Havi bevétel", "Göngyölt bevétel"],
                       [[MONTHS[i], ft(inc[i]), ft(cum[i]) if cum[i] is not None else "–"] for i in range(12)])
    prev = sz.get("elozo_evben_kiallitott_idei_kifizetes") or []
    if prev:
        prev_rows = "".join(f"<tr><td>{E(x['szamlaszam'])}</td><td>{E(x['kelt'])}</td><td>{E(x['kifizetve'])}</td><td class=\"num\">{ft(x['netto_huf'])}</td></tr>" for x in prev)
        prev_html = (f'<div class="card c12"><h3>{ev - 1}-ben kiállított, {ev}-ben kifizetett számlák ({ev}. évi bevétel)</h3>'
                     '<div class="tablewrap"><table><thead><tr><th>Számla</th><th>Kelt</th><th>Kifizetve</th><th class="num">Nettó (HUF)</th></tr></thead>'
                     f"<tbody>{prev_rows}</tbody></table></div>"
                     '<p class="muted small">A bevétel megszerzésének napja számít (Szja tv. 9. § (2) a): a pénz jóváírása), nem a számla kelte.</p></div>')
    else:
        prev_html = (f'<div class="card c12"><h3>{ev - 1}-ben kiállított, {ev}-ben kifizetett számlák</h3>'
                     f'<p class="muted">Nincs ilyen számla a lekért adatban. A számlaadat az {ev - 1}. év elejétől tart; ennél korábban kiállított számla nem látszik.</p></div>')
    client_list = "".join(
        f'<li><span class="sw" data-sw="{i}"></span><span class="nm">{E(c["name"])}</span>'
        f'<span class="vl">{ft(c["value"])}</span><span class="sh">{c["share"]}</span></li>'
        for i, c in enumerate(P["clients"]))

    bh = sz["bevetel_hatar"]
    gauges = [
        {"label": "Bevételi határ" + (" (időarányos)" if bh.get("idoaranyos") else ""), "ratio": float(D(bh["kihasznaltsag"])),
         "pct": pct(bh["kihasznaltsag"]),
         "detail": f"{ft(bh['bevetel'])} / {ft(bh['hatar'])}" + (
             f" · {bh['aktiv_napok']}/{bh['ev_napjai']} nap, éves határ: {ft(bh['eves_hatar'])}" if bh.get("idoaranyos") else "")},
        {"label": "Adómentes jövedelemkeret", "ratio": float(D(sz["adomentes_keret_kihasznaltsag"])),
         "pct": pct(sz["adomentes_keret_kihasznaltsag"]),
         "detail": f"{ft(last['jovedelem_gongyolt']) if last else 0} / {ft(rules['adomentes_jovedelem_eves'])}"
                   + (" · túllépve: efölött keletkezik szja-előleg-kötelezettség" if float(D(sz['adomentes_keret_kihasznaltsag'])) > 1 else "")}]
    P["gauges"] = [{"ratio": g["ratio"]} for g in gauges]
    gauge_html = "".join(
        f'<div class="gauge-wrap"><div class="gauge"><canvas id="ch-gauge{i}" role="img" aria-label="{E(g["label"])}: {E(g["pct"])}"></canvas>'
        f'<div class="mid">{g["pct"]}</div></div><p class="label">{E(g["label"])}</p><p class="muted small">{E(g["detail"])}</p></div>'
        for i, g in enumerate(gauges))

    # ---- kiadás
    ex = expenses(d["kiad"], ev)
    billingo_van = ex["allapot"] == "van"
    pdf_p = ROOT / "data" / "kiadasok" / "pdf_kiadasok.json"
    pdfi = loadj(pdf_p)["iratok"] if pdf_p.exists() else []
    pdf_sz = [x for x in pdfi if x["tipus"] == "szamla" and x["kelt"][:4] == str(ev)]
    if pdf_sz:
        pm = [D(0)] * 12
        for x in pdf_sz:
            pm[int(x["kelt"][5:7]) - 1] += D(x["brutto"])
        if billingo_van:
            ex["honapok"] = [a + b for a, b in zip(ex["honapok"], pm)]
        else:
            ex = {"allapot": "van", "honapok": pm, "nem_ertelmezett": 0, "lekerve": ""}
    deemed = ytd * kh
    exp_total = D(0)
    if ex["allapot"] == "van":
        P["exp"] = {"months": [float(x) for x in ex["honapok"]]}
        exp_total = sum(ex["honapok"], D(0))
        exp_html = (f'<div class="chartbox"><canvas id="ch-exp" role="img" aria-label="Havi kiadás {ev}-ben"></canvas></div>'
                    f'<p class="muted small">Forrás: ' + ("Billingo bejövő számlák, lekérve " + E(ex["lekerve"][:16].replace("T", " ")) + " (a mezőnevek értelmezése nem ellenőrzött)" if billingo_van else "") + (" és " if billingo_van and pdf_sz else "") + (f"{len(pdf_sz)} PDF számla (kiadasok-dokumentumok skill; a havi összeg a számla kelte szerinti bruttó)" if pdf_sz else "") + ".</p>")
        if ex["nem_ertelmezett"]:
            warns.append(f"{ex['nem_ertelmezett']} bejövő számlához nem találtam dátum- vagy összegmezőt; ezeket nem számoltam.")
        if billingo_van:
            warns.append("A bejövő számlák (spendings) mezőneveit nem tudtam ellenőrizni, mert nincs rögzített tétel; a diagram a talált dátum- és összegmezőkre épül.")
    else:
        why = ("A Billingo nem ad vissza bejövő számlát (a /spendings végpont 0 tételt jelent)." if ex["allapot"] == "ures"
               else "Nincs lekért kiadásfájl a data/kiadasok/ alatt.")
        exp_html = f'<div class="empty"><strong>Nincs megjeleníthető kiadás.</strong> {E(why)}</div>'
    exp_tbl_html = ""
    if pdfi:
        rows_k = []
        for x in sorted(pdfi, key=lambda x: x["kelt"], reverse=True):
            if x["tipus"] == "dijbekero":
                meg = "díjbekérő, nem kiadás" + (f"; a(z) {x['dijbekero_szamla']} számlához tartozik" if x.get("dijbekero_szamla") else "")
            else:
                meg = ("ÁFA-t tartalmaz; alanyi adómentesként az ÁFA nem levonható" if x.get("afa") else "áfa nélkül (AAM)") + ("; fizetve díjbekérő alapján, a fizetés napja nem igazolt" if x.get("penzugyi_teljesitest_nem_igenyel") else "")
            rows_k.append([x["kelt"], x["szallito"] or "?", x["sorszam"], ft(x["netto"] or 0), ft(x["afa"] or 0), ft(x["brutto"]), meg])
        th = "".join(f"<th{'' if i in (0, 1, 2, 6) else ' class=num'}>{E(h)}</th>" for i, h in enumerate(["Kelt", "Szállító", "Sorszám", "Nettó", "ÁFA", "Bruttó", "Megjegyzés"]))
        trs = "".join("<tr>" + "".join(f"<td{'' if i in (0, 1, 2, 6) else ' class=num'}>{E(str(c))}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows_k)
        exp_tbl_html = ('<h3>Bejövő számlák (PDF)</h3><div class="tablewrap"><table><thead><tr>' + th + "</tr></thead><tbody>" + trs + "</tbody></table></div>"
                     '<p class="muted small">Átalányadózónál a ténylegesen felmerült költség az adót nem csökkenti (a költséghányad az átalány); a kiadások tájékoztató jellegűek. Forrás: data/kiadasok/pdf_kiadasok.json.</p>')
    exp_card = ('<div class="card c12">' + exp_tbl_html + "</div>") if exp_tbl_html else ""
    P["deemed"] = {"deemed": float(deemed), "recorded": float(exp_total)}

    # ---- adó
    ql = [f"{q['negyedev']}. n.év" + (" (folyamatban)" if q["allapot"] == "folyamatban" else "") for q in qs]
    P["quarters"] = {"labels": ql, "szja": [q["szja_eloleg"] for q in qs],
                     "tbj": [q["tbj_eloleg"] for q in qs] if jar_ok else None,
                     "szocho": [q["szocho_eloleg"] for q in qs] if jar_ok else None}
    q_table = dtable("Adatok táblázatban", ["Negyedév", "SZJA előleg", "TBJ", "SZOCHO", "Határidő"],
                     [[ql[i], ft(q["szja_eloleg"]), ft(q["tbj_eloleg"]) if jar_ok else "nem számolható",
                       ft(q["szocho_eloleg"]) if jar_ok else "nem számolható", q["tb_hatarido"] or q["szja_hatarido"] or "–"]
                      for i, q in enumerate(qs)])
    paid = {k: 0 for k in ADONEM.values()}
    nav_rows, pay_month = [], {k: [0] * 12 for k in ADONEM.values()}
    if rep:
        for r in rep["adonemek"]:
            nm = ADONEM.get(r["kod"])
            if not nm:
                continue
            paid[nm] = r["befizetesek_osszesen"]
            nav_rows.append((nm, r))
            for b in r["befizetesek"]:
                if b["datum"][:4] == str(ev):
                    pay_month[nm][int(b["datum"][5:7]) - 1] += b["osszeg"]
    comp = {"SZJA": last["szja_gongyolt"] if last else 0,
            "TBJ": last["tbj_gongyolt"] if last and jar_ok else None,
            "SZOCHO": last["szocho_gongyolt"] if last and jar_ok else None}
    P["cmp"] = {"labels": [k if comp[k] is not None else f"{k} (nem számolható)" for k in ("SZJA", "TBJ", "SZOCHO")],
                "computed": [comp[k] for k in ("SZJA", "TBJ", "SZOCHO")], "paid": [paid[k] for k in ("SZJA", "TBJ", "SZOCHO")]}
    P["pay"] = {"series": [{"name": k, "values": pay_month[k]} for k in ("SZJA", "TBJ", "SZOCHO")]}
    if miss:
        warns.append("A tb-járulék és szocho NEM számolható; hiányzó beállítás a config/vallalkozas.json-ban: " + ", ".join(miss) + ".")

    # ---- mutatók
    nxt = (ell or {}).get("kovetkezo_kotelezettseg")
    findings = (ell or {}).get("talalatok", [])
    tb_total = (last["tbj_gongyolt"] + last["szocho_gongyolt"]) if last and jar_ok else None
    kpis = [
        ("Számított SZJA (göngyölt)", ft(last["szja_gongyolt"]) if last else "–", "az adómentes rész után, 15%"),
        ("Átalányos jövedelem", ft(last["jovedelem_gongyolt"]) if last else "–", f"bevétel × (1 − {pct(kh)})"),
        ("Számított TBJ + SZOCHO", ft(tb_total) if tb_total is not None else "Nem számolható",
         "göngyölt" if tb_total is not None else "hiányzó beállítás: " + ", ".join(miss)),
        ("NAV adószámlán befizetve", ft(rep["osszes_befizetes"]) if rep else "Nincs adat",
         f"NAV lekérdezés: {rep['lekerdezes'].replace('T',' ')[:16]}" if rep else "nincs feldolgozott kivonat"),
        ("Következő határidő", (nxt["hatarido"].replace("-", ".") + ".") if nxt else "–",
         (f"SZJA még fedezetlen: {ft(nxt['szja_fedezetlen'])}" if nxt else "nincs adat")),
    ]
    tiles = (f'<div class="tile lg c6" data-enter style="--i:5"><span class="label">Bevétel (kifizetett, nettó)</span>'
             f'<div class="big" data-count="{float(ytd):.2f}" data-final="{ft(ytd)}">{ft(ytd)}</div>'
             f'<span class="muted small">{len(sz["bevetelkent_szamolt_szamlak"])} számla, a kifizetés napja szerint</span>'
             f'<div class="spark"><canvas id="ch-spark" role="img" aria-label="Göngyölt bevétel alakulása"></canvas></div></div>')
    spans = ["c3", "c3", "c4", "c4", "c4"]
    for i, ((a, b, c), sp) in enumerate(zip(kpis, spans)):
        tiles += (f'<div class="tile {sp}" data-enter style="--i:{6+i}"><span class="label">{E(a)}</span>'
                  f'<div class="big">{b}</div><span class="muted small">{E(c)}</span></div>')
    if ell:
        import re as _re
        msgs_all = [m for f in findings for m in f.get("uzenetek", [])]
        elm = [m for m in msgs_all if " befizetés: " in m]
        elt = [m for m in msgs_all if "≠" in m]
        nsz = [m for m in msgs_all if "NEM SZÁMOLHATÓ" in m]
        elt_ossz = sum(int(x.replace(" ", "").replace(chr(160), "")) for m in elt for x in _re.findall(r"eltérés ([\d  ]+) Ft", m))
        reszek = []
        reszek.append(f"{len(elm)} lejárt, be nem fizetett vagy hiányosan befizetett tétel" if elm else "Nincs lejárt, be nem fizetett tétel az ellenőrizhető határidőknél")
        if elt:
            ugyek = sorted({E(f["teendo"].replace("**", "").split(",")[0]) for f in findings if any("≠" in m for m in f.get("uzenetek", []))})
            reszek.append(f"{len(elt)} eltérés a számított és a NAV által előírt összeg között ({E('; '.join(ugyek))}; összesen {ft(elt_ossz)}): az ok nem állapítható meg, a könyvelővel kell tisztázni")
        if nsz:
            reszek.append(f"{len(nsz)} nem számolható tétel (hiányzó beállítás)")
        # minden észrevétel (lejárt, be nem fizetett tétel; eltérés a számított és a NAV-előírás között; nem számolható tétel) saját piros buborékot kap
        bubi = []
        for f in findings:
            datum = f.get("datum")
            cim = (E(datum.replace("-", ".")) + ". " if datum else "") + E(f.get("teendo", "").replace("**", ""))
            for m in f.get("uzenetek", []):
                if " befizetés: " in m or "≠" in m or "NEM SZÁMOLHATÓ" in m:
                    bubi.append(f'<a class="banner bad" href="#hataridok"><span class="ico" aria-hidden="true">🔴</span><span><strong>{cim}</strong><br>{E(m)}</span></a>')
        kel_b = ROOT / "data" / "konyvelo" / f"ellenorzes_{ev}.json"  # a könyvelői ellenőrzés eltérései is saját buborékot kapnak
        if kel_b.exists():
            for q in loadj(kel_b).get("negyedevek", []):
                for t in q.get("tetelek", []):
                    if t.get("szint") == "hiba":
                        bubi.append(f'<a class="banner bad" href="#konyvelo"><span class="ico" aria-hidden="true">🔴</span><span><strong>Könyvelői ellenőrzés: {q["negyedev"]}. negyedév, {E(t["adonem"])}</strong><br>'
                                    f'a könyvelő {ft(t["konyvelo"])} ≠ számított {ft(t["szamitott"])} (eltérés {ft(abs(t["elteres"]))}); okát nem tudom megállapítani</span></a>')
        if not bubi:
            bubi.append(f'<div class="banner"><span class="ico" aria-hidden="true">✅</span><span>{E(reszek[0])}</span></div>')
        banner = '<div class="banners" role="status" data-enter style="--i:4">' + "".join(bubi) + "</div>"
    else:
        banner = '<div class="banner" role="status" data-enter style="--i:4">Az ellenőrzés még nem futott le; a határidők állapota hiányzik.</div>'
    chips = [(f"Állapot: {today.isoformat()}", False), (f"Számlaadat: {sz['szamlak_forras']} ({sz['szamlak_kora_ora']/24:.1f} napos)", False)]
    if rep:
        chips.append((f"NAV kivonat: {rep['lekerdezes'].replace('T',' ')[:16]}", False))
    if sz["beallitasok"].get("min_alap_tipus_megerositve") is False:
        chips.append(("Minimális járulékalap: nem megerősített", True))
    chips_html = "".join(f'<li{" class=warnchip" if w else ""}>{E(c)}</li>' for c, w in chips)

    # ---- határidők, NAV, következő
    rows, pre_rows, rows_past = [], [], []
    for it in ((ell or {}).get("hataridok") or []):
        if it["szint"] == "indulas_elott":
            pre_rows.append(f'<tr><td>{E(it["datum"].replace("-", "."))}.</td><td>{E(it["adonem"])}</td><td>{E(it["teendo"])}</td></tr>')
            continue
        msgs = "".join(f'<span class="msg">{E(m)}</span>' for m in it["uzenetek"])
        when = f"{it['nap']} nap múlva" if it["nap"] >= 0 else f"{-it['nap']} napja lejárt"
        (rows_past if it["nap"] < 0 else rows).append(f'<tr class="{"past-bad" if it["szint"] == "hiba" else ""}"><td>{E(it["datum"].replace("-", "."))}.</td><td>{E(it["jel"])}</td>'
                    f'<td>{E(it["adonem"])}</td><td>{E(it["teendo"])}{msgs}</td><td class="num">{E(when)}</td></tr>')
    _thead = ('<thead><tr><th>Határidő</th><th>Állapot</th><th>Adónem</th><th>Teendő</th><th class="num">Mikor</th></tr></thead>')

    def _tabla(rs):
        return '<div class="tablewrap"><table>' + _thead + '<tbody>' + "".join(rs) + '</tbody></table></div>'
    if rows:
        cal_html = _tabla(rows)
    elif rows_past:
        cal_html = '<div class="empty">Nincs közelgő határidő az adónaptárban.</div>'
    else:
        cal_html = '<div class="empty">Nincs határidő-állapot adat: futtasd az adoellenorzes skillt.</div>'
    if rows_past:
        _jelek = {}
        for it in ((ell or {}).get("hataridok") or []):
            if it["szint"] != "indulas_elott" and it["nap"] < 0:
                _jelek[it["jel"]] = _jelek.get(it["jel"], 0) + 1
        _osszegzes = " · ".join(f"{k} {v}" for k, v in sorted(_jelek.items()))
        cal_html += (f'<details class="dt past"><summary>{len(rows_past)} lejárt határidő ({E(_osszegzes)})</summary>'
                     + _tabla(rows_past) + '</details>')
    if pre_rows:
        cal_html += (f'<details class="dt"><summary>{len(pre_rows)} határidő a vállalkozás indulása ({E(sz["beallitasok"].get("vallalkozas_kezdete") or "")}) előtt: nem releváns</summary>'
                     '<div class="tablewrap"><table><thead><tr><th>Határidő</th><th>Adónem</th><th>Teendő</th></tr></thead><tbody>'
                     + "".join(pre_rows) + "</tbody></table></div></details>")
    nav_html = ""
    if nav_rows:
        trs = ""
        for nm, r in nav_rows:
            e = r["szamitott_egyenleg"]
            trs += (f'<tr><td>{E(nm)}</td><td class="num">{ft(r["befizetesek_osszesen"])}</td>'
                    f'<td class="num">{ft(abs(e))} {"tartozás" if e > 0 else ("túlfizetés" if e < 0 else "nulla")}</td></tr>')
        nav_html = ('<h3>NAV adószámla adónemenként</h3><div class="tablewrap"><table><thead><tr><th>Adónem</th><th class="num">Befizetve</th>'
                    '<th class="num">Tételekből számított egyenleg</th></tr></thead><tbody>' + trs + '</tbody></table></div>'
                    '<p class="muted small">Az egyenleg a kivonat tételeinek összege; a NAV nem közöl összesített egyenleget.</p>')
    if nxt:
        nxt_html = (f'<div class="card"><h3>Következő adófizetési kötelezettség: {E(nxt["hatarido"].replace("-", "."))}.</h3>'
                    f'<p>SZJA még fedezetlen: <strong>{ft(nxt["szja_fedezetlen"])}</strong>.'
                    + (f' TBJ még fizetendő: <strong>{ft(nxt["tbj_fizetendo"])}</strong>, SZOCHO: <strong>{ft(nxt["szocho_fizetendo"])}</strong>.'
                       if "tbj_fizetendo" in nxt else ' TBJ és SZOCHO: nem számolható (hiányzó beállítás).')
                    + '</p><p class="muted small">A folyamatban lévő negyedév az eddigi adatokkal számolt érték; a végleges csak a negyedév lezárása után ismert.</p></div>')
    else:
        nxt_html = ""
    # ---- a vállalkozás története (data/vallalkozas/profil.json: forrással igazolt tények)
    prof_p = ROOT / "data" / "vallalkozas" / "profil.json"
    if prof_p.exists():
        facts = loadj(prof_p).get("tenyek", [])
        key = {f["kulcs"]: f for f in facts if f.get("kulcs")}

        def dt(x):
            if not x:
                return "dátum nélkül"
            parts = x.split("-")
            return ".".join(parts) + ("." if len(parts) == 3 else "")

        def srcs(f):
            return ", ".join(x.replace("archive/vallalkozas-iratok/", "") for x in f["forras"])

        phases = ""
        if all(k in key for k in ("kezdet", "szunetel_kezdet", "szunetel_veg", "folytatas")):
            ph = [("Működés", f"{dt(key['kezdet']['datum'])} – {dt(key['szunetel_kezdet']['datum'])}", False),
                  ("Szünetelés", f"{dt(key['szunetel_kezdet']['datum'])} – {dt(key['szunetel_veg']['datum'])}", False),
                  ("Folytatás", f"{dt(key['folytatas']['datum'])} –", True)]
            ph.reverse()  # az újabb szakasz előre
            phases = '<div class="phases">' + "".join(
                f'<div class="phase{" on" if on else ""}"><span class="label">{E(n)}</span><div class="rng">{E(r)}</div></div>' for n, r, on in ph) + "</div>"
        dated = sorted((f for f in facts if f.get("datum")), key=lambda f: f["datum"], reverse=True)  # fordított időrend: az újabb van felül
        undated = [f for f in facts if not f.get("datum")]
        tl = "".join(
            f'<li class="tl-item{" hl" if f.get("kulcs") else ""}"><div class="tl-date">{E(dt(f["datum"]))}</div><p>{E(f["allitas"])}</p>'
            f'<p class="muted small">{E(f.get("ellenorzes", "?"))} · forrás: {E(srcs(f))}</p></li>' for f in dated)
        others = "".join(f'<li>{E(f["allitas"])} <span class="muted small">({E(f.get("ellenorzes", "?"))} · {E(srcs(f))})</span></li>' for f in undated)
        hist_html = (f'<p class="sub">Dokumentumokból és megadott adatokból összeállított, forrással ellátott események. A „mappanévből" vagy „fájlnévből" jelölt tények tartalmát nem ellenőriztem.</p>'
                     f'{phases}<ol class="timeline">{tl}</ol>'
                     + (f'<h3>További szereplők</h3><ul class="warn">{others}</ul>' if others else "")
                     + '<p class="muted small">Forrás: data/vallalkozas/profil.json (a vallalkozas-dokumentumok skill). A report nem tartalmaz adószámot, TAJ-számot, címet vagy bankszámlát.</p>')
    else:
        hist_html = '<div class="empty">Még nincs vállalkozói profil: futtasd a vallalkozas-dokumentumok skillt (--profil).</div>'
    # ---- könyvelői dokumentumok és beküldött bevallások (data/konyvelo/, data/nav-egyenleg/bevallasok.json)
    def tbl(headers, rows, left=(0,)):
        th = "".join(f"<th{'' if i in left else ' class=num'}>{E(h)}</th>" for i, h in enumerate(headers))
        trs = "".join("<tr>" + "".join(f"<td{'' if i in left else ' class=num'}>{E(str(c))}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
        return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'

    def idoszak(x):
        if not x:
            return "?"
        if x.startswith("Q"):
            return ["I.", "II.", "III.", "IV."][int(x[1]) - 1] + " negyedév"
        return MONTHS[int(x[1:]) - 1] + "."

    kon_p = ROOT / "data" / "konyvelo" / "konyvelo_adatok.json"
    kel_p = ROOT / "data" / "konyvelo" / f"ellenorzes_{ev}.json"
    reg_p = ROOT / "data" / "nav-egyenleg" / "bevallasok.json"
    TIP = {"utalando": "Utalandó adó/járulék", "berosszesito": "Bérösszesítő", "2658": "2658 bevallás (könyvelőtől)"}
    kel = loadj(kel_p) if kel_p.exists() else None
    if kon_p.exists():
        irat = [x for x in loadj(kon_p)["iratok"] if x.get("ev") == ev]
        rows = []
        for x in sorted(irat, key=lambda x: (x.get("negyedev") or 0, x.get("idoszak") or "", x["tipus"])):
            osz = {t["adonem"]: t["osszeg"] for t in x.get("tetelek", [])}
            per = idoszak(x.get("idoszak")) if x.get("idoszak") else idoszak(f"Q{x.get('negyedev')}")
            rows.append([TIP.get(x["tipus"], x["tipus"]), f"{ev}. {per}",
                         ft(osz["SZJA"]) if "SZJA" in osz else "–", ft(osz["TBJ"]) if "TBJ" in osz else "–",
                         ft(osz["SZOCHO"]) if "SZOCHO" in osz else "–", x.get("kelt") or x.get("nyomtatva") or "–"])
        konyvelo_html = ('<p class="sub">A könyvelőtől kapott iratokból a script által kiolvasott összegek (konyvelo-dokumentumok skill). Személyes azonosító nincs a táblában.</p>'
                         + (tbl(["Irat", "Időszak", "SZJA", "TBJ", "SZOCHO", "Irat kelte"], rows, left=(0, 1)) if rows else '<div class="empty">Nincs ' + str(ev) + '. évi könyvelői irat.</div>'))
        if kel and kel.get("negyedevek"):
            crow = []
            for q in kel["negyedevek"]:
                for t in q["tetelek"]:
                    if "adonem" in t:
                        crow.append([f"{idoszak('Q' + str(q['negyedev']))}", t["adonem"], ft(t["konyvelo"]), ft(t["szamitott"]),
                                     "egyezik ✅" if t["elteres"] == 0 else f"eltérés {ft(t['elteres'])} 🔴"])
            if crow:
                konyvelo_html += ('<h3>A könyvelő számításai a számítottal összevetve (adónemenként)</h3>'
                                  + tbl(["Negyedév", "Adónem", "Könyvelő", "Számított", "Állapot"], crow, left=(0, 1))
                                  + '<p class="muted small">Forrás: data/konyvelo/ellenorzes_' + str(ev) + '.json. Az eltérés okát a script nem tudja megállapítani; a minimális alap típusa nem megerősített (config).</p>')
    else:
        konyvelo_html = '<div class="empty">Még nincs feldolgozott könyvelői irat: másold az input/konyvelo/ mappába, és futtasd a konyvelo-dokumentumok skillt (--feldolgoz).</div>'

    if reg_p.exists():
        reg = loadj(reg_p)["bevallasok"]
        BT = {"2658": "2658 (negyedéves járulékbevallás)", "25SZJA": "25SZJA (éves szja-bevallás)",
              "25EGYSZA": "25EGYSZA (1+1% rendelkező nyilatkozat)", "helyi-ado-kivonat": "Helyi adó adószámla-kivonat"}
        brow = []
        for k, v in sorted(reg.items(), key=lambda kv: kv[0].split("|")[1]):
            tip, per = k.split("|")
            ku = v.get("kulcsadatok") or {}
            kus = "; ".join(f"{('járulékalap' if n == 'jarulekalap' else n.upper())}: {ft(a)}" for n, a in ku.items()) or "–"
            hely = v["forras"].rsplit("/", 1)[0] if "/" in v["forras"] else v["forras"]
            pers = per if "-Q" not in per else per.split("-Q")[0] + ". " + idoszak("Q" + per.split("-Q")[1])
            brow.append([BT.get(tip, tip), pers, kus, hely.replace("archive/vallalkozas-iratok/", ""), len(v.get("duplikatumok", []))])
        bev_html = ('<p class="sub">A NAV-ról letöltött és a könyvelőtől kapott bevallások nyilvántartása (adofizetes skill, bevallasok.py). A duplán bemásolt irat egyszer szerepel; a duplikátumok száma az utolsó oszlopban.</p>'
                    + tbl(["Bevallás", "Időszak", "Kulcsadatok", "Irat helye (archive/vallalkozas-iratok/…)", "Duplikátum"], brow, left=(0, 1, 2, 3)))
        if kel and kel.get("negyedevek"):
            hrow = []
            for q in kel["negyedevek"]:
                ir = next((t for t in q["tetelek"] if t.get("bevallas") in ("2658-irat", "2658-nyilvantartas")), None)
                nv = next((t for t in q["tetelek"] if t.get("bevallas") == "nav-eloiras"), None)
                if ir and ir.get("bevallas") == "2658-nyilvantartas":
                    irs = "megvan, az összegek egyeznek a könyvelővel ✅" if ir["egyezik"] else "megvan, az összegek NEM egyeznek 🔴"
                elif ir and "nyomtatva" in ir:
                    irs = f"megvan, nyomtatva: {ir['nyomtatva']}"
                else:
                    irs = "nincs irat ❓"
                hrow.append([idoszak("Q" + str(q["negyedev"])), q["hatarido"], irs, "van ✅?" if nv and nv["van"] else "nincs 🔴"])
            bev_html += ('<h3>Negyedéves bevallások időbelisége</h3>'
                         + tbl(["Negyedév", "Határidő", "2658 irat", "NAV-előírás a határidő napjára"], hrow, left=(0, 1, 2, 3))
                         + '<p class="muted small">A NAV adószámlán a bevallási előírás megléte a bevallás megtörténtét jelzi, de a beadás napját nem; az irat nyomtatási dátuma sem beadási dátum. Beadási igazolás (NAV beküldési igazolás) kérhető a könyvelőtől.</p>')
    else:
        bev_html = '<div class="empty">Még nincs nyilvántartott bevallás: másold a PDF-eket az input/nav-egyenleg/ mappába, és futtasd az adofizetes skill bevallasok.py scriptjét.</div>'
    # ---- vállalkozás adatai (config + igazolt tények; személyes azonosító nincs benne) és tennivalók
    cfg_p = konfig.vallalkozas_ut()
    cfg = loadj(cfg_p) if cfg_p.exists() else {}
    prof_p2 = ROOT / "data" / "vallalkozas" / "profil.json"
    pf = loadj(prof_p2) if prof_p2.exists() else {}
    nyitott_profil = pf.get("nyitott", []) if isinstance(pf, dict) else []
    ipa_p = ROOT / "data" / "ipa" / f"ipa_{ev}.json"
    JOG = {"egyeni_vallalkozo": "egyéni vállalkozó"}
    ADO = {"atalanyado": "átalányadózó"}
    TBS = {"fofoglalkozasu": "főfoglalkozású"}

    def dtx(x):
        return ".".join(x.split("-")) + "." if x else "?"

    kv = []
    kv.append(("Jogállás, adózás", f"{JOG.get(cfg.get('jogallas'), cfg.get('jogallas') or 'NEM TUDOM')}, {ADO.get(cfg.get('adozasi_mod'), cfg.get('adozasi_mod') or 'NEM TUDOM')}"))
    kv.append(("Főtevékenység", (cfg.get("tevekenyseg") or "NEM TUDOM").replace("szoftverfejlesztes", "szoftverfejlesztés")))
    kv.append(("Költséghányad", f"{float(sz['beallitasok']['koltseghanyad']) * 100:.0f}%" if sz["beallitasok"].get("koltseghanyad") else "NEM TUDOM"))
    kv.append(("TB-státusz", TBS.get(cfg.get("tb_statusz"), cfg.get("tb_statusz") or "NEM TUDOM")))
    mt = cfg.get("min_alap_tipus")
    kv.append(("Minimális járulékalap", (f"{'minimálbér' if mt == 'minimalber' else 'garantált bérminimum' if mt == 'garantalt' else 'NEM TUDOM'}"
                                         + ("" if cfg.get("min_alap_tipus_megerositve") else " (nem megerősített)"))))
    kv.append(("Tevékenység folytatása", dtx(cfg.get("vallalkozas_kezdete")) if cfg.get("vallalkozas_kezdete") else "NEM TUDOM"))
    kv.append(("ÁFA-státusz", "alanyi adómentes (a felhasználó szerint; a Billingo beállítása eltér)"))
    ipa_t = cfg.get("ipa_telepules")
    ipa_mod = {"tetelesen": "tételes", "hagyomanyos": "hagyományos"}.get(cfg.get("ipa_adozasi_mod"), "adózás módja még nincs megadva")
    kv.append(("Iparűzési adó (IPA)", f"{ipa_t}, {ipa_mod}" if ipa_t else "illetékességi hely még nincs megadva"))
    if cfg.get("kamara_koteles") is not None:
        kv.append(("Kamarai hozzájárulás", (f"köteles, {ft(cfg.get('kamara_hozzajarulas_ft') or 0)}, határidő {dtx(cfg.get('kamara_hatarido'))}"
                                            + (" (befizetve, MKIK-igazolás)" if cfg.get("kamara_befizetes_igazolva") else " (befizetés nem igazolt)")) if cfg.get("kamara_koteles") else "nem köteles"))
    kd = cfg.get("kedvezmenyek")
    if kd is not None:
        kv.append(("Adó- és járulékkedvezmények", "nincs: nem jogosult családi, személyi, első házasok, 25 év alattiak vagy anyák kedvezményére" if kd.get("nincs") else ", ".join(k for k, v in kd.items() if v and k != "nincs" and not str(k).startswith("_")) or "nincs eldöntve"))
    if ipa_p.exists():
        kv.append(("Éves IPA (számított)", ft(loadj(ipa_p)["eves_ipa"])))
    vall_html = ('<p class="sub">A config/vallalkozas.json és a vállalkozói profil alapján. Személyes azonosító (adószám, cím, bankszámla) nincs a reportban.</p>'
                 '<div class="kv">' + "".join(f'<div class="kvi"><span class="muted small">{E(k)}</span><strong>{E(v)}</strong></div>' for k, v in kv) + "</div>")

    # tennivalók: ki mit tegyen (feltételekhez kötve, a beállításokból és a számítás eredményéből)
    # ---- a kimenő számlák megfelelőségi ellenőrzése (szamlak/szamla_ellenorzes.py: Áfa tv. szabályok, hivatkozással)
    sze_p = ROOT / "data" / "szamlak" / "szamla_ellenorzes.json"
    szla_card = ""
    sze_db = 0
    if sze_p.exists():
        sze = loadj(sze_p)
        sze_db = sze["hiba"] + sze["figyelmeztetes"]
        sor = []
        for r in sze["eredmenyek"]:
            for f in r["megallapitasok"]:
                if f["szint"] in ("hiba", "figyelmeztetés"):
                    sor.append([r["szamlaszam"], "🔴 hiba" if f["szint"] == "hiba" else "🟡 ellenőrizendő", f["szabaly"], f["uzenet"]])
        fej = (f'<p class="sub">Az Áfa tv. szabályai szerint, számlánként ({sze["szamlak"]} számla; {len(sze.get("stornozott_kihagyva", []))} sztornózott kihagyva). '
               f'<strong>{sze["hiba"]} hiba, {sze["figyelmeztetes"]} ellenőrizendő megállapítás.</strong> A számlázóprogram adatait ellenőrzi, a számla nyomtatott szövegét nem látja.</p>')
        if sor:
            th = "".join(f"<th>{E(h)}</th>" for h in ["Számla", "Szint", "Szabály", "Megállapítás"])
            trs = "".join("<tr>" + "".join(f"<td>{E(str(c))}</td>" for c in r) + "</tr>" for r in sor)
            szla_card = ('<div class="card c12"><h3>Számlák megfelelőségi ellenőrzése</h3>' + fej + '<div class="tablewrap"><table><thead><tr>' + th + "</tr></thead><tbody>" + trs
                         + '</tbody></table></div><p class="muted small">Forrás: data/szamlak/szamla_ellenorzes.json; szabályok: .claude/rules/szamlazas.md.</p></div>')
        else:
            szla_card = '<div class="card c12"><h3>Számlák megfelelőségi ellenőrzése</h3>' + fej + '<p>Nincs kifogás.</p></div>'
    import hashlib as _hl
    import re as _re2
    todo_reg = []
    tisztazott = set(cfg.get("tisztazott_tennivalok") or [])

    class _T(list):
        """A tennivalók listája: minden tétel stabil azonosítót kap (a szöveg betűiből), nyilvántartásba kerül, és a felhasználó által
        tisztázottnak jelölt (config: tisztazott_tennivalok) tétel nem jelenik meg az aktív listában."""
        def __init__(self, ki):
            super().__init__()
            self.ki = ki

        def append(self, szoveg):
            iden = _hl.sha1(_re2.sub(r"[^a-záéíóöőúüű]", "", szoveg.casefold())[:70].encode("utf-8")).hexdigest()[:8]
            todo_reg.append({"id": iden, "ki": self.ki, "szoveg": szoveg, "tisztazott": iden in tisztazott})
            if iden not in tisztazott:
                super().append((szoveg, iden))

    todo_konyvelo, todo_ai, todo_info = _T("konyvelo"), _T("ai"), _T("info")
    bil_p = ROOT / "data" / "vallalkozas" / "billingo-szervezet.json"
    bil = loadj(bil_p).get("szamla_szervezet", {}) if bil_p.exists() else {}
    if not cfg.get("min_alap_tipus_megerositve"):
        todo_konyvelo.append("Kérdezd meg a könyvelőt vagy a NAV-ot, hogy a szoftverfejlesztő főtevékenységnél a minimálbér (322 800 Ft) vagy a garantált bérminimum (373 200 Ft) a minimális járulékalap. "
                             "A NAV tájékoztatója a garantált bérminimumot akkor írja elő, ha a személyes főtevékenység legalább középfokú végzettséget vagy szakképzettséget igényel; hogy a szoftverfejlesztés ide tartozik-e, hivatalos forrás nem mondja ki. A repó jelenleg a minimálbérrel számol, ez nem megerősített.")
    k_hiba = sum(1 for q in (kel or {}).get("negyedevek", []) for t in q["tetelek"] if t.get("szint") == "hiba") if kel else 0
    if k_hiba:
        mondat = f"Tisztázd a könyvelővel a {k_hiba} eltérést a könyvelő által számolt és a számított adók között (lásd a Könyvelői dokumentumok szakaszt)."
        for q in (kel or {}).get("negyedevek", []):
            for t in q["tetelek"]:
                if t.get("adonem") == "TBJ" and t.get("elteres") and t.get("levezetett_alap"):
                    nap = (D(t["levezetett_alap"]) / D(rules["minimalber_havi"]) * 30).quantize(D("0.01"))
                    mondat += (f" A {q['negyedev']}. negyedéves könyvelői TBJ-ből levezetett járulékalap {nap} napnak felel meg (a minimálbér 1/30-ával), "
                               f"a számításunk a tevékenység folytatásától ({dtx(cfg.get('vallalkozas_kezdete'))}) számol; a különbség okát kérdezd meg.")
        todo_konyvelo.append(mondat)
    if sze_db:
        todo_konyvelo.append(f"Számlák megfelelősége: {sze_db} megállapítás a kimenő számlákon (lásd a Bevételek szakasz táblázatát): a figyelmeztetések a számlázóprogram adatai alapján ellenőrizendők a könyvelővel; "
                             "hibás számlát az Áfa tv. 170. § szerinti okirattal (sztornó/helyesbítés) kell javítani. A javítás után futtasd újra az adóellenőrzést.")
    todo_konyvelo.append("Kérj a könyvelőtől vagy a NAV-tól beadási igazolást a negyedéves bevallásokról: az irat nyomtatási dátuma és a NAV-előírás megléte nem mondja meg, mikor adták be.")
    eu = "Egyeztesd a könyvelővel az uniós, külföldi vevők felé kiállított számlák teendőit (áfa-státusz; összesítő nyilatkozat: Áfa tv. 4/A. melléklet I. 1. e) és I. 2. szerint a 37. § szerinti uniós szolgáltatásnyújtásról a tárgyhót/tárgynegyedévet követő hónap 20. napjáig; a rád való vonatkozás nem ellenőrzött); az Áfa tv. 37. § szerint ezek nem belföldi teljesítésű ügyletek (lásd .claude/rules/afa.md), de az összesítő nyilatkozat szabálya a 4/A. mellékletben és az Art.-ban van, amelyek nincsenek a törvénytárban."
    if bil.get("eu_tax_number") and not bil.get("small_taxpayer"):
        eu += " A közösségi adószámod a NAV 2026.07.31-i igazolása szerint megállapított (2026.07.21-től alkalmazható); a Billingo viszont nem jelöli alanyi adómentesként, ami eltér az általad megadott státusztól."
        todo_konyvelo.append("Javítsd a Billingo cégadatait: az alanyi adómentesség jelölése eltér az iratoktól és az általad megadott státusztól (a közösségi adószám rendben van).")
    todo_konyvelo.append(eu)
    if any("devizás" in w for w in warns):
        todo_konyvelo.append("Devizás számlák: kérdezd meg, hogy a bevétel forintosításához a számlán alkalmazott árfolyam (Szja tv. 6. § (2a) a)) vagy az MNB-árfolyam az irányadó, és kinél melyik.")
    _jk_nyitott = [x for x in (sz.get("jogi_kerdesek") or []) if x.get("allapot") != "elfogadva"]
    if _jk_nyitott:
        todo_konyvelo.append(f"{len(_jk_nyitott)} nyitott jogi kérdés (89%-os szabály, minimális alap típusa, időarányosítás, szünetelés stb.): a törvényi hellyel ellátott kérdéslista a data/szamitas/konyvelo_kerdeslista.md fájlban van, vidd a könyvelőhöz/NAV-hoz; "
                             "a választ így rögzítheted: python -I .claude/skills/adoszamitas/scripts/jogi_kerdesek.py --rogzit ID ERTEK --ki \"könyvelő\".")
    todo_konyvelo.append("Kérdezd meg, hogy az időarányos bevételi határnál (Szja tv. 50. § (8)) a nevező a naptári napok száma (365) vagy más; a törvény ezt nem mondja ki.")
    if cfg.get("kedvezmenyek") is None:
        todo_ai.append("Kedvezmények: add meg, melyik jár neked (családi, személyi, első házasok, 25 év alattiak, anyák kedvezményei) vagy hogy egyik sem (\"nincs\"): a számítás elkészült, a részletes adatot (jogosultsági hónapok, eltartottak száma) a config/vallalkozas.json 'kedvezmenyek' mezőjébe kell írni; minta: python -I .claude/skills/adoszamitas/scripts/kedvezmenyek.py --pelda. Könyvelő nem kell hozzá, de a jogosultság feltételeit te felelsz.")
    elif not kd.get("nincs"):
        ks = sz.get("kedvezmenyek_szamitas")
        if ks and ks.get("szamolhato"):
            todo_info.append(f"Kedvezmények: az éves szja kedvezmény nélkül {ft(ks['szja_kedvezmeny_nelkul'])}, kedvezménnyel {ft(ks['szja_kedvezmennyel'])} (megtakarítás {ft(ks['megtakaritas'])}). "
                             "Az adóbevallásban a jogcímekről nyilatkozni kell (pl. Szja tv. 29/B. § (2), 29/D. § (6)); a negyedéves előleg változatlan, a tbj/szocho kedvezmény nélkül számolódik.")
        else:
            todo_ai.append("Kedvezmények: a számításhoz részletes adat kell a config/vallalkozas.json 'kedvezmenyek' mezőjében (jogosultsági hónapok, eltartottak száma stb.; minta: "
                           "python -I .claude/skills/adoszamitas/scripts/kedvezmenyek.py --pelda). Hiányzó vagy hibás: " + "; ".join((ks or {}).get("nem_szamolhato") or ["nincs részletes adat"]))
    if cfg.get("kamara_koteles") is None:
        todo_konyvelo.append("Kamarai hozzájárulás: kérdezd meg, hogy köteles-e a vállalkozás (az egyéni vállalkozó évi 5 000 Ft-ot fizet március 31-ig, kivéve ha a teljes naptári évben szünetel; 1999. évi CXXI. tv. 34/A. §), és rögzítsd a profilban.")
    elif cfg.get("kamara_koteles") and not cfg.get("kamara_befizetes_igazolva"):
        todo_konyvelo.append(f"Kamarai hozzájárulás: igazold a 2026. évi {ft(cfg.get('kamara_hozzajarulas_ft') or 0)} befizetését (határidő {dtx(cfg.get('kamara_hatarido'))}, 1999. évi CXXI. tv. 34/A. §): kérd a banki bizonylatot vagy a kamara igazolását; a repóban nincs befizetési adat.")
    for _mappa, _m in ((ell or {}).get("feldolgozatlan_input") or {}).items():
        todo_ai.append(f"Feldolgozatlan fájlok az input/{_mappa}/ alatt: {_m['db']} fájl ({', '.join(f'{k}={v}' for k, v in _m['tipusok'].items())})"
                       + (f"; {_m['nem_tamogatott']} nem támogatott formátum" if _m.get("nem_tamogatott") else "")
                       + ". Futtasd a megfelelő skillt, és olvasd el az üzenetét: azonosító-eltérés, ismeretlen irattípus vagy ellentmondás miatt maradhatott ott.")
    if cfg.get("ipa_telepules") and ipa_p.exists():
        ipa = loadj(ipa_p)
        todo_konyvelo.append(f"Iparűzési adó ({cfg['ipa_telepules']}, éves IPA a számítás szerint {ft(ipa['eves_ipa'])}): kérdezd meg a könyvelőt, hogy a tételes adózás választását bejelentették-e (Htv. 39/A. § (4)), "
                             "a szüneteléssel töltött napok beleszámítanak-e az időarányosításba, és hogy a 2026. május 31-i előleg-határidő a folytatás (június 16.) előtt esedékes volt-e.")
    elif cfg.get("ipa_telepules"):
        todo_konyvelo.append(f"Iparűzési adó ({cfg['ipa_telepules']}): kérdezd meg az önkormányzati adóhatóságot vagy a könyvelőt a 2026. évi mértékről és mentességről, és hogy a tételes adózást bejelentették-e (Htv. 39/A. § (4)).")
    if not cfg.get("ipa_adozasi_mod") and cfg.get("ipa_telepules"):
        todo_ai.append("Add meg az iparűzési adó módját (tételes vagy hagyományos): a helyi-ipa skill ezt a döntést kéri, addig az IPA nem számolható.")
    if cfg.get("ipa_telepules") and not ipa_p.exists():
        todo_ai.append(f"Futtasd a helyi-ipa skillt: szerezze be {cfg['ipa_telepules']} helyi rendeletét (a hatályos adókulcsot forrással), és számolja ki az éves IPA-t.")
    if not cfg.get("ipa_telepules"):
        todo_ai.append("Add meg az iparűzési adó illetékességi helyét a vallalkozas-dokumentumok skillben (--ipa-javaslat).")
    _sz = {t.get("kulcs"): t.get("datum") for t in (pf.get("tenyek", []) if isinstance(pf, dict) else []) if t.get("kulcs")}
    _fetch_start = f"{ev - 1}-01-01"
    _szunetelt = bool(_sz.get("szunetel_kezdet") and _sz["szunetel_kezdet"] <= _fetch_start <= (_sz.get("folytatas") or "9999-12-31"))
    if not _szunetelt:  # szüneteltetés alatt nem állítható ki számla: ilyenkor a korábbi kiállítású számlák kizárhatók
        todo_ai.append(f"A {ev - 1}. január 1. előtt kiállított, de {ev}-ben kifizetett számlák nem látszanak: az alapértelmezett Billingo-lekérés {ev - 1}. január 1-jétől indul. Ha ilyen számla lehet, kérd a szamlak skilltől a korábbi időszak lekérését.")
    _szja_txt = ""
    for _f in (ROOT / "torvenytar" / "docs" / "szja-tv").rglob("*.txt"):
        _szja_txt += _f.read_text(encoding="utf-8", errors="ignore")
    if not _re2.search(r"^\s*(4|10)\. számú melléklet az? 1995\. évi CXVII\. törvényhez", _szja_txt, _re2.M):
        todo_ai.append("A Szja tv. 4. és 10. számú melléklete nincs a letöltött szövegben (az njt.hu főoldala nem adja a mellékleteket): futtasd a nav-forrasok skillt (a net.jogtar.hu-s kiegészítést is letölti: *.jogtar.txt).")
    navs_ = sorted((ROOT / "data" / "nav-egyenleg").glob("nav_egyenleg_*.json"))
    if navs_:
        lek = loadj(navs_[-1]).get("lekerdezes", "")[:10]
        if lek and lek < today.isoformat():
            todo_ai.append(f"A NAV adószámla kivonat {lek} napi; ha azóta fizettél vagy volt könyvelés, tölts le újat (input/nav-egyenleg/), az adofizetes skill feldolgozza.")
    if any(q["allapot"] == "folyamatban" for q in qs):
        todo_info.append("A folyamatban lévő negyedév összege az eddigi adatokkal számolt, nem végleges; a negyedév lezárása után ismert a végleges.")
    todo_info.append("A Billingo bejövő számla végpontja (/spendings) 0 tételt ad; a kiadások a PDF számlákból jönnek (kiadasok-dokumentumok skill), ezért a Billingóból érkező bejövő számlák mezőneveit nem tudtam ellenőrizni." if not billingo_van
                     else "A Billingo bejövő számláinak (spendings) mezőneveit nem tudtam ellenőrizni, mert nincs rögzített tétel; a diagram a talált mezőkre épül.")
    todo_info.append("Az adónaptár nem NAV-adószámlás tételeit (kamarai díj, helyi adó előleg és bevallás) a repó nem tudja ellenőrizni; az éves IPA összegét a helyi-ipa skill számolja, a befizetését viszont nem követi.")
    todo_info.append("Az adóévhez a bevétel megszerzésének napja számít (a pénz jóváírása), nem a számla kelte: a tavaly kiállított, idén kifizetett számla idei bevétel (Szja tv. 9. § (2) a), a törvényszövegből ellenőrizve).")
    todo_info.append("A töredékhónap minimális alapját naptári naponként a járulékalap 1/30-ával számoljuk; a NAV tájékoztatója ezt írja elő.")

    def ul(items):
        return '<ul class="warn">' + "".join(f'<li>{E(x)} <span class="muted small">[{E(i)}]</span></li>' for x, i in items) + "</ul>"

    # ---- a tennivalók felülvizsgálata minden generáláskor: összevetés az előző állapottal
    tv_p = ROOT / "data" / "szamitas" / f"tennivalok_{ev}.json"
    elozo = loadj(tv_p) if tv_p.exists() else None
    aktiv = [t for t in todo_reg if not t["tisztazott"] and t["ki"] != "info"]
    aktiv_idk = {t["id"] for t in aktiv}
    elozo_idk = {t["id"]: t for t in (elozo or {}).get("tetelek", []) if t.get("ki") != "info"}
    megoldott = [t for i, t in elozo_idk.items() if i not in aktiv_idk]
    uj = [t for t in aktiv if t["id"] not in elozo_idk] if elozo else []
    lezart = [t for t in todo_reg if t["tisztazott"]]
    tv_p.write_text(json.dumps({"keszult": datetime.now().isoformat(timespec="seconds"), "tetelek": [{k: t[k] for k in ("id", "ki", "szoveg")} for t in todo_reg if not t["tisztazott"]]},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    felul = (f'<p class="muted small">A lista a report generálásakor ({datetime.now():%Y-%m-%d %H:%M}) újraértékelődött a beállítások, a feldolgozott adatok és a törvénytár alapján: '
             f'<strong>{len(aktiv)} aktív teendő</strong>'
             + (f", az előző generálás óta <strong>{len(megoldott)} megoldódott</strong>, <strong>{len(uj)} új</strong>" if elozo else " (ez az első felülvizsgálat)") + ". "
             "Egy pont lezárásához add az azonosítóját a config/vallalkozas.json <code>tisztazott_tennivalok</code> listájához (vagy: <code>adoreport.py --lezar ID</code>).</p>")
    if megoldott:
        felul += '<div class="card c12"><h3>Megoldódott az előző generálás óta</h3>' + "".join(f'<p class="small">✅ {E(t["szoveg"][:220])}…</p>' for t in megoldott) + "</div>"
    if lezart:
        felul += '<details class="dt"><summary>Lezárt (tisztázott) pontok: ' + str(len(lezart)) + "</summary><ul class=\"warn\">" + "".join(f"<li>{E(t['szoveg'][:200])}… <span class=\"muted small\">[{E(t['id'])}]</span></li>" for t in lezart) + "</ul></details>"

    tennivalo_html = ('<p class="sub">Mit kell kideríteni vagy megkérdezni, és mit kell az AI-asszisztensnek megadni ahhoz, hogy minden szám ellenőrzött legyen.</p>' + felul +
                      '<div class="grid"><div class="card c6"><h3>Neked kell utánajárnod (könyvelő, NAV, önkormányzat)</h3>' + ul(todo_konyvelo) + '</div>'
                      '<div class="card c6"><h3>Az AI-asszisztensnek kell megadni vagy futtatni</h3>' + ul(todo_ai)
                      + '<h3 style="margin-top:var(--s5)">Amit tudnod kell (korlátok)</h3>' + ul(todo_info) + '</div></div>')
    warn_html = "".join(f"<li>{E(w)}</li>" for w in dict.fromkeys(warns))
    warn_html += "<li>Az IPA, a kamarai díj és az adónaptár egyéb, nem NAV-adószámlás tételei a repó adataiból nem ellenőrizhetők.</li>"

    css = (ASSETS / "report.css").read_text(encoding="utf-8")
    chartjs = (ASSETS / "chart.umd.js").read_text(encoding="utf-8")
    js = (ASSETS / "report.js").read_text(encoding="utf-8")
    payload = json.dumps(P, ensure_ascii=False).replace("</", "<\\/")
    seg = ('<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Világos/sötét téma váltása" title="Világos/sötét téma váltása">'
           '<svg class="i-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
           '<svg class="i-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>')

    return f"""<!doctype html>
<html lang="hu" data-type="software">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="page-type" content="software"><meta name="site-kind" content="software">
<meta name="robots" content="noindex">
<title>Adóreport {ev}</title>
{HEAD_JS}
<style>{css}</style>
</head>
<body>
<a class="skip" href="#fo">Ugrás a tartalomra</a>
<header class="nav"><div class="wrap">
<a class="brand" href="#attekintes">Adóreport <b>{ev}</b></a>
<ul id="nav-menu"><li><a href="#vallalkozas">Vállalkozás</a></li><li><a href="#bevetelek">Bevételek</a></li><li><a href="#kiadasok">Kiadások</a></li><li><a href="#ado">Adó</a></li><li><a href="#hataridok">Határidők</a></li><li><a href="#konyvelo">Könyvelő</a></li><li><a href="#bevallasok">Bevallások</a></li><li><a href="#tennivalok">Tennivalók</a></li><li><a href="#tortenet">Története</a></li></ul>
{seg}
<button type="button" class="menu-toggle" id="menu-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Menü megnyitása"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path class="i-open" d="M4 7h16M4 12h16M4 17h16"/><path class="i-close" d="M6 6l12 12M18 6L6 18"/></svg></button>
</div></header>
<main id="fo">
<section class="hero" id="attekintes"><div class="wrap">
<p class="kicker" data-enter style="--i:0">Átalányadózó egyéni vállalkozó</p>
<h1 data-enter style="--i:1">Adóreport {ev}. <span class="muted">Bevétel, kiadás és adó egy helyen.</span></h1>
<p class="lead" data-enter style="--i:2">A kiállított számlák, a NAV adószámla és az adónaptár alapján. A számokat Python scriptek számolták, nem becslések.</p>
<ul class="chips" data-enter style="--i:3">{chips_html}</ul>
{banner}
<div class="grid" style="margin-top:var(--s7)">{tiles}</div>
</div></section>

<section id="vallalkozas"><div class="wrap"><h2>Vállalkozás adatai</h2>{vall_html}</div></section>

<section id="bevetelek"><div class="wrap"><h2>Bevételek</h2>
<p class="sub">A kifizetés napja szerint, nettó forintban, a számlán alkalmazott árfolyammal.</p>
<div class="grid">
<div class="card c12"><h3>Havi és göngyölt bevétel</h3><div class="chartbox"><canvas id="ch-income" role="img" aria-label="Havi nettó bevétel és göngyölt bevétel {ev}-ben"></canvas></div>{inc_table}</div>
<div class="card c7"><h3>Limitek kihasználtsága</h3><div class="gauges">{gauge_html}</div></div>
<div class="card c5"><h3>Bevétel ügyfelenként</h3><div class="chartbox sm"><canvas id="ch-clients" role="img" aria-label="Bevétel megoszlása ügyfelenként"></canvas></div><ul class="legendlist">{client_list}</ul></div>
{prev_html}
{szla_card}
</div></div></section>

<section id="kiadasok"><div class="wrap"><h2>Kiadások</h2>
<p class="sub">Átalányadózásnál a tényleges kiadás nem csökkenti az adóalapot: a jövedelmet a {pct(kh)} költséghányad adja. A kiadás itt tájékoztató adat.</p>
<div class="grid">
<div class="card c6"><h3>Bejövő számlák havonta</h3>{exp_html}</div>
<div class="card c6"><h3>Átalány-költség és rögzített kiadás</h3><div class="chartbox"><canvas id="ch-deemed" role="img" aria-label="Az átalányban elszámoltnak tekintett költség és a rögzített kiadás összehasonlítása"></canvas></div></div>
{exp_card}</div>
</div></section>

<section id="ado"><div class="wrap"><h2>Adó</h2>
<p class="sub">A göngyölt kötelezettség negyedéves különbsége. A folyamatban lévő negyedév az eddigi adatokkal számolt, nem végleges.</p>
<div class="grid">
<div class="card c12"><h3>Számított negyedéves kötelezettség</h3><div class="chartbox"><canvas id="ch-quarters" role="img" aria-label="Számított negyedéves szja-előleg, tb-járulék és szocho"></canvas></div>{q_table}</div>
<div class="card c6"><h3>Számított kötelezettség és NAV-befizetés</h3><div class="chartbox"><canvas id="ch-cmp" role="img" aria-label="Számított kötelezettség és a NAV adószámlán befizetett összeg adónemenként"></canvas></div></div>
<div class="card c6"><h3>Befizetések havonta a NAV-nál</h3><div class="chartbox"><canvas id="ch-pay" role="img" aria-label="Havi befizetések a NAV adószámlán adónemenként"></canvas></div></div>
<div class="c12">{nxt_html}</div>
<div class="card c12">{nav_html}</div>
</div></div></section>

<section id="hataridok"><div class="wrap"><h2>Határidők</h2>{cal_html}</div></section>

<section id="konyvelo"><div class="wrap"><h2>Könyvelői dokumentumok</h2>{konyvelo_html}</div></section>

<section id="bevallasok"><div class="wrap"><h2>Beküldött bevallások</h2>{bev_html}</div></section>

<section id="tennivalok"><div class="wrap"><h2>Tennivalók</h2>{tennivalo_html}</div></section>

<section id="tortenet"><div class="wrap"><h2>A vállalkozás története</h2>{hist_html}</div></section>
</main>
<footer><div class="wrap">
<p>Készült: {datetime.now():%Y-%m-%d %H:%M}. Forrás: data/szamitas/adoszamitas_{ev}.json, ellenorzes_{ev}.json, data/nav-egyenleg/, data/szamlak/, data/kiadasok/. Diagramok: Chart.js v4.4.7 (MIT), beágyazva.</p>
<p>Tájékoztató jellegű, nem adótanácsadás. Döntés előtt egyeztess a könyvelőddel vagy a NAV-val.</p>
</div></footer>
<script id="report-data" type="application/json">{payload}</script>
<script>{chartjs}</script>
<script>{js}</script>
</body></html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="HTML adóreport készítése a feldolgozott adatokból.")
    ap.add_argument("--ev", type=int, default=date.today().year, help="az adóév (alapból az aktuális év)")
    ap.add_argument("--lezar", metavar="ID", help="egy tennivaló lezárása (tisztázottnak jelölése) az azonosítója alapján; a config/vallalkozas.json-ba kerül")
    a = ap.parse_args()
    if a.lezar:
        cp = konfig.vallalkozas_ut()
        c = json.loads(cp.read_text(encoding="utf-8"))
        l = c.setdefault("tisztazott_tennivalok", [])
        if a.lezar not in l:
            l.append(a.lezar)
        cp.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Lezárva: {a.lezar} (config/vallalkozas.json: tisztazott_tennivalok)")
    page = build(a.ev)
    out = ROOT / "tax-reports"
    out.mkdir(exist_ok=True)
    p = out / f"adoreport_{a.ev}.html"
    p.write_text(page, encoding="utf-8")
    print(f"Report: {p.relative_to(ROOT)} ({len(page)//1024} KB)")


if __name__ == "__main__":
    main()

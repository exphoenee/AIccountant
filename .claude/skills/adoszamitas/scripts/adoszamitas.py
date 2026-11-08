#!/usr/bin/env python3
"""Adókötelezettség kiszámítása a Billingo számlák alapján (átalányadózó egyéni vállalkozó).

Használat:
    python -I .claude/skills/adoszamitas/scripts/adoszamitas.py
    python -I .claude/skills/adoszamitas/scripts/adoszamitas.py --szamlak data/szamlak/szamlak_2026-01-01_2026-12-31.json

Bemenet (mind a repóból, lásd .claude/rules/adatkezeles.md):
    data/szamlak/szamlak_<tol>_<ig>.json   (skill: szamlak)
    data/adonaptar/<év>.json               (skill: adonaptar)  – a negyedéves határidők forrása
    config/vallalkozas.json, config/szabalyok_<év>.json      – beállítások és szabályparaméterek
Kimenet: képernyő + data/szamitas/adoszamitas_<év>.json

Elvek (.claude/rules/nincs-becsles.md): nincs becslés; ha beállítás hiányzik, az érintett számítás
'NEM SZÁMOLHATÓ'. Decimal aritmetika, a végén forintra kerekítés (fél felfelé).
A kerekítési szabály NAV szerinti helyességét nem ellenőriztem; a NAV-kivonattal való összevetést
az adoellenorzes skill végzi.
"""
import argparse
import calendar
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
CONFIG = ROOT / "config"


def D(x) -> Decimal:
    return Decimal(str(x))


def rnd(x) -> int:
    return int(D(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def ft(n) -> str:
    return f"{int(n):,}".replace(",", " ") + " Ft"


def die(msg):
    sys.exit(f"HIBA: {msg}")


# ------------------------------------------------------------------- bemenetek

def load_configs(cfg_path, ev=None):
    p = Path(cfg_path) if cfg_path else konfig.vallalkozas_ut()
    if not p.exists():
        die(f"hiányzik a {p}")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["ev"] = ev or cfg["ev"]  # az adóév: argumentum, különben a config éve
    rp = konfig.szabalyok_ut(cfg["ev"])
    if not rp.exists():
        die(f"hiányzik a szabályparaméter-fájl: {rp.relative_to(ROOT)} (évente létre kell hozni a .claude/rules alapján)")
    return cfg, json.loads(rp.read_text(encoding="utf-8"))


def find_invoice_file(ev, explicit, today):
    if explicit:
        p = Path(explicit)
        if not p.exists():
            die(f"nincs ilyen fájl: {p}")
        return p
    ok = []
    # az egyesített, keresztvalidált számlafájl (Billingo + Számlázz.hu + bevételi fájlok) az elsődleges; a nyers Billingo-fájl csak tartalék
    egyesitett = list((ROOT / "data" / "szamlak").glob("egyesitett_*.json"))
    for p in (egyesitett or (ROOT / "data" / "szamlak").glob("szamlak_*.json")):
        m = re.fullmatch(r"(?:egyesitett|szamlak)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.json", p.name)
        # az adóévi számításhoz az előző év elejétől kell a számlaadat: a tavaly kiállított, idén kifizetett számla idei bevétel
        if m and date.fromisoformat(m.group(1)) <= date(ev - 1, 1, 1) and \
                date.fromisoformat(m.group(2)) >= min(today, date(ev, 12, 31)):
            ok.append(p)
    if not ok:
        die(f"nincs {ev}. évet lefedő számlafájl a data/szamlak/ alatt. Futtasd a 'szamlak' skillt "
            f"({ev}-01-01 – {ev}-12-31).")
    return max(ok, key=lambda p: p.stat().st_mtime)


def load_calendar(ev):
    p = ROOT / "data" / "adonaptar" / f"{ev}.json"
    if not p.exists():
        die(f"nincs feldolgozott adónaptár ({p.relative_to(ROOT)}). Futtasd az 'adonaptar' skillt.")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ számlák

def classify(docs, ev):
    counted, unpaid, excluded, partial = [], [], [], []
    for d in docs:
        num, t = d.get("invoice_number"), d.get("type")
        if t == "cancellation":
            excluded.append((num, "stornó bizonylat")); continue
        if d.get("cancelled"):
            excluded.append((num, "stornózott számla")); continue
        if t != "invoice":
            excluded.append((num, f"nem kezelt bizonylattípus: {t}")); continue
        s = d.get("summary") or {}
        if s.get("net_amount_local") is None:
            excluded.append((num, "hiányzik a nettó forintérték (summary.net_amount_local)")); continue
        status = d.get("payment_status")
        if status == "paid" and d.get("paid_date"):
            if d["paid_date"][:4] == str(ev):
                counted.append(d)
            else:
                excluded.append((num, f"kifizetés nem {ev}-ben történt ({d['paid_date']})"))
        elif status == "partial":
            partial.append(d)
        else:
            unpaid.append(d)
    return counted, unpaid, excluded, partial


# ---------------------------------------------------------------- számítás

def szunetelesek(cfg):
    """A config 'szunetelesek' listája: [(tol, ig), ...] (naptári napok, mindkét nap beleértve)."""
    out = []
    for s in cfg.get("szunetelesek") or []:
        out.append((date.fromisoformat(s["tol"]), date.fromisoformat(s["ig"])))
    return out


def _szunet_napok(a, b, szun):
    """Az [a, b] intervallumba eső szünetelő napok száma (az átfedő szüneteléseket egyszer számolja)."""
    napok = set()
    for s0, s1 in szun:
        x, y = max(a, s0), min(b, s1)
        d = x
        while d <= y:
            napok.add(d)
            d = date.fromordinal(d.toordinal() + 1)
    return len(napok)


def active_fraction(year, month, start, end, szun=()):
    dim = calendar.monthrange(year, month)[1]
    a = max(date(year, month, 1), start) if start else date(year, month, 1)
    b = min(date(year, month, dim), end) if end else date(year, month, dim)
    if b < a:
        return D(0)
    days = (b - a).days + 1 - _szunet_napok(a, b, szun)
    if days <= 0:
        return D(0)
    # Teljes hónap = 1. Töredék hónap: naptári naponként a járulékalap harmincad része
    # (forrás: torvenytar/NAV/2026/atalanyado-alapveto-szabalyai-2026-02-20.txt, a járulékfizetési alsó határról szóló rész).
    # A szünetelő napok kihagyása értelmezés (a jogállás szünetelés alatti hatása nem ellenőrzött: könyvelő / NAV).
    return D(1) if days >= dim else min(D(days) / D(30), D(1))


def prorated_limit(ev, cfg, rules):
    """Az 52. § (1) szerinti bevételi értékhatár időarányosítása: Szja tv. 50. § (8), 'a tevékenység folytatásának napjaival'.
    A törvény a nevezőt nem mondja ki; a naptári napok / az adóév napjai értelmezést használjuk (nem ellenőrzött).
    A config 'szunetelesek' napjai kimaradnak a folytatás napjaiból."""
    y0, y1 = date(ev, 1, 1), date(ev, 12, 31)
    start = date.fromisoformat(cfg["vallalkozas_kezdete"]) if cfg.get("vallalkozas_kezdete") else None
    end = date.fromisoformat(cfg["vallalkozas_megszunese"]) if cfg.get("vallalkozas_megszunese") else None
    a = max(start, y0) if start else y0
    b = min(end, y1) if end else y1
    days, ydays = max((b - a).days + 1, 0), (y1 - y0).days + 1
    szun = _szunet_napok(a, b, szunetelesek(cfg)) if days else 0
    days -= szun
    full = rules["bevetel_hatar_altalanos"]
    return {"eves_hatar": full, "aktiv_napok": days, "ev_napjai": ydays, "kezdet": a.isoformat(), "veg": b.isoformat(),
            "szunetelo_napok": szun,
            "hatar": int((D(full) * D(days) / D(ydays)).quantize(Decimal(1), rounding=ROUND_HALF_UP)),
            "idoaranyos": days < ydays}


def compute(ev, counted, cfg, rules, cal, today):
    kh = D(cfg["koltseghanyad"])
    mentes = D(rules["adomentes_jovedelem_eves"])
    szja_k, tbj_k, szo_k = D(rules["szja_kulcs"]), D(rules["tbj_kulcs"]), D(rules["szocho_kulcs"])

    missing = []
    status = cfg.get("tb_statusz")
    if status is None:
        missing.append("tb_statusz")
    elif status not in ("fofoglalkozasu", "munkaviszony_36_vagy_nappali", "nyugdijas"):
        die(f"érvénytelen tb_statusz: {status!r}")
    min_alap = None
    start = end = None
    if status == "fofoglalkozasu":
        t = cfg.get("min_alap_tipus")
        if t is None:
            missing.append("min_alap_tipus")
        elif t == "minimalber":
            min_alap = D(rules["minimalber_havi"])
        elif t == "garantalt":
            min_alap = D(rules["garantalt_berminimum_havi"])
        else:
            die(f"érvénytelen min_alap_tipus: {t!r}")
        if cfg.get("vallalkozas_kezdete") is None:
            missing.append("vallalkozas_kezdete")
        else:
            start = date.fromisoformat(cfg["vallalkozas_kezdete"])
        if cfg.get("vallalkozas_megszunese"):
            end = date.fromisoformat(cfg["vallalkozas_megszunese"])
    szun = szunetelesek(cfg)
    jarulek_ok = not missing

    due = {}
    for r in cal["tetelek"]:
        q = r.get("negyedev")
        if q and q["ev"] == ev and r["tipus"] in ("szja_eloleg", "tb_szocho"):
            due.setdefault(q["negyedev"], {})[r["tipus"]] = r["datum"]

    rows, cum_b, prev = [], D(0), {"szja": 0, "tbj": 0, "szo": 0}
    cum_min, prior_base = D(0), D(0)
    for q in range(1, 5):
        qs = date(ev, 3 * q - 2, 1)
        if qs > today:
            break
        qe = date(ev, 3 * q, calendar.monthrange(ev, 3 * q)[1])
        b_q = sum((D(d["summary"]["net_amount_local"]) for d in counted
                   if qs <= date.fromisoformat(d["paid_date"]) <= qe), D(0))
        cum_b += b_q
        jov = cum_b * (D(1) - kh)
        szja_alap = max(D(0), jov - mentes)
        szja_cum = rnd(szja_alap * szja_k)
        row = {"negyedev": q, "tol": qs.isoformat(), "ig": qe.isoformat(),
               "allapot": "lezárt" if today > qe else "folyamatban",
               "szja_hatarido": due.get(q, {}).get("szja_eloleg"),
               "tb_hatarido": due.get(q, {}).get("tb_szocho"),
               "bevetel_negyedev": rnd(b_q), "bevetel_gongyolt": rnd(cum_b),
               "bevetel_gongyolt_pontos": str(cum_b),
               "jovedelem_gongyolt": rnd(jov), "szja_alap_gongyolt": rnd(szja_alap),
               "szja_gongyolt": szja_cum, "szja_eloleg": szja_cum - prev["szja"]}
        prev["szja"] = szja_cum
        if jarulek_ok and status == "nyugdijas":
            row.update(jarulekalap_gongyolt=0, tbj_gongyolt=0, tbj_eloleg=0, szocho_gongyolt=0, szocho_eloleg=0,
                       min_alap_gongyolt=0)
        elif jarulek_ok:
            # NAV göngyölítés (torvenytar/NAV/2026/atalanyado-alapveto-szabalyai-2026-02-20.txt, 6.1.): a negyedév járulékalapja
            # = (az év elejétől göngyölt, adómentes rész nélküli jövedelem) − (a korábbi negyedévekben ténylegesen figyelembe
            # vett járulékalap), de legalább a negyedév minimális alapja (havonta a minimálbér/garantált bérminimum;
            # töredék hónapban naponként a harmincad része).
            if status == "munkaviszony_36_vagy_nappali":
                # NAV tájékoztató 6.2.: heti 36 órás munkaviszony / nappali tanulmányok mellett a tbj és szocho alapja a göngyölítéssel
                # megállapított összeg; minimális alapról a forrás nem szól, ezért nincs minimális alap (nem becslünk többet).
                min_q = D(0)
            else:
                min_q = sum((min_alap * active_fraction(ev, m, start, end, szun) for m in (3 * q - 2, 3 * q - 1, 3 * q)), D(0))
            cum_min += min_q
            base_q = max(szja_alap - prior_base, min_q)
            prior_base += base_q
            base = prior_base
            tbj_c, szo_c = rnd(base * tbj_k), rnd(base * szo_k)
            row.update(min_alap_gongyolt=rnd(cum_min), jarulekalap_negyedev=rnd(base_q), jarulekalap_gongyolt=rnd(base),
                       tbj_gongyolt=tbj_c, tbj_eloleg=tbj_c - prev["tbj"],
                       szocho_gongyolt=szo_c, szocho_eloleg=szo_c - prev["szo"])
            prev["tbj"], prev["szo"] = tbj_c, szo_c
        else:
            row.update(jarulekalap_gongyolt=None, tbj_gongyolt=None, tbj_eloleg=None,
                       szocho_gongyolt=None, szocho_eloleg=None, min_alap_gongyolt=None)
        rows.append(row)
    return rows, missing


# ---------------------------------------------------------------------- main

def egyeb_fizetendo(cfg, ev):
    """Nem adószámlás, de törvényi kötelezettségek: kamarai hozzájárulás (1999. évi CXXI. tv. 34/A. §: évi 5000 Ft, március 31-ig).
    Csak akkor számol, ha a felhasználó kötelezettnek mondta magát és az összeg megvan; különben jelzi, mi hiányzik. Nem becsül."""
    tetelek, figy = [], []
    k = cfg.get("kamara_koteles")
    if k is None:
        figy.append("NEM SZÁMOLHATÓ: a kamarai hozzájárulás kötelezettsége nincs megadva (config: kamara_koteles). Kérdezd meg a vállalkozó profil készítésekor.")
    elif k:
        osszeg = cfg.get("kamara_hozzajarulas_ft")
        if osszeg is None:
            figy.append("NEM SZÁMOLHATÓ: a kamarai hozzájárulás összege nincs megadva (config: kamara_hozzajarulas_ft; 2026-ban a törvény szerint 5000 Ft).")
        else:
            tetelek.append({"nev": "Kamarai hozzájárulás", "osszeg": int(osszeg), "hatarido": cfg.get("kamara_hatarido") or f"{ev}-03-31",
                            "befizetes_igazolva": bool(cfg.get("kamara_befizetes_igazolva")),
                            "forras": "1999. évi CXXI. törvény 34/A. § (2)-(3) (torvenytar/kamarai-tv/2026/)"})
            if not cfg.get("kamara_befizetes_igazolva"):
                figy.append(f"A kamarai hozzájárulás ({int(osszeg)} Ft, határidő {cfg.get('kamara_hatarido') or f'{ev}-03-31'}) befizetése nincs igazolva a repó adataiban: "
                            "kérd a banki bizonylatot vagy a kamara igazolását.")
    return tetelek, figy


def kedvezmeny_ellenorzes(cfg):
    """Kedvezmények: ha a felhasználó 'nincs' választ adott, a számítás nem csökken. Ha bármelyiket választotta, a számítás
    még nincs implementálva (a törvényi képletek külön ellenőrzést igényelnek): ezt kimondjuk, nem hagyjuk csendben figyelmen kívül."""
    kd = cfg.get("kedvezmenyek")
    if kd is None:
        return ["NEM SZÁMOLHATÓ: a kedvezményekre való jogosultság nincs megadva (config: kedvezmenyek). Kérdezd meg a vállalkozó profil készítésekor."]
    if kd.get("nincs"):
        return []
    valasztott = [k for k, v in kd.items() if k != "nincs" and v]
    if valasztott:
        return ["NEM SZÁMOLHATÓ: a(z) " + ", ".join(valasztott) + " kedvezmény számítása nincs implementálva; a kimenet kedvezmény nélkül számol. Egyeztess a könyvelővel."]
    return ["NEM SZÁMOLHATÓ: a kedvezményekre való jogosultság nincs eldöntve (config: kedvezmenyek)."]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Adókötelezettség a Billingo számlák alapján.")
    ap.add_argument("--szamlak", help="számla JSON (alapból a legfrissebb, az évet lefedő)")
    ap.add_argument("--config", help="teszteléshez: másik vallalkozas.json")
    ap.add_argument("--ma", type=date.fromisoformat, default=date.today(), help="teszteléshez")
    ap.add_argument("--csendes", action="store_true", help="nem ír a képernyőre, csak a data/ fájlt menti")
    ap.add_argument("--ev", type=int, help="az adóév (alapból az aktuális év)")
    a = ap.parse_args()

    today = a.ma
    ev = a.ev or today.year
    cfg, rules = load_configs(a.config, ev)
    if rules["ev"] != ev:
        die("a vallalkozas.json és a szabalyok fájl éve nem egyezik")
    inv_path = find_invoice_file(ev, a.szamlak, today)
    docs = json.loads(inv_path.read_text(encoding="utf-8"))
    age_h = (datetime.now() - datetime.fromtimestamp(inv_path.stat().st_mtime)).total_seconds() / 3600
    cal = load_calendar(ev)
    counted, unpaid, excluded, partial = classify(docs, ev)
    rows, missing = compute(ev, counted, cfg, rules, cal, today)

    warns = []
    if age_h > 24:
        warns.append(f"A számlaadat {age_h/24:.1f} napos; azóta kiállított/kifizetett számlák hiányozhatnak. Frissítsd a 'szamlak' skill-lel.")
    prev_year = [d for d in counted if (d.get("invoice_date") or "")[:4] < str(ev)]
    warns.append("Az adóévhez a bevétel megszerzésének napja (a pénz jóváírása, Billingo: paid_date) számít (Szja tv. 9. § (2) a)), nem a számla kelte: "
                 f"a {ev - 1}. évben kiállított, {ev}-ben kifizetett számla {ev}. évi bevétel; a {ev}-ben kiállított, {ev + 1}-ben kifizetett pedig {ev + 1}. évi. "
                 "A vállalkozói bevételről szóló 4. és 10. számú melléklet szövege nincs a letöltött njt.hu-kivonatban, ezért az esetleges eltérő időpont-szabályt nem tudtam ellenőrizni.")
    warns.append(f"A Billingo dátumszűrője a számla KIÁLLÍTÁSI dátumára vonatkozik, ezért a lekérés a {ev - 1}. év elejétől indul. "
                 f"A {ev - 1}. évnél korábban kiállított, {ev}-ben kifizetett számla nem látszik; ilyen számla létezését nem ellenőriztem (kérd a szamlak skilltől a korábbi időszak lekérését).")
    warns.append("NYITOTT JOGI KÉRDÉS (nem számoltam vele): az Szja tv. 29. § és 47. § (5) szerint, ha a magánszemély szocho-fizetésre kötelezett, "
                 "a megállapított jövedelem 89%-át kell figyelembe venni; a NAV 2026-os számpéldája és ez a számítás ezt nem alkalmazza. "
                 "A letöltött törvényszöveg és a NAV-példa látszólag ellentmond; a feloldást a repó nem tartalmazza. Az szja összege emiatt eltérhet: "
                 "egyeztess a könyvelővel vagy a NAV-val.")
    if cfg.get("szunetelesek"):
        warns.append("A config 'szunetelesek' napjai kimaradnak az időarányos bevételi határból és a töredékhónapos minimális alapból. "
                     "Hogy a szünetelés alatt a járulék szempontjából a jogállás fennáll-e, nem ellenőrzött: könyvelő / NAV.")
    if cfg.get("tb_statusz") == "nyugdijas":
        warns.append("Nyugdíjas státusznál tbj/szocho nincs. Kivétel: az anyák kedvezményét érvényesítő saját jogú nyugdíjas szochója "
                     "(NAV tájékoztató 6.3.): ezt a számítás nem kezeli.")
    if cfg.get("tb_statusz") == "munkaviszony_36_vagy_nappali":
        warns.append("Heti 36 órás munkaviszony / nappali tanulmányok mellett a tbj és szocho alapja a göngyölített jövedelem (NAV tájékoztató 6.2.); "
                     "minimális alapot nem számolok. Ha a göngyölt jövedelem nem haladja meg az adómentes keretet, akkor sincs fizetendő, de a 2658-as bevallás kötelező.")
    foreign = [d for d in counted if d.get("currency") != "HUF"]
    if foreign:
        warns.append(f"{len(foreign)} számla devizás; a forintérték a Billingo árfolyamával számolt. "
                     "Szja tv. 6. § (2a) a): egyéni vállalkozónál az irányadó az az árfolyam, amelyet az ügyletben az áfa-alap forintra átszámításához alkalmaz (a Billingo a számlán alkalmazott árfolyamot adja); alternatíva: 6. § (4) b), MNB-árfolyam a bevétel napját megelőző hónap 15-én. Nem ellenőrzött: a külföldi vevős, alanyi adómentes ügyleteidre a (2a) a) pont vonatkozik-e; egyeztess a könyvelővel (lásd .claude/rules/bevetel-nyilvantartas.md).")
    if partial:
        warns.append(f"🔴 {len(partial)} részben fizetett számla van ({', '.join(str(d.get('invoice_number')) for d in partial)}); a beérkezett rész "
                     "a pénz megérkezésekor már bevétel lehet (bevetel-nyilvantartas.md), de a részkifizetés összege nem érhető el, ezért NEM számoltam bele: "
                     "a bevétel, a bevételi határ kihasználtsága és az adó alulszámolt lehet. Add meg a beérkezett összegeket a könyvelőnek.")
    if any("nem kezelt" in r for _, r in excluded):
        warns.append("Van nem kezelt bizonylattípus (lásd a kizárt tételeket); nem számoltam bevételnek.")
    lim = prorated_limit(ev, cfg, rules)
    if lim["idoaranyos"]:
        warns.append(f"Időarányos bevételi határ (Szja tv. 50. § (8)): {lim['aktiv_napok']}/{lim['ev_napjai']} nap, {ft(lim['eves_hatar'])} helyett {ft(lim['hatar'])}. "
                     "A törvény a nevezőt nem mondja ki; a naptári napok / az adóév napjai értelmezést használom (nem ellenőrzött). "
                     "Az adómentes jövedelemkeret (1 936 800 Ft) év közbeni kezdésnél nem arányosítandó (NAV tájékoztató).")
    if not (cfg.get("kedvezmenyek") or {}).get("nincs"):
        warns.append("Az szja-számítás kedvezményeket (családi stb.) nem tartalmaz; a töredékhónap minimális alapját naptári naponként a járulékalap 1/30-ával számolom (NAV tájékoztató).")

    alt = None
    if (not missing and cfg.get("tb_statusz") == "fofoglalkozasu" and cfg.get("min_alap_tipus")
            and cfg.get("min_alap_tipus_megerositve") is False):
        other = "garantalt" if cfg["min_alap_tipus"] == "minimalber" else "minimalber"
        alt_rows, _ = compute(ev, counted, {**cfg, "min_alap_tipus": other}, rules, cal, today)
        if alt_rows and rows and alt_rows[-1]["tbj_gongyolt"] is not None:
            r0, r1 = rows[-1], alt_rows[-1]
            alt = {"min_alap_tipus": other, "tbj_gongyolt": r1["tbj_gongyolt"], "szocho_gongyolt": r1["szocho_gongyolt"],
                   "kulonbseg_tbj": r1["tbj_gongyolt"] - r0["tbj_gongyolt"],
                   "kulonbseg_szocho": r1["szocho_gongyolt"] - r0["szocho_gongyolt"]}
            alt["negyedevek"] = [
                {"negyedev": a_["negyedev"], "kulonbseg_tbj_eloleg": a_["tbj_eloleg"] - r_["tbj_eloleg"],
                 "kulonbseg_szocho_eloleg": a_["szocho_eloleg"] - r_["szocho_eloleg"]}
                for r_, a_ in zip(rows, alt_rows)]
            diffs = "; ".join(f"{q['negyedev']}. n.év: TBJ {q['kulonbseg_tbj_eloleg']:+,} Ft, SZOCHO {q['kulonbseg_szocho_eloleg']:+,} Ft".replace(",", " ")
                              for q in alt["negyedevek"] if q["kulonbseg_tbj_eloleg"] or q["kulonbseg_szocho_eloleg"]) or "nincs különbség"
            warns.append(
                f"NEM MEGERŐSÍTETT minimális alap: a számítás a '{cfg['min_alap_tipus']}' típussal fut. A '{other}' típussal az év végi göngyölt "
                f"TBJ különbsége {ft(alt['kulonbseg_tbj'])}, a SZOCHO-é {ft(alt['kulonbseg_szocho'])}; a negyedéves előlegek különbsége: {diffs}. "
                "Döntés: könyvelő vagy NAV.")

    last = rows[-1] if rows else None
    ytd = last["bevetel_gongyolt"] if last else 0
    limit = lim["hatar"]
    ratio = D(ytd) / D(limit) if limit else D(0)
    mentes_ratio = (D(last["jovedelem_gongyolt"]) / D(rules["adomentes_jovedelem_eves"])) if last else D(0)

    egyeb, egyeb_figy = egyeb_fizetendo(cfg, ev)
    warns += egyeb_figy + kedvezmeny_ellenorzes(cfg)

    result = {
        "ev": ev, "szamitas_datuma": today.isoformat(), "szamlak_forras": inv_path.name,
        "szamlak_kora_ora": round(age_h, 1),
        "beallitasok": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "hianyzo_beallitasok": missing,
        "bevetelkent_szamolt_szamlak": [
            {"szamlaszam": d.get("invoice_number"), "kifizetve": d["paid_date"], "deviza": d.get("currency"),
             "arfolyam": d.get("conversion_rate"), "netto_huf": str(D(d["summary"]["net_amount_local"]))}
            for d in sorted(counted, key=lambda d: d["paid_date"])],
        "nem_szamolt": [{"szamlaszam": n, "ok": r} for n, r in excluded],
        "elozo_evben_kiallitott_idei_kifizetes": [
            {"szamlaszam": d.get("invoice_number"), "kelt": d.get("invoice_date"), "kifizetve": d["paid_date"],
             "deviza": d.get("currency"), "netto_huf": str(D(d["summary"]["net_amount_local"]))}
            for d in sorted(prev_year, key=lambda d: d["paid_date"])],
        "reszben_fizetett_szamlak": [{"szamlaszam": d.get("invoice_number"), "kelt": d.get("invoice_date"), "deviza": d.get("currency")} for d in partial],
        "kintlevo_szamlak": [{"szamlaszam": d.get("invoice_number"), "kelt": d.get("invoice_date"),
                              "fizetesi_hatarido": d.get("due_date"), "deviza": d.get("currency"),
                              "netto_huf": str(D(d["summary"]["net_amount_local"]))} for d in unpaid],
        "negyedevek": rows,
        "bevetel_hatar": {"hatar": limit, "eves_hatar": lim["eves_hatar"], "aktiv_napok": lim["aktiv_napok"],
                          "ev_napjai": lim["ev_napjai"], "idoaranyos": lim["idoaranyos"], "bevetel": ytd,
                          "kihasznaltsag": str(ratio.quantize(Decimal("0.0001")))},
        "adomentes_keret_kihasznaltsag": str(mentes_ratio.quantize(Decimal("0.0001"))),
        "alternativ_min_alap": alt,
        "egyeb_fizetendo": egyeb,
        "kedvezmenyek": cfg.get("kedvezmenyek"),
        "figyelmeztetesek": warns,
    }
    out_dir = ROOT / "data" / "szamitas"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"adoszamitas_{ev}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.csendes:
        return

    print(f"== Adókötelezettség a kiállított számlák alapján – {ev} (állapot: {today}) ==")
    print(f"Számlaadat: {inv_path.name} ({age_h/24:.1f} napos)  |  költséghányad: {D(cfg['koltseghanyad'])*100:.0f}%")
    print(f"Bevételként számolt számla: {len(counted)} db (kifizetés dátuma szerint, nettó HUF)")
    for s in result["bevetelkent_szamolt_szamlak"]:
        cur = "" if s["deviza"] == "HUF" else f", {s['deviza']} @ {s['arfolyam']}"
        print(f"  {s['kifizetve']}  {s['szamlaszam']:<14} {ft(rnd(s['netto_huf'])):>16}{cur}")
    if excluded:
        print(f"Nem számolt ({len(excluded)} db): " + "; ".join(f"{n} ({r})" for n, r in excluded))
    if prev_year:
        print(f"Ebből a {ev - 1}. évben kiállított, {ev}-ben kifizetett: {len(prev_year)} db, "
              f"{ft(rnd(sum(D(d['summary']['net_amount_local']) for d in prev_year)))} ({ev}. évi bevétel, Szja tv. 9. § (2) a)):")
        for d in sorted(prev_year, key=lambda d: d["paid_date"]):
            print(f"    {d.get('invoice_number')}: kelt {d.get('invoice_date')}, kifizetve {d['paid_date']}")
    else:
        print(f"{ev - 1}. évben kiállított, {ev}-ben kifizetett számla: nincs (a számlaadat az {ev - 1}. év elejétől tartalmaz számlákat).")
    if unpaid:
        print(f"Kintlévő (még nem fizetett, NEM bevétel): {len(unpaid)} db, "
              f"{ft(rnd(sum(D(d['summary']['net_amount_local']) for d in unpaid)))}")
    print()
    for r in rows:
        print(f"{r['negyedev']}. negyedév ({r['tol']} – {r['ig']}, {r['allapot']})")
        print(f"  bevétel a negyedévben:        {ft(r['bevetel_negyedev'])}")
        print(f"  göngyölt bevétel:             {ft(r['bevetel_gongyolt'])}")
        print(f"  göngyölt átalányos jövedelem: {ft(r['jovedelem_gongyolt'])}")
        print(f"  göngyölt szja-alap (jöv. − adómentes): {ft(r['szja_alap_gongyolt'])}")
        print(f"  SZJA göngyölt: {ft(r['szja_gongyolt'])}  ->  negyedéves előleg: {ft(r['szja_eloleg'])}"
              f"   (határidő: {r['szja_hatarido'] or 'nincs az adónaptárban'})")
        if r["tbj_gongyolt"] is None:
            print(f"  TBJ / SZOCHO: NEM SZÁMOLHATÓ – hiányzó beállítás(ok) a config/vallalkozas.json-ban: {', '.join(missing)}")
        else:
            print(f"  járulékalap göngyölt: {ft(r['jarulekalap_gongyolt'])} (ebből minimális alap: {ft(r['min_alap_gongyolt'])})")
            print(f"  TBJ   göngyölt: {ft(r['tbj_gongyolt'])}  ->  negyedéves: {ft(r['tbj_eloleg'])}")
            print(f"  SZOCHO göngyölt: {ft(r['szocho_gongyolt'])}  ->  negyedéves: {ft(r['szocho_eloleg'])}"
                  f"   (határidő: {r['tb_hatarido'] or 'nincs az adónaptárban'})")
        print()
    if last:
        print(f"Eddig keletkezett kötelezettség ({last['negyedev']}. negyedév végéig göngyölve"
              f"{', a negyedév még folyamatban' if last['allapot']=='folyamatban' else ''}):")
        print(f"  SZJA: {ft(last['szja_gongyolt'])}")
        if last["tbj_gongyolt"] is not None:
            print(f"  TBJ: {ft(last['tbj_gongyolt'])}   SZOCHO: {ft(last['szocho_gongyolt'])}")
        else:
            print("  TBJ / SZOCHO: NEM SZÁMOLHATÓ (hiányzó beállítás)")
    if lim["idoaranyos"]:
        print(f"Időarányos bevételi határ: {ft(lim['eves_hatar'])} × {lim['aktiv_napok']}/{lim['ev_napjai']} nap = {ft(limit)}")
    print(f"Bevételi határ kihasználtsága: {ft(ytd)} / {ft(limit)} = {ratio*100:.2f}%")
    print(f"Adómentes keret kihasználtsága: {mentes_ratio*100:.2f}%")
    for name, thr in (("🔴", rules["figyelmeztetes_kuszob_piros"]), ("🟡", rules["figyelmeztetes_kuszob_sarga"])):
        if ratio >= D(thr):
            print(f"{name} A bevételi határ elérte a {D(thr)*100:.0f}%-ot!")
            break
    print("\nFigyelmeztetések / nem ellenőrzött pontok:")
    for w in warns:
        print(f"- {w}")
    print(f"\nMentve: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

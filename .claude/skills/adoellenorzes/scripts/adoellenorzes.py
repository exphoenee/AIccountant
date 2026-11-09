#!/usr/bin/env python3
"""Adó-ellenőrzés: kiállított számlák -> keletkezett kötelezettség, összevetve a NAV adószámlával és az adónaptárral.

Használat:
    python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py                    # az aktuális adóévre: előbb frissít, aztán ellenőriz
    python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py 2026               # a megadott adóévre (pl. 2026)
    python -I .claude/skills/adoellenorzes/scripts/adoellenorzes.py --nincs-frissites  # frissítés nélkül (offline / teszt)

Futás előtt a többi skill scriptjével beszerzi a friss adatot:
  1. szamlak      – Billingo számlák és bejövő számlák (kiadások) lekérése az év elejétől az év végéig (ha nem sikerül, a meglévő adattal dolgozik,
                    és ezt kiírja)
  2. adonaptar    – új naptárfájl feldolgozása az input/adonaptar/ mappából (ha van)
  3. adofizetes   – új NAV-kivonat feldolgozása az input/nav-egyenleg/ mappából (ha van); a NAV-kivonatot a
                    felhasználónak kell letöltenie és bemásolnia, azt a script nem tudja lekérni
  4. adoszamitas  – kötelezettség kiszámítása a friss adatokból
Ezután összeveti az adónaptárral: elmaradás / eltérés / közelgő határidő / következő kötelezettség.
Kimenet: képernyő + data/szamitas/ellenorzes_<év>.json + HTML adóreport (skill: adoreport) minden futás végén
Minden szám a fenti scriptek kimenetéből vagy a NAV-tételekből származó egyszerű összegzés; nincs becslés
(.claude/rules/nincs-becsles.md). Új, feldolgozatlan fájlokat ez a script nem dolgoz fel – azt a megfelelő skill végzi.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys as _sys; _sys.path.insert(0, str(ROOT / ".claude" / "scripts")); import konfig  # noqa: E402
SK = ROOT / ".claude" / "skills"
PY = [sys.executable, "-I"]


def ft(n) -> str:
    return f"{int(n):,}".replace(",", " ") + " Ft"


def run(cmd, label):
    r = subprocess.run(PY + cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        print(f"HIBA ({label}):\n{(r.stderr or r.stdout).strip()}")
        sys.exit(1)
    return r.stdout


def try_run(cmd):
    r = subprocess.run(PY + cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode == 0, (r.stdout if r.returncode == 0 else (r.stderr or r.stdout)).strip()


def latest(glob_dir: Path, pattern: str, key=None):
    files = list(glob_dir.glob(pattern))
    if not files:
        return None
    return max(files, key=key or (lambda p: p.stat().st_mtime))


def jel(days: int) -> str:
    return "🔴" if days <= 7 else ("🟡" if days <= 30 else "🟢")


def account_credit(nav, kod, upto: str):
    """Az adónem tételeiből: jóváírás (+) / tartozás (−) a megadott napig. = −(Σ előírás + Σ pénzforgalom)."""
    ad = next((a for a in nav["adonemek"] if a["kod"] == kod), None)
    if ad is None:
        return None
    elo = sum(t["eloiras"] for t in ad["tetelek"]
              if t["eloiras"] is not None and t["kotelezettseg_datum"] and t["kotelezettseg_datum"] <= upto)
    pf = sum(t["penzforgalom"] for t in ad["tetelek"]
             if t["penzforgalom"] is not None and t["teljesites_datum"] and t["teljesites_datum"] <= upto)
    return -(elo + pf)


def nav_elo(nav, kod, datum):
    ad = next((a for a in nav["adonemek"] if a["kod"] == kod), None)
    if ad is None:
        return None
    v = [t["eloiras"] for t in ad["tetelek"]
         if t["kotelezettseg_datum"] == datum and t["eloiras"] is not None
         and "negyedéves bevallás" in (t["kotelezettseg_megnevezes"] or "")]
    return sum(v) if v else None


def has_item(nav, kod, datum, szoveg):
    ad = next((a for a in nav["adonemek"] if a["kod"] == kod), None)
    return bool(ad) and any(t["kotelezettseg_datum"] == datum and szoveg in (t["kotelezettseg_megnevezes"] or "")
                            for t in ad["tetelek"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Számlák – adókötelezettség – NAV – adónaptár összevetése.")
    ap.add_argument("--nincs-frissites", action="store_true",
                    help="nem frissít (nincs Billingo-lekérés, nincs új fájl feldolgozás); offline vagy teszt")
    ap.add_argument("--config", help="teszteléshez: másik vallalkozas.json")
    ap.add_argument("ev", nargs="?", type=int, help="az adóév, pl. 2026 (alapból az aktuális év)")
    ap.add_argument("--ma", type=date.fromisoformat, default=date.today(), help="teszteléshez")
    a = ap.parse_args()
    today = a.ma
    # KAPU: a vállalkozás feldolgozott adatai nélkül (memória-profil) az ellenőrzés nem fut le
    prof = ROOT / ".claude" / "memory" / "vallalkozasi-profil.md"
    n_tenyek = 0
    if prof.exists():
        txt = prof.read_text(encoding="utf-8")
        if "Igazolt tények száma: " in txt:
            num = txt.split("Igazolt tények száma: ")[1].split("**")[0].strip()
            n_tenyek = int(num) if num.isdigit() else 0
    # a profil a jelenlegi vállalkozáshoz tartozik-e: a generáláskor a data/vallalkozas/ alatt profil.json és azonosito.json is keletkezik
    # (nem verziózott); egy másik gépről/repóból átvett memóriafájl ezek nélkül nem nyitja ki a kaput
    vdata = ROOT / "data" / "vallalkozas"
    kapu_hiany = []
    if not (vdata / "profil.json").exists():
        kapu_hiany.append("data/vallalkozas/profil.json (a --profil futás eredménye)")
    try:
        az_ok = bool(json.loads((vdata / "azonosito.json").read_text(encoding="utf-8")).get("adoszam"))
    except Exception:
        az_ok = False
    if not az_ok:
        kapu_hiany.append("data/vallalkozas/azonosito.json (a vállalkozás azonosítója: vallalkozas-dokumentumok --billingo)")
    if n_tenyek >= 1 and kapu_hiany:
        print("🔴 LEÁLLT: a memória-profil nem ehhez a vállalkozáshoz tartozik, vagy a feldolgozás nem fejeződött be. Hiányzik: " + "; ".join(kapu_hiany))
        print("   Ne másolj át profilt másik repóból: futtasd a vallalkozas-dokumentumok skillt a saját iratokon. Részletek: usage.md.")
        sys.exit(2)
    if n_tenyek < 1:
        print("🔴 LEÁLLT: nincs feldolgozott vállalkozói profil a memóriában (.claude/memory/vallalkozasi-profil.md).")
        print("   Az adóellenőrzés csak a vállalkozás feldolgozott adatai után futhat. Előbb:")
        print("   1. másold az iratokat az input/ alatti 'v…adatok' mappába,")
        print("   2. futtasd a vallalkozas-dokumentumok skillt: --leltar, --konvertal, --terv, --vegrehajt, majd a profil-tenyek.json kitöltése után --profil.")
        print("   Részletek: usage.md.")
        sys.exit(2)
    cfg_path = Path(a.config) if a.config else konfig.vallalkozas_ut()
    cfgd = json.loads(cfg_path.read_text(encoding="utf-8"))
    # A kapu nem csak azt nézi, hogy a profil létrejött, hanem hogy a kötelező kérdésekre (kamara, kedvezmények, IPA-hely) van-e válasz:
    # ezek nélkül az ellenőrzés hiányos állításokat tenne (pl. a kamarai hozzájárulás nem szerepelne a kötelezettségek között).
    if not a.config:
        valasz_hiany = [t for t, ok in (("kamarai hozzájárulás: köteles-e (dokumentumok.py --kamara igen|nem)", cfgd.get("kamara_koteles") is not None),
                                        ("adó- és járulékkedvezmények (dokumentumok.py --kedvezmeny nincs | ...)", cfgd.get("kedvezmenyek") is not None),
                                        ("iparűzési adó illetékességi helye (dokumentumok.py --ipa-beallit \"<település>\")", bool(cfgd.get("ipa_telepules")))) if not ok]
        if valasz_hiany:
            print("🔴 LEÁLLT: a vállalkozói profil kötelező kérdései közül hiányzik válasz: " + "; ".join(valasz_hiany) + ".")
            print("   A skill a profilkészítéskor megkérdezi ezeket (usage.md 2.7–2.8); válasz nélkül az ellenőrzés hiányos állításokat tenne.")
            sys.exit(2)
    ev = a.ev or today.year
    # Az "indulás előtti" határidők csak a vállalkozás ELSŐ napja előtt nem relevánsak. A vallalkozas_kezdete a jelenlegi jogviszony (újraindulás)
    # kezdete: az az előtti határidők (előző évi bevallás, kamara, korábbi negyedévek) egy régebbi vállalkozásnál is érvényesek lehetnek.
    start = date.fromisoformat(cfgd["vallalkozas_elso_napja"]) if cfgd.get("vallalkozas_elso_napja") else         (date.fromisoformat(cfgd["vallalkozas_kezdete"]) if cfgd.get("vallalkozas_kezdete") else None)

    refresh = []
    if a.nincs_frissites:
        refresh.append("🟡 Frissítés kihagyva (--nincs-frissites): a meglévő adatból dolgozom.")
    else:
        # számlaforrások: minden lépés csendben kimarad, ha nincs kulcs / nincs új fájl; azonosító-eltérés (4) és keresztvalidálási
        # ellentmondás (5) esetén a futás megáll, mert hibás adatból nem szabad adót számolni
        def lepes(cimke, script, *args, vegzetes=(4, 5)):
            r = subprocess.run(PY + [str(SK / script)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            szoveg = (r.stdout or "").strip() or (r.stderr or "").strip()
            if r.returncode in vegzetes:
                print(f"🔴 {cimke}: a futás megáll.{chr(10)}{szoveg}")
                sys.exit(r.returncode)
            if r.returncode != 0:
                refresh.append(f"🔴 {cimke}: NEM sikerült, a meglévő adattal dolgozom: " + (szoveg.splitlines()[-1] if szoveg else "ismeretlen hiba"))
            elif szoveg and not szoveg.startswith(("Nincs feldolgozand", "Az input/")):
                refresh.append(f"✅ {cimke}: " + szoveg.splitlines()[0])
                for extra in szoveg.splitlines()[1:6]:
                    if extra.startswith(("🔴", "ℹ️", "❓", "=", "+")):
                        refresh.append("   " + extra)

        def env_van(nev):
            try:
                for sor in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
                    if sor.startswith(nev + "="):
                        return bool(sor.split("=", 1)[1].strip().strip("\"'"))
            except OSError:
                pass
            return False
        refresh.append("Bevételi források: Billingo: " + ("kulcs beállítva" if env_van("BILLING_API_KEY") else "🟡 NINCS kulcs (kihagyva)")
                       + "; Számlázz.hu: " + ("kulcs beállítva" if env_van("SZAMLAZZ_API_KEY") else "🟡 NINCS kulcs (kihagyva)")
                       + "; fájlok (input/bevetelek, archive/bevetelek): " + ("van" if any((ROOT / d).glob("**/*")
                                                                                  for d in ("archive/bevetelek",) if (ROOT / d).exists()) else "nincs")
                       + ". Ha ennél több forrásból vannak bevételeid, a hiányzó forrás bevétele nem szerepel a számításban.")
        tol_, ig_ = f"{ev - 1}-01-01", f"{ev}-12-31"
        lepes("Billingo számlák", "szamlak/scripts/billingo_szamlak.py", tol_, ig_)
        lepes("Bejövő számlák (Billingo)", "szamlak/scripts/billingo_kiadasok.py", tol_, ig_)
        lepes("Számlázz.hu számlák", "szamlak/scripts/szamlazz_szamlak.py", tol_, ig_)
        lepes("Bevételi fájlok (input/bevetelek)", "szamlak/scripts/bevetelek.py", "--feldolgoz", vegzetes=(4,))
        lepes("Számlák egyesítése és keresztvalidálása", "szamlak/scripts/szamlak_egyesites.py")
        lepes("Számlák megfelelősége (Áfa tv.)", "szamlak/scripts/szamla_ellenorzes.py", vegzetes=())
        lepes("Kiadási számlák (input/kiadasok)", "kiadasok-dokumentumok/scripts/kiadasok.py", "--feldolgoz", vegzetes=(4,))
        lepes("Könyvelői iratok (input/konyvelo)", "konyvelo-dokumentumok/scripts/konyvelo.py", "--feldolgoz", vegzetes=(4,))
        lepes("NAV-bevallások (PDF)", "adofizetes/scripts/bevallasok.py", vegzetes=(4,))
        ok, out = try_run([str(SK / "adonaptar" / "scripts" / "adonaptar.py")])
        refresh.append("Adónaptár: " + (out.splitlines()[0] if ok else "🔴 HIBA: " + out.splitlines()[0]))
        ok, out = try_run([str(SK / "adofizetes" / "scripts" / "nav_egyenleg.py"), "--ma", str(today)])
        if ok:
            proc = [l for l in out.splitlines() if l.startswith(("Feldolgozva", "Archiválva", "HIBA", "Nincs új"))]
            refresh += ["NAV-kivonat: " + l for l in proc] or ["NAV-kivonat: nincs új feldolgozási üzenet"]
        else:
            refresh.append("🔴 NAV-kivonat feldolgozása sikertelen: " + out.splitlines()[-1])
    extra = ["--config", a.config] if a.config else []
    run([str(SK / "adoszamitas" / "scripts" / "adoszamitas.py"), "--csendes", "--ev", str(ev), "--ma", str(today)] + extra, "adószámítás")
    run([str(SK / "adofizetes" / "scripts" / "nav_egyenleg.py"), "--jelentes", "--ma", str(today)], "NAV adószámla")

    sz = json.loads((ROOT / "data" / "szamitas" / f"adoszamitas_{ev}.json").read_text(encoding="utf-8"))
    navp = latest(ROOT / "data" / "nav-egyenleg", "nav_egyenleg_*.json",
                  key=lambda p: json.loads(p.read_text(encoding="utf-8"))["lekerdezes"])
    nav = json.loads(navp.read_text(encoding="utf-8"))
    cal_p = ROOT / "data" / "adonaptar" / f"{ev}.json"
    if not cal_p.exists():
        sys.exit("HIBA: nincs feldolgozott adónaptár; futtasd az 'adonaptar' skillt.")
    cal = json.loads(cal_p.read_text(encoding="utf-8"))
    rep_p = latest(ROOT / "data" / "nav-egyenleg", f"jelentes_{navp.stem.replace('nav_egyenleg_', '')}.json")
    rep = json.loads(rep_p.read_text(encoding="utf-8"))
    pay_checks = {r["kod"]: {c["hatarido"]: c for c in r["hatarido_ellenorzes"]} for r in rep["adonemek"]}
    qrows = {r["negyedev"]: r for r in sz["negyedevek"]}
    nav_tol, nav_ig = nav["idoszak"]["tol"], nav["idoszak"]["ig"]
    nav_ok = nav_tol <= f"{ev}-01-01" and nav_ig[:4] >= str(ev)  # a NAV-kivonat az adóév elejétől tart-e
    miss = sz["hianyzo_beallitasok"]

    print(f"== Adó-ellenőrzés – {ev} (állapot: {today}) ==")
    print("-- Adatfrissítés")
    for l in refresh:
        print(f"   {l}")
    print(f"Számlaadat:  {sz['szamlak_forras']} ({sz['szamlak_kora_ora']/24:.1f} napos)")
    print(f"NAV kivonat: {navp.name} (lekérdezés: {nav['lekerdezes'].replace('T', ' ')[:16]}, időszak: {nav_tol} – {nav_ig})")
    if not nav_ok:
        print(f"🔴 A NAV-kivonat ({nav_tol} – {nav_ig}) nem fedi az {ev}. adóévet: a befizetések és az előírások ellenőrzése nem végezhető el. Tölts le {ev}. évi adószámla-kivonatot (input/nav-egyenleg/).")
    print(f"Adónaptár:   {cal_p.relative_to(ROOT)}")
    stale = []
    if sz["szamlak_kora_ora"] > 24:
        stale.append("számlaadat >1 napos")
    if (today - date.fromisoformat(nav["lekerdezes"][:10])).days >= 1:
        stale.append("NAV kivonat >1 napos")
    if stale:
        print(f"🟡 Elavulhat az adat ({', '.join(stale)}): tölts le újat, mielőtt döntesz.")
    print()

    findings, upcoming, all_items, pre_start = [], [], [], 0
    print("-- Határidők állapota")
    for r in cal["tetelek"]:
        D = r["datum"]
        diff = (date.fromisoformat(D) - today).days
        if start and date.fromisoformat(D) < start:
            # A vállalkozás indulása (config: vallalkozas_elso_napja, ennek hiányában vallalkozas_kezdete) előtti határidő: nem releváns, nem ellenőrizzük és nem jelezzük.
            pre_start += 1
            all_items.append({"datum": D, "adonem": r["adonem"], "teendo": r["teendo"].replace("**", ""), "tipus": r["tipus"],
                              "nap": diff, "jel": "–", "szint": "indulas_elott",
                              "uzenetek": [f"A vállalkozás indulása ({start.isoformat()}) előtti határidő: nem releváns."]})
            continue
        label = f"{D}  [{r['adonem']}] {r['teendo'].replace('**', '')}"
        t, q = r["tipus"], r.get("negyedev")
        item = {"datum": D, "teendo": r["teendo"], "tipus": t}
        msgs, level = [], None
        if not nav_ok and diff < 0 and t in ("szja_eloleg", "tb_szocho", "szja_bevallas"):
            msgs.append(f"A NAV-kivonat ({nav_tol} – {nav_ig}) nem fedi az {ev}. évet: nem ellenőrizhető.")
            level = "nem_ellenorizheto"
        elif t in ("szja_eloleg", "tb_szocho") and q and q["ev"] == ev and q["negyedev"] in qrows:
            row = qrows[q["negyedev"]]
            partial = row["allapot"] == "folyamatban"
            tag = " (a negyedév még folyamatban – az eddigi adatokkal számolt érték, változhat)" if partial else ""
            if t == "szja_eloleg":
                cum = row["szja_gongyolt"]
                msgs.append(f"számított göngyölt SZJA: {ft(cum)}, negyedéves előleg: {ft(row['szja_eloleg'])}{tag}")
                if diff < 0 and not partial:
                    cr = account_credit(nav, "103", D)
                    if cum == 0:
                        level = "ok"; msgs.append("számított előleg-kötelezettség nincs")
                    elif cr is not None and cr >= cum:
                        level = "ok?"
                        msgs.append(f"az adószámlán a határidőre {ft(cr)} jóváírás állt (≥ göngyölt {ft(cum)}); "
                                    "azt, hogy a NAV ezt előlegként elszámoltnak veszi, nem tudom ellenőrizni")
                    else:
                        level = "hiba"
                        msgs.append(f"az adószámlán a határidőre {ft(cr or 0)} jóváírás állt; a göngyölt számított SZJA-hoz "
                                    f"hiányzik {ft(cum - (cr or 0))}")
            else:  # tb_szocho
                if row["tbj_eloleg"] is None:
                    level = "nem_szamolhato" if diff < 0 else None
                    msgs.append(f"NEM SZÁMOLHATÓ – hiányzó beállítás: {', '.join(miss)}")
                else:
                    msgs.append(f"számított TBJ: {ft(row['tbj_eloleg'])}, SZOCHO: {ft(row['szocho_eloleg'])}{tag}")
                    if diff < 0 and not partial:
                        n_tb, n_sz = nav_elo(nav, "406", D), nav_elo(nav, "258", D)
                        problems = []
                        for nm, comp, navv in (("TBJ", row["tbj_eloleg"], n_tb), ("SZOCHO", row["szocho_eloleg"], n_sz)):
                            if navv is None and comp > 0:
                                problems.append(f"{nm}: számított {ft(comp)}, de nincs negyedéves bevallás-előírás a NAV adószámlán")
                            elif navv is not None and navv != comp:
                                problems.append(f"{nm}: számított {ft(comp)} ≠ NAV előírás {ft(navv)} (eltérés {ft(abs(comp - navv))}); okát nem tudom megállapítani")
                            else:
                                msgs.append(f"{nm}: NAV előírás {'nincs, számított 0' if navv is None else ft(navv)} – egyezik")
                        for kod, nm in (("406", "TBJ"), ("258", "SZOCHO")):
                            c = pay_checks.get(kod, {}).get(D)
                            if c and c["allapot"] != "rendben":
                                problems.append(f"{nm} befizetés: {c['allapot']}"
                                                + (f" ({c['keses_nap']} nap késés)" if c.get("keses_nap") else "")
                                                + (f", hiány {ft(c['hiany'])}" if c.get("hiany") else ""))
                            elif c:
                                msgs.append(f"{nm} befizetés a határidőig: rendben")
                        level = "hiba" if problems else "ok"
                        msgs += problems
        elif t in ("szja_eloleg", "tb_szocho") and q:
            # nem az aktuális év negyedéve: csak a NAV-ból ellenőrizhető
            kods = ("103",) if t == "szja_eloleg" else ("406", "258")
            cs = [pay_checks.get(k, {}).get(D) for k in kods]
            cs = [c for c in cs if c]
            if diff < 0 and cs:
                bad = [c for c in cs if c["allapot"] != "rendben"]
                level = "hiba" if bad else "ok"
                msgs.append("NAV befizetés-ellenőrzés: " + ("; ".join(c["allapot"] for c in bad) if bad else "rendben")
                            + f" ({q['ev']}. {q['negyedev']}. negyedév; számlából nem számolom)")
            elif diff < 0:
                msgs.append(f"{q['ev']}. {q['negyedev']}. negyedév: nem ellenőrizhető (nincs számított adat, a NAV-kivonatban nincs ehhez tétel)")
        elif t == "szja_bevallas":
            if diff < 0:
                if has_item(nav, "103", D, "Éves bevallás"):
                    msgs.append("a NAV adószámlán szerepel 'Éves bevallás' tétel erre a napra (a beadást ez jelzi, de nem hivatalos igazolás)")
                    level = "ok?"
                else:
                    msgs.append("nincs 'Éves bevallás' tétel az adószámlán erre a napra; azt, hogy beadtad-e, nem tudom megállapítani")
                    level = "nem_ellenorizheto"
        else:
            if diff < 0:
                msgs.append("nem ellenőrizhető: ehhez nincs adat a repóban (nem NAV-adószámlás tétel)")
                level = "nem_ellenorizheto"
        sym = ({"ok": "✅", "ok?": "✅?", "hiba": "🔴", "nem_szamolhato": "❓", "nem_ellenorizheto": "❓"}.get(level, "❓")
               if diff < 0 else jel(diff))
        all_items.append({"datum": D, "adonem": r["adonem"], "teendo": r["teendo"].replace("**", ""), "tipus": t,
                          "nap": diff, "jel": sym, "szint": level, "uzenetek": msgs})
        if diff < 0:
            print(f"{sym} {label}  (lejárt {-diff} napja)")
            for m in msgs:
                print(f"     {m}")
            if level in ("hiba", "nem_szamolhato"):
                findings.append({**item, "szint": level, "uzenetek": msgs})
        elif diff <= 60:
            print(f"{jel(diff)} {label}  ({diff} nap múlva)")
            for m in msgs:
                print(f"     {m}")
            upcoming.append({**item, "nap": diff, "jel": jel(diff)})
    if pre_start:
        print(f"({pre_start} határidő a vállalkozás indulása ({start.isoformat()}) előtt van: nem releváns, kihagyva.)")
    print()

    # következő kötelezettség
    nxt = next((r for r in cal["tetelek"] if r["tipus"] in ("szja_eloleg", "tb_szocho")
                and date.fromisoformat(r["datum"]) >= today), None)
    next_block = None
    print("-- Következő adófizetési kötelezettség")
    if not nxt:
        print("Nincs több negyedéves határidő az adónaptárban.")
    else:
        D = nxt["datum"]
        q = nxt["negyedev"]
        row = qrows.get(q["negyedev"]) if q and q["ev"] == ev else None
        print(f"Határidő: {D} ({(date.fromisoformat(D) - today).days} nap múlva)")
        if not row:
            print("Erre a negyedévre nincs számított adat.")
        else:
            tag = "a negyedév még folyamatban; az eddigi adatokkal számolt, végleges érték csak a negyedév lezárása után" \
                if row["allapot"] == "folyamatban" else "lezárt negyedév"
            print(f"({q['negyedev']}. negyedév – {tag})")
            now = today.isoformat()
            cr103 = account_credit(nav, "103", now)
            cr258, cr406 = account_credit(nav, "258", now), account_credit(nav, "406", now)
            need_szja = max(0, row["szja_gongyolt"] - (cr103 or 0))
            print(f"  SZJA: göngyölt számított {ft(row['szja_gongyolt'])}; adószámla jóváírás ma: {ft(cr103 or 0)}"
                  f" -> még fedezetlen: {ft(need_szja)}  (negyedéves előleg a számítás szerint: {ft(row['szja_eloleg'])})")
            next_block = {"hatarido": D, "szja_fedezetlen": need_szja}
            if row["tbj_eloleg"] is None:
                print(f"  TBJ / SZOCHO: NEM SZÁMOLHATÓ – hiányzó beállítás: {', '.join(miss)}")
            else:
                need_tb = max(0, row["tbj_eloleg"] - (cr406 or 0))
                need_sz = max(0, row["szocho_eloleg"] - (cr258 or 0))
                print(f"  TBJ:    számított negyedéves {ft(row['tbj_eloleg'])}; adószámla jóváírás ma: {ft(cr406 or 0)} -> még fizetendő: {ft(need_tb)}")
                print(f"  SZOCHO: számított negyedéves {ft(row['szocho_eloleg'])}; adószámla jóváírás ma: {ft(cr258 or 0)} -> még fizetendő: {ft(need_sz)}")
                print(f"  Összesen a három adónemre, a fedezetlen részek összege: {ft(need_szja + need_tb + need_sz)}")
                next_block.update(tbj_fizetendo=need_tb, szocho_fizetendo=need_sz,
                                  osszesen=need_szja + need_tb + need_sz)

    if sz["kintlevo_szamlak"]:
        print(f"\n-- Kintlévő számlák (nem bevétel, amíg nincs kifizetve): {len(sz['kintlevo_szamlak'])} db")
        for k in sz["kintlevo_szamlak"]:
            print(f"   {k['szamlaszam']}  kelt {k['kelt']}, fizetési határidő {k['fizetesi_hatarido']}")
    bh = sz["bevetel_hatar"]
    print(f"\nBevételi határ kihasználtsága: {ft(bh['bevetel'])} / {ft(bh['hatar'])} = {float(bh['kihasznaltsag'])*100:.2f}%")
    print(f"Adómentes keret kihasználtsága: {float(sz['adomentes_keret_kihasznaltsag'])*100:.2f}%")

    print()
    kok, kout = try_run([str(SK / "konyvelo-dokumentumok" / "scripts" / "konyvelo.py"), "--ellenoriz", str(ev)])
    print(kout.strip() if kout else "❓ A könyvelői ellenőrzés nem futott le.")
    k_hibak = sum(1 for l in (kout or "").splitlines() if "🔴" in l)

    print("\n-- Összegzés")
    if k_hibak:
        print(f"🔴 Könyvelői ellenőrzés: {k_hibak} eltérés / igazolatlan bevallás (lásd fent).")
    # lejárt, de NEM ellenőrizhető tételek (régi NAV-kivonat, IPA, kamara, éves bevallás, nem NAV-adószámlás tételek): ezekről nem állítjuk, hogy rendben vannak
    nem_ell = [x for x in all_items if x["szint"] in ("nem_ellenorizheto", "nem_szamolhato") and x["nap"] < 0]
    if findings:
        print(f"🔴 {len(findings)} elmaradás / eltérés / nem számolható tétel – lásd fent.")
    if nem_ell:
        print(f"❓ {len(nem_ell)} lejárt határidő NEM ellenőrizhető a repó adataiból; ezekről nem állítom, hogy rendben vannak:")
        for x in nem_ell:
            print(f"   ❓ {x['datum']} [{x['adonem']}] {x['teendo']}")
    if not findings and not nem_ell:
        print("Nem találtam elmaradást: minden lejárt határidő ellenőrizve volt.")
    elif not findings:
        print("Bizonyított elmaradást nem találtam, de ez csak az ellenőrizhető tételekre igaz (lásd a ❓ sorokat).")
    for u in upcoming:
        if u["nap"] <= 30:
            print(f"{u['jel']} {u['datum']}: {u['teendo'].replace('**', '')} ({u['nap']} nap)")
    print("\nNem ellenőrzött / ismert korlátok:")
    for w in sz["figyelmeztetesek"]:
        print(f"- {w}")
    print("- Az adónaptár IPA, kamarai és egyéb tételeit nem tudom a repó adataiból ellenőrizni.")
    # az input/ alatt maradt, FELDOLGOZATLAN fájlok (az input/ feldolgozás után üres kell legyen: adatkezeles.md); az ok a skill üzenetében van
    import bemenet
    maradek = bemenet.maradek(ROOT / "input")
    maradek.pop("vallalkozas-adatok", None)  # a vállalkozói iratokat a vallalkozas-dokumentumok skill külön, kérdések után rendezi
    print("\n-- Feldolgozatlan fájlok az input/ alatt")
    if maradek:
        for mappa, m in maradek.items():
            print(f"🟡 input/{mappa}/: {m['db']} fájl ({', '.join(f'{k}={v}' for k, v in m['tipusok'].items())})"
                  + (f"; ebből {m['nem_tamogatott']} nem támogatott formátum (támogatott: {', '.join(m['tamogatott_kiterjesztesek'])})" if m["nem_tamogatott"] else "")
                  + ": futtasd a megfelelő skillt, és olvasd el az üzenetét (azonosító-eltérés, ismeretlen irattípus vagy ellentmondás miatt maradhat itt)")
    else:
        print("✅ Az input/ mappák üresek (minden feldolgozódott).")
    out = {"ev": ev, "datum": today.isoformat(), "szamitas": f"adoszamitas_{ev}.json", "nav": navp.name,
           "talalatok": findings, "kozelgo": upcoming, "kovetkezo_kotelezettseg": next_block,
           "hataridok": all_items, "frissites": refresh, "konyvelo_hibak": k_hibak, "feldolgozatlan_input": maradek}
    p = ROOT / "data" / "szamitas" / f"ellenorzes_{ev}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nMentve: {p.relative_to(ROOT)}")

    # bevételi nyilvántartás (Szja tv. 51. § (3)) az egyesített számlákból
    ok, bout = try_run([str(SK / "adoszamitas" / "scripts" / "bevetel_nyilvantartas.py"), "--ev", str(ev), "--ma", str(today)])
    print("\n-- Bevételi nyilvántartás")
    print(bout.splitlines()[0] if ok and bout else f"🔴 A bevételi nyilvántartás elkészítése NEM sikerült: {bout.splitlines()[-1] if bout else 'ismeretlen hiba'}")

    # minden futás után: HTML adóreport (skill: adoreport)
    ok, rout = try_run([str(SK / "adoreport" / "scripts" / "adoreport.py"), "--ev", str(ev)])
    print("\n-- Adóreport")
    print(rout.splitlines()[-1] if ok and rout else f"🔴 A report elkészítése NEM sikerült: {rout.splitlines()[-1] if rout else 'ismeretlen hiba'}")


if __name__ == "__main__":
    main()

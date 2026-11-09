# Jogi nyilatkozat (DISCLAIMER)

Ez a repó **nem helyettesíti a könyvelőt, az adótanácsadót és a jogi szakértőt**. Ez egy nyomkövető és figyelmeztető eszköz: a vállalkozás törvényi és számviteli ügyeit **követi**, és **kérdéseket vet fel** a könyvelő és a jogi képviselő felé. A döntés, a bevallás és a jogi értelmezés az ő, illetve a te felelősséged.

## Mit csinál az eszköz
- **Követ:** a számlákból, a NAV adószámlából, az adónaptárból és a vállalkozás iratai alapján nyilvántartja a bevételt, a keletkezett adót és járulékot, a határidőket, a befizetéseket és a nyitott teendőket.
- **Figyelmeztet:** jelzi a közelgő és lejárt határidőket, az eltéréseket (számított összeg és NAV-előírás között), a hiányzó adatot és a számlák esetleges hibáit.
- **Kérdéseket vet fel:** a törvényszövegben vagy a hivatalos tájékoztatókban ellentmondó, homályos vagy nem eldönthető pontokat külön listázza (`data/szamitas/konyvelo_kerdeslista.md`, a report Tennivalók szakasza), törvényi hellyel, hogy a könyvelő vagy a NAV dönthessen.

## Amit az eszköz nem csinál
- **Nem ad adótanácsot, jogi véleményt vagy könyvelői szolgáltatást.** A kimenete tájékoztató jellegű munkaanyag, nem szakvélemény.
- **Nem dönt jogértelmezési kérdésekben.** Ahol a törvény és a NAV-tájékoztató ellentmond, vagy a szöveg nem mond ki valamit (pl. a 89%-os szabály alkalmazhatósága, a minimális járulékalap típusa, az időarányosítás nevezője, az összesítő nyilatkozat vonatkozása), az eszköz a kérdést felveti, de **nem válaszolja meg**.
- **Nem készít és nem ad be bevallást**, nem fizet, nem módosít számlát a számlázóprogramban (a Billingo-kapcsolat csak olvasási), és nem küld semmit a NAV-nak.
- **Nem ellenőrzi a jogosultság feltételeit.** A kedvezmények számítása a megadott jogosultsági hónapokkal és eltartottakkal számol; hogy a jogosultság fennáll-e, és az adóbevalláshoz szükséges nyilatkozatok megvannak-e, a te felelősséged.
- **Nem ellenőrzi a számlák nyomtatott tartalmát.** A számlamegfelelőségi ellenőrzés a számlázóprogram adatait vizsgálja; a „figyelmeztetés” nem jogi minősítés.

## Korlátok, amelyeket ismerned kell
- **Adóév és hatály:** az eszköz a **2026-os adóévre** készült. Az évente változó értékek (minimálbér, költséghányad, kedvezmények összegei, űrlapkódok) a `config/szabalyok_<év>.json`-ban vannak; új évhez ezeket hivatalos forrásból kell frissíteni. A jogszabályok módosulhatnak: a letöltött szövegek hatályos állapotát a `torvenytar/**/*.forras.json` rögzíti.
- **Jogforrások:** a törvényszövegek az njt.hu-ról és a net.jogtar.hu-ról gépiesen kerültek letöltésre, és a szabályfájlok hivatkozásait a repó automatikusan csak a szakasz **meglétére** ellenőrzi, a tartalmi egyezésre nem. Nem minden vonatkozó jogszabály van letöltve.
- **Az AI hibázhat.** A számításokat Python scriptek végzik, nem az AI, de az AI értelmezi a feladatot, olvassa az iratokat és fogalmazza a magyarázatot. Az AI tévedhet, félreérthet iratot, vagy hibásan kapcsolhat össze szabályokat. A Graphify tudásgráf egyes élei következtetések (INFERRED/AMBIGUOUS), nem tények.
- **Bizonytalan esetben** a válasz mindig az, hogy kérdezd meg a könyvelődet vagy a NAV-ot. Amit az eszköz nem tud, azt kimondja („NEM SZÁMOLHATÓ”, „nem ellenőrzött”), és nem becsül.
- **Adatvédelem:** amit az AI beolvas, azt a modellszolgáltató is megkapja; lásd a [README.md](README.md) figyelmeztetését. Ha ezt nem vállalod, ne használd az eszközt személyes iratokkal.

## Felelősség
- Az adóügyi döntésekért, a bevallások pontosságáért és határidőre való beadásáért, a befizetésekért és a nyilatkozatokért **te** (illetve a könyvelőd és a jogi képviselőd) felelsz, nem az eszköz és nem a készítői.
- Az eszköz **„ahogy van”** alapon áll rendelkezésre, kifejezett vagy hallgatólagos garancia nélkül (a pontosságra, teljességre, naprakészségre vagy bármely konkrét célra való alkalmasságra sem). A használatából eredő adóelőny vagy -hátrány, bírság, késedelmi pótlék vagy egyéb kár miatt a készítők nem vállalnak felelősséget.
- A kimenetet bevallás vagy befizetés előtt mindig vesd össze a hivatalos forrásokkal (NAV, adószámla, hatályos jogszabály), és egyeztesd a könyvelővel.

## Hogyan használd helyesen
1. Használd **munkaanyagnak és emlékeztetőnek**: mikor mi esedékes, mi hiányzik, mi tér el.
2. A nyitott kérdéseket (`konyvelo_kerdeslista.md`, a report Tennivalói) **vidd el a könyvelőhöz vagy a jogi képviselőhöz**, és a választ rögzítsd (`jogi_kerdesek.py --rogzit`).
3. Új adóév, jogszabály-módosítás vagy változott élethelyzet (indulás, szünetelés, jogállás, TB-státusz) esetén **előbb egyeztess a könyvelővel**, és frissítsd a beállításokat.
4. A jelentés és a számítás eredményét ne tekintsd végleges adónak, amíg a könyvelő nem erősítette meg.

## Licenc
A repó saját kódja és dokumentációja MIT licenc alatt áll, lásd a [LICENCE.md](LICENCE.md) fájlt (a harmadik féltől származó részek kivételével). A licenc „ahogy van” és garancia nélküli jellege a fenti felelősségi szabályokkal együtt értendő.

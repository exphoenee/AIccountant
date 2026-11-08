# Átalányadózó egyéni vállalkozó – könyvelés és szoftver (jegyzetek)

> Háttéranyag, nem adószabály-forrás. A szabályokat lásd: `atalanyado-szabalyok-osszefoglalo.md` és `.claude/rules/`.

## Átalányadózó egyéni vállalkozó könyvelőprogramja

Egy átalányadózó egyéni vállalkozó konyveloprogramjának elsősorban az **egyszeres könyvvitel**, a bevétel- és költségnyilvántartás, az áfa, valamint az átalányadó miatti szja- és járulékfeladatok támogatására kell alkalmasnak lennie. A legfontosabb, hogy a program ne kényszerítsen teljes (kettős) könyvvitelt, hanem az egyszeres könyvviteli nyilvántartásokat kezelje.

### Alapvető követelmények

- **Egyszeres könyvvitel vezetése:** bevételi és kiadási napló, pénztár- és bankkönyv, készletnyilvántartás, valamint a törvény által előírt egyéb nyilvántartások kezelése.
- **Átalányadós bevételkövetés:** a programnak a vállalkozói bevételt kell alapul vennie, mert az átalányadózásnál a jövedelmet a bevételből a tevékenységtől függő költséghányad levonásával számítják ki; 2026-ban ez általában 45%, 2027-től 50%.
- **Szja-adóelőleg számítás:** az átalányban megállapított jövedelem éves minimálbér-felét el nem érő része adómentes; 2026-ban ez 1 936 800 Ft. A programnak ezt a küszöböt és a felette eső rész adózását is kezelnie kell.
- **Járulék- és szochoz-követés:** a programnak figyelembe kell vennie a vállalkozó TB-státuszát, mert ez határozza meg a járulék- és szociális hozzájárulási adó fizetési kötelezettséget.
- **Áfa-kezelés:** ha a vállalkozó áfa-alany, a programnak kell kezelnie áfafajtákat, áfa-bevallási adatokat, valamint a nettó bevételt kell átalányadó-alapnak tekintenie.
- **Előlegek kezelése:** az átalányadóba beszámító és nem beszámító előlegeket külön kell tudni kezelni.

### Számlázási és adatszolgáltatási funkciók

- **Számla kiállítása és Online Számla adatszolgáltatás:** a programnak NAV-kompatibilis XML-t kell tudnia készíteni és beküldeni.
- **Bevételkönyvelés teljesítés elve alapján:** átalányadózásnál a kiegyenlített bevételek számítanak bevételnek.
- **Bank- és pénztár egyeztetés:** automatikus banki tranzakcióimport, pénztárzárás és egyeztetés.
- **NAV űrlapokhoz / bevallásokhoz adatgyűjtés:** éves szja-bevallás, áfabevallás, esetleges helyi adó és egyéb adókhoz szükséges összesítő adatok.

### Különösen hasznos funkciók

- Tevékenységenkénti költséghányad kezelése.
- Több adózási mód kezelése, például kisadózásból átalányadózásra váltás.
- Családi kedvezmény és egyéb adókedvezmények kezelése.
- Kimutatások: havi/éves átalányadós bevétel, kiszámított jövedelem, adómentes keret kihasználtsága, várható adó és járulék.

### Gyakorlati minimum

1. Egyszeres könyvvitelt vezetni.
2. Számlát kiállítani és online számlát adatszolgáltatni.
3. Áfát kezelni, ha szükséges.
4. Átalányadós bevételt és költséghányad alapján jövedelmet számolni.
5. Szja-adóelőleget, adómentes jövedelemrészt és járulékokat követni.
6. NAV-kompatibilis listákat, exportokat és bevallási alapadatokat készíteni.

---

## Átalányadós pénztárkönyv vezetése

Átalányadózó egyéni vállalkozóként a pénztárkönyvet attól függően kell vezetni, hogy érvényesíted-e az áfa-levonási jogot. Ha **nem érvényesíted**, elegendő a pénztárkönyv **bevételi oldalát** vezetni; ha **áfalevonást érvényesítesz**, a teljes pénztárkönyvet kell vezetni, a kiadásokkal együtt.

### Mikor elég a bevételi oldal?

Ha az átalányadózó EV:

- nem jogosult áfa-levonásra, vagy
- jogosult, de a levonási jogát nem érvényesíti,

akkor csak bevételi nyilvántartást kell vezetnie, amely lényegében a pénztárkönyv bevételi adatait tartalmazza. A költségekről a számlákat és bizonylatokat továbbra is meg kell őrizni.

### Mit tartalmazzon a bevételi nyilvántartás?

Minden vállalkozási bevételt akkor kell bevezetni, amikor a pénz ténylegesen megérkezik — készpénzben vagy bankszámlára. Az átalányadózásnál a bevétel alapja a **kiegyenlített, nettó** bevétel.

| Rovat | Mit írj be? |
|---|---|
| Sorszám | Folyó sorszám |
| Keltezés | A pénz beérkezésének napja |
| Bizonylat | Számla, nyugta, banki kivonat, készpénzátvételi elismervény |
| Ügyfél / teljesítő | Ki fizetett |
| Bevétel jogcíme | pl. szolgáltatás, értékesítés, előleg |
| Nettó összeg | Az átalányadó alapjába tartozó bevétel |
| Áfa | Ha áfa-alany vagy, a számlán szereplő áfa |
| Bruttó összeg | A ténylegesen beérkezett pénz |
| Megjegyzés | Pl. előleg, visszatérítés, különbözet |

### Teljes pénztárkönyv esetén

Ha áfalevonási jogot érvényesítesz, a kiadási oldalon is vezetned kell minden, a vállalkozáshoz kapcsolódó pénzmozgást: anyagbeszerzés, alvállalkozói számla, bérleti díj, rezsi, eszközvásárlás stb.

### Napi és havi gyakorlat

1. **Minden pénzmozgáshoz tartozzék bizonylat:** számla, nyugta, banki tranzakció, készpénz-átvételi elismervény.
2. **Készpénznél** naponta vagy legalább rendszeresen zárj pénztárat: nyitó készpénz + készpénzbevétel − készpénzkiadás = záró készpénz.
3. **Banki bevételeknél** a banki kivonat dátumán és összegén könyvelj, ne a számla kiállítási napján.
4. **Nyugtás értékesítésnél** a napi nyugtaösszesítő alapján könyvelhető az adott nap összesített készpénzbevétele.
5. **Előlegnél** az átalányadóba beszámító és nem beszámító előleget külön kell kezelni.
6. **Hónap végén** ellenőrizd, hogy a könyvelt bevételek egyeznek-e a banki kivonatokkal és a pénztárzárásokkal.

### Egyszerű példa

| Dátum | Bizonylat | Jogcím | Nettó bevétel | Áfa | Bruttó |
|---|---|---|---:|---:|---:|
| 11.06. | Számla 123 | Webfejlesztés | 200 000 Ft | 52 000 Ft | 252 000 Ft |
| 11.10. | Banki kivonat | Ügyfél átutalás | 100 000 Ft | 26 000 Ft | 126 000 Ft |
| 11.15. | Nyugtaösszesítő | Készpénzes értékesítés | 50 000 Ft | 13 000 Ft | 63 000 Ft |

## Könyvelőprogram követelménye

A programnak tudnia kell:

- bevételi nyilvántartást vagy teljes pénztárkönyvet vezetni,
- készpénz- és banki tranzakciókat elkülöníteni,
- áfás és áfa nélküli tételeket kezelni,
- előlegeket külön jelölni,
- napi/havi összesítést és bizonylati visszakeresést biztosítani,
- banki kivonat importálását és egyeztetését támogatni.

---

## Bevételi nyilvántartáshoz ajánlott szoftver

Átalányadózó egyéni vállalkozónak a bevételi nyilvántartáshoz a legegyszerűbb választás egy **online számlázó + egyszerű nyilvántartó**, például **Számlázz.hu Online Könyvelő**. Ha áfalevonást is érvényesítesz, vagy teljes pénztárkönyvet/naplófőkönyvet szeretnél, akkor inkább egy **egyszeres könyvviteli program**, például **Novitax TAXA** jöhet szóba.

### Ajánlott opciók

| Szoftver | Kinek jó? | Erőssége |
|---|---|---|
| **Számlázz.hu Online Könyvelő** | Alanyi adómentes vagy áfás, egyszerű átalányadózó EV | A kiállított számlák és kifizetettség alapján automatikusan készíti a bevételi nyilvántartást és az adókalkulációt. |
| **Számlázz.hu** | Kis volumenű, főleg szolgáltató EV | Számlázás, bevételi nyilvántartás, költségszámlák és áfapozíció egy helyen. |
| **Novitax TAXA** | Áfalevonást érvényesítő, bonyolultabb vagy teljes egyszeres könyvvitelt vezető EV | Pénztárkönyv, naplófőkönyv, bevételi nyilvántartás, áfa-analitika, adószámla és több bevallás elkészítése. |
| **Billingo / Számlázó robot** | Egyszerű, számlázás-központú működés | Gyors számlázás és alapvető bevételkövetés. |

### Mit válassz?

- **Nem érvényesítesz áfalevonást, kevés a számla:** válassz online számlázót, amely automatikusan bevételi nyilvántartást készít.
- **Áfás vagy, és levonod az áfát:** teljes pénztárkönyvre vagy naplófőkönyvre lesz szükséged, ezért egyszeres könyvviteli program a jobb választás.
- **Sok banki tranzakció, készpénz és több ügyfél:** olyan megoldást válassz, amely banki kivonat-importot, pénztárzárást és bizonylat-csatolást is tud.
- **Könyvelővel dolgozol:** kérdezd meg, melyik programot használja ő; a közös rendszer csökkenti az adatátviteli hibákat.

### Minimum funkciók

- Számlánként rögzíteni a **kiegyenlítés dátumát**.
- Nettó bevételt, áfát és bruttó összeget külön kezelni.
- Átalányadó-alapba tartozó és nem tartozó előleget elkülöníteni.
- Havi és éves bevételösszesítést készíteni.
- Átalányadós jövedelmet, adómentes keretet és adóelőleget követni.
- Bizonylatot, számlát vagy banki kivonatot csatolni.

### Gyakorlati ajánlás

Ha most kezded, és főleg számlás szolgáltatásból élsz, indíts **Számlázz.hu Online Könyvelővel** vagy hasonló online megoldással. Ha áfalevonásod van, készpénzforgalmad jelentős, vagy a könyvelőd teljes egyszeres könyvvitelt kér, válaszd a **Novitax TAXA** jellegű egyszeres könyvviteli programot.

---

## Nagyobb, komplexebb könyvelőprogramok

Ha nem csak bevételi nyilvántartót, hanem teljes egyszeres könyvvitelt, több bankot, áfát, készletet, munkaszámokat és könyvelői együttműködést keresel, akkor a **Novitax TAXA**, a **Kulcs-Soft** vagy egy **Contorg Evolut** jellegű program a megfelelőbb.

### Nagyobb, komplexebb opciók

| Szoftver | Mire való? | Miért nagyobb lépték? |
|---|---|---|
| **Novitax TAXA** | Egyéni vállalkozók, egyszeres könyvvitel | Teljes egyszeres könyvviteli rendszer: könyvel, nyilvántart, adózást és beszámolót készít; tanítható könyvelési szabályok, munkaszám- és költséghely-követés is van. |
| **Novitax NTAX** | Nagyobb, moduláris ügyvitel | Tanítható automatikus számlakiegyenlítés, banki események kontírozása és bővíthető kontírozás. |
| **Kulcs-Soft** | Kis- és középvállalkozások | Moduláris egyszeres és kettős könyvelés; átalányadózók és KATA-sok adóbevallásainak elkészítését és beküldését is támogatja. |
| **Contorg Evolut** | Komplexebb egyszeres könyvvitel | Naplófőkönyvi és pénztárkönyvi könyvelést, vállalkozói és nonprofit sémákat is tartalmaz. |
| **Naturasoft Pénztárkönyv / Naplófőkönyv** | Önállóan könyvelő EV-k | Korlátlan bank- és pénztárkezelés, áfabevallás, online számlaletöltés, automatikus évnyitás/zárás. |

### Melyiket válaszd?

- **Ha csak egy lépcsővel nagyobbat akarsz:** **Novitax TAXA** — egyszeres könyvvitel, átalányadózás, áfa, pénztár- és bankkönyv egy rendszerben.
- **Ha több cég, több bank, bonyolultabb áfa vagy könyvelői munkafolyamat van:** **Kulcs-Soft** vagy **Contorg Evolut**.
- **Ha helyi, asztali programot szeretnél, és magad vezeted a pénztárkönyvet:** **Naturasoft Pénztárkönyv**.
- **Ha számlázás és ügyvitel egyben kell:** **Novitax RAXLA-S**.

### Átalányadózó szempontból

Átalányadózó EV-ként a **TAXA** valószínűleg a legjobb „nagyobb” választás: kifejezetten támogatja az átalányadóval adózó egyéni vállalkozókat, és az egyszeres könyvvitel teljes körű nyilvántartásait kezeli.

Ha viszont nincs áfalevonásod és csak bevételi nyilvántartás kell, akkor a nagyobb program felesleges komplexitást hozhat; ilyenkor az online számlázó + automatikus bevételi nyilvántartás továbbra is elég lehet.

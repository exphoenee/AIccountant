# Általános forgalmi adó (Áfa tv.): amit a repó használ

> Forrás: 2007. évi CXXVII. törvény (`torvenytar/afa-tv/2026/2007-evi-cxxvii-torveny.txt`, letöltve 2026-11-08 a `torvenytar/forrasok.json` szerint). A szakaszszámokat a letöltött szövegből vettem.

## Alanyi adómentesség (187–191. §)

1. **187. § (2):** az alanyi adómentesség időszakában az adóalany **adófizetésre nem kötelezett**, **előzetesen felszámított adót nem vonhat le**, és **csak olyan számlát bocsáthat ki, amelyben áthárított adó nem szerepel**. Következmény a repóban: a bejövő számlák ÁFA-ja (pl. a Billingo-előfizetés 27%-a) nem levonható, a bruttó összeg a költség.
2. **188. § (1)–(2):** az alanyi adómentesség akkor választható, ha az összes termékértékesítés és szolgáltatásnyújtás ellenértéke sem az előző naptári évben (ténylegesen), sem a tárgyévben (ésszerűen várhatóan, illetve ténylegesen) nem haladja meg a **20 000 000 Ft**-ot.
3. **2. § a):** az értékhatárba a belföldön, ellenérték fejében teljesített ügyletek számítanak. Az olyan szolgáltatás, amelynek teljesítési helye a 37. § (1) szerint másik tagállam (adóalany megrendelő), **nem belföldi teljesítés**, ezért az értékhatár szempontjából nem belföldi ügylet. Ennek a gyakorlati alkalmazását a könyvelővel kell megerősíteni (nem ellenőrzött).
4. **190. §:** az alanyi adómentességet a tárgy naptári év végéig lehet választani.
5. **191. § (1):** megszűnik az alanyi adómentesség, ha a tárgyévi tényadatok alapján a 188. § (1) b) feltétel nem teljesül (az értékhatár túllépése), vagy ha az adóalany a következő évre nem kívánja alkalmazni.

## Teljesítés helye (37. §)

**37. § (1):** adóalany részére nyújtott szolgáltatás teljesítési helye ott van, ahol a szolgáltatás igénybevevője gazdasági céllal letelepedett. Ezért az uniós (adóalany) megrendelőnek kiállított számlák a magyar áfa hatályán kívül esnek; a Billingo-számlák „Áfa tv. 37. § alapján másik tagállamban teljesített, fordítottan adózó ügylet” megjegyzése erre utal.

## Nyitott pontok

- **Összesítő nyilatkozat:** a szabályra az Áfa tv. szövege a 4/A. számú mellékletre utal (pl. 89/A., 96. §), amelynek szövege a letöltött törvényszövegben **nincs meg**; az adózás rendjéről szóló törvény (Art.) sem szerepel a törvénytárban. Hogy a szolgáltatásnyújtásról (37. §) kell-e és milyen gyakorisággal összesítő nyilatkozat, **nem ellenőrzött**: könyvelő vagy NAV.
- **Közösségi adószám:** uniós ügyfeleknek szóló számlákhoz kell; a megállapítás tényét a vállalkozói profil rögzíti (iratból).
- **A számlázóprogram jelölése:** ha a számlázóprogramban az eladó státusza (`small_taxpayer`) eltér a tényleges ÁFA-státusztól, a program beállítását javítani kell; a `szamla_ellenorzes.py` az ellentmondást jelzi.

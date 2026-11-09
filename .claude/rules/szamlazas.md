# Kimenő számlák megfelelősége (Áfa tv.)

> Forrás: 2007. évi CXXVII. törvény (`torvenytar/docs/afa-tv/2026/2007-evi-cxxvii-torveny.txt`). A szakaszszámokat a letöltött szövegből vettem. Végrehajtás: `.claude/skills/szamlak/scripts/szamla_ellenorzes.py` (önteszt: `teszt_szamla_ellenorzes.py`).

## Mit ellenőriz a script számlánként (a sztornózott számlákat kihagyja)

| Szabály | Törvényi hely | Szint |
|---|---|---|
| Kötelező adattartalom: kelte, sorszám, eladó adószáma, eladó és vevő neve és címe, tétel megnevezése/mennyisége/nettó egységára, az adó mértéke vagy a mentesség jelölése, a teljesítés időpontja | 169. § a)–c), e)–g), i)–j) | hiba, ha hiányzik |
| Vevő adóalanyi minőségének megállapíthatósága: külföldi vevő adószám nélkül nem igazolható adóalanynak (37. § (1)), nem adóalanynál a teljesítési hely az eladónál van (37. § (2)) | 37. § (1)–(2); 169. § d) | figyelmeztetés |
| A jogcím és a vevő országa ellentmond (pl. uniós fordított adózás jogcím nem uniós vevőnél) | 37. §; számlázó-jelölés | hiba |
| Alanyi adómentes eladó számláján nem lehet áthárított adó; alanyi adómentes jelölés és a számlázóprogram eladói státusza ellentmond | 187. § (2) c); 187–188. § | hiba / figyelmeztetés |
| Mentesség vagy hatályon kívüliség esetén jogszabályi hivatkozás vagy egyértelmű utalás | 169. § m) | figyelmeztetés |
| „fordított adózás” kifejezés, ha az adófizetésre a szolgáltatást igénybevevő kötelezett (uniós adóalany megrendelő, 37. §) | 169. § n) | figyelmeztetés (a számlán „fordítottan adózó” is szerepelhet: a törvény pontos kifejezése „fordított adózás”) |
| Időszakonkénti elszámolás (folyamatos teljesítés): a teljesítés időpontja az időszak utolsó napja; ha a fizetési határidő későbbi, a fizetési határidő (legfeljebb az időszak vége utáni 60. nap); ha a kibocsátás és a határidő is az időszak vége előtt van, a kibocsátás napja | 58. § (1), (1a) | figyelmeztetés eltérésnél |
| Fordított adózású szolgáltatás számlája a teljesítés hónapját követő hónap 15. napjáig | 163. § (2) a) | hiba |
| Devizás számlán az átváltási árfolyam megléte (forintra átszámítás a teljesítés/kibocsátás időpontjának árfolyamával) | 80. §; 172. § | hiba, ha hiányzik |

## Korlátok

- A script a **számlázóprogram adatait** vizsgálja (Billingo/Számlázz.hu mezők, megjegyzések), a számla nyomtatott szövegét és a PDF-et nem. A „figyelmeztetés” nem jelent hibát: eltérést vagy ellenőrizendő pontot jelez, amit a könyvelővel kell tisztázni.
- Nem ellenőrzi: a vtsz/TESZOR szám megadását (169. § f)), az árfolyam forrását (80. § (2)), az összesítő nyilatkozatot (4/A. melléklet, Art.: nincs a törvénytárban), a pénzforgalmi elszámolás jelölését (169. § h), csak ha a számlázóprogram jelzi), és a számlák folyamatos sorszámozását.
- Hibás számlát az Áfa tv. 170. § szerinti, számlával egy tekintet alá eső okirattal kell javítani (sztornó, helyesbítő számla); a repó ezt nem készíti el.

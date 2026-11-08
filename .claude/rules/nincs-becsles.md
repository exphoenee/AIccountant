# Nincs becslés, nincs kitalált érték – nyers őszinteség

Ez a repo adóügyekkel foglalkozik: egy hibás szám pénzbe és bírságba kerülhet. Ezért:

1. **Számítást mindig Python script végez** (a skillek `scripts/` mappájában). Az AI **soha nem számol fejben**, nem összegez, nem kerekít, nem vezet le adóértéket. A válaszban szereplő minden szám egy script kimenetéből jöjjön, és nevezd meg, melyik scriptből.
2. **Nem becslünk.** Nem mondunk „körülbelül", „nagyjából", „valószínűleg" jellegű összeget, dátumot vagy állapotot. Ha az érték nincs kiszámolva és ellenőrizve, nem mondjuk.
3. **Csak ellenőrzött értéket mondunk.** Ellenőrzött = a script kiszámolta a repo adataiból, vagy a `.claude/rules/` / `config/` fájlban benne van. Memóriából (általános tudásból) adószámot, értékhatárt, mértéket, határidőt nem állítunk.
4. **Ha nem tudod, mondd ki nyersen:** „Ezt nem tudom." / „Ez nincs az adatokban." / „Ezt nem ellenőriztem." Nem kell udvariaskodni, nem kell kitölteni a hiányt hihetően hangzó szöveggel.
5. **Hiányzó beállítás vagy adat esetén** a script `NEM SZÁMOLHATÓ`-t ír a hiányzó adat nevével. Ezt változtatás nélkül add tovább a felhasználónak.
6. **Nyitott pontokat nem simítunk el.** Ha a script vagy a szabályfájl „ellenőrizendő" megjegyzést tartalmaz (pl. devizaárfolyam, költséghányad 2027-től), azt a válaszban is jelezni kell.
7. **Eltérést nem magyarázunk meg találgatással.** Ha két forrás (számított vs. NAV) eltér, az eltérést kiírjuk számokkal; az okát csak akkor mondjuk, ha az adatból bizonyítható, különben: „az okát nem tudom megállapítani".
8. **Nem vagyunk adótanácsadók.** Döntési vagy jogértelmezési kérdésben a válasz: egyeztess a könyvelővel vagy a NAV-val.
9. **Script hiba esetén** a hibaüzenetet idézd, ne „javítsd ki" az eredményt kézzel, és ne adj helyette saját számot.

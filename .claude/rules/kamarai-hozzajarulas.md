# Kamarai hozzájárulás (egyéni vállalkozó)

> Forrás: 1999. évi CXXI. törvény a gazdasági kamarákról, 34/A. § (`torvenytar/docs/kamarai-tv/2026/1999-evi-cxxi-torveny.txt`). A kamarák 2026. évi tájékoztatói ugyanezt az összeget és határidőt közlik.

## Szabály (a törvényszövegből)

1. **Kötelezett:** a gazdálkodó szervezet, ide értve az egyéni vállalkozót is, **kamarai hozzájárulást fizet** (34/A. § (1)).
2. **Mentesség:** az egyéni vállalkozó nem fizet, ha a vállalkozási tevékenységét **a naptári év teljes időszakában szünetelteti**, és ezt a nyilvántartását vezető területi gazdasági kamarának bejelenti (34/A. § (1)). Ha a tevékenység az év közben folytatódik, a mentesség nem áll fenn.
3. **Összeg:** évi **5 000 Ft** (34/A. § (2)).
4. **Határidő:** a tárgyév **március 31-ig**, az országos gazdasági kamara részére (34/A. § (3)).
5. **Nem fizetés:** a meg nem fizetett hozzájárulás köztartozás, amelyet az adóhatóság adók módjára hajt be (34/A. § (5)).

## Hogyan kezeli a repó

- A vállalkozói profil készítésekor **rá kell kérdezni** a kötelezettségre; a válasz a `config/vallalkozas.json` `kamara_koteles` mezőjébe kerül (`dokumentumok.py --kamara igen|nem`), az összeg és a határidő évente a `config/szabalyok_<év>.json`-ból jön (`kamara_hozzajarulas_ft`, `kamara_hatarido_nap`); a `vallalkozas.json`-beli érték csak akkor érvényes, ha ott kézzel megadták.
- Az `adoszamitas` az `egyeb_fizetendo` listában mutatja; az éves összegbe (szja + tbj + szocho) **külön tételként** kerül, nem az adószámlán.
- A befizetés igazolása (banki bizonylat, kamarai igazolás) a repóban nincs; a `kamara_befizetes_igazolva` jelző addig `false`, és a report tennivalóként jelzi.

## Ellenőrizendő / nyitott pontok

- Az országos gazdasági kamara alapszabálya a fizetés részleteit adja (34/A. § (4)); ezt nem töltöttük le.
- A mentesség feltételeinek teljesülését (teljes éves szünetelés + bejelentés) a repó nem tudja ellenőrizni.

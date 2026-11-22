---
name: segitseg
description: Súgó az AI-eszköz használatához: a docs/ mappa Markdown fájljai, a usage.md, a README.md, a CLAUDE.md, a skillek és a rule-ok tartalmában keres, és ebből válaszol a felhasználó "hogyan használom", "mit hova másoljak", "melyik skillt futtassam", "mit csinál X" jellegű kérdéseire. Használd, ha a kérdés az eszköz működéséről szól, nem konkrét adóadatról.
---

# Súgó (az eszköz használata)

**Kötelező szabályok:** [`.claude/rules/nincs-becsles.md`](../../rules/nincs-becsles.md) és [`.claude/rules/adatkezeles.md`](../../rules/adatkezeles.md). Előbb olvasd el őket.

## Mit csinál

A `scripts/sugo_kereses.py` kulcsszavas keresést végez (csak olvas) ezekben: `docs/**/*.md` (az Archify HTML/JSON diagramokat nem olvassa), `usage.md`, `README.md`, `CLAUDE.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md`. Pontozott találatokat ad `fájl:sor` hivatkozással. A választ te állítod össze ezekből.

## Futtatás

```
python -I .claude/skills/segitseg/scripts/sugo_kereses.py "<a felhasználó kérdése vagy kulcsszavak>" [--max 8]
python -I .claude/skills/segitseg/scripts/sugo_kereses.py --forrasok     # mely fájlokban keres
```

## Munkamenet

1. Futtasd a keresést a kérdés kulcsszavaival (ha kevés a találat, próbálj szinonimákkal, pl. „bemásol" / „hova tegyem").
2. A legjobb találatoknál olvasd el a teljes releváns részt (`Read` a megjelölt fájlon és soron), mielőtt válaszolsz.
3. Válaszolj magyarul, röviden, lépésekkel és pontos parancsokkal, ahogy a forrásban szerepelnek.
4. **Minden állítás mellé írd a forrást** (`usage.md:44`, `.claude/skills/adofizetes/SKILL.md`).
5. Ha a kérdés konkrét adóadatra vagy összegre vonatkozik, ne válaszolj fejből: irányítsd a megfelelő skillhez (`adoellenorzes`, `adoszamitas`, ...), és az futtassa a scriptet.

## Szabályok ehhez a skillhez

- Csak azt mondd, ami a dokumentációban benne van. Ha nincs találat vagy a forrás nem egyértelmű: „ezt nem tudom, a dokumentációban nincs benne".
- Ne találj ki parancsot, kapcsolót vagy mappát; ellenőrizd a forrásban (vagy a script `--help`-jében).
- Jogi/adótanácsadási kérdésben: könyvelő vagy NAV (`nincs-becsles.md` 8. pont).
- A `.env` tartalmát soha ne olvasd ki; személyes adatot ne idézz a `data/` fájlokból.
- Ha a dokumentációk ellentmondanak, mindkettőt idézd, és jelezd az eltérést.

# Törvénytérkép (Graphify tudásgráf)

Generált mappa: a `nav-forrasok` skill állítja elő (`graf_ellenorzes.py`), kézzel ne szerkeszd. A gráf a `torvenytar/docs/` hivatalos jogszabályszövegeiből és NAV-tájékoztatóiból készült; **személyes adatot nem tartalmaz** (csak nyilvános szöveg), ezért verziózott.

Utolsó közzététel: 2026-11-09T09:07:59
- Csomópont: 731, él: 1255; EXTRACTED 651, INFERRED 601, AMBIGUOUS 3.

| Fájl | Tartalom |
|---|---|
| `graph.html` | interaktív gráf (böngészőben nyitható) |
| `graph.json` | a nyers gráfadat (csomópontok, élek, közösségek) |
| `GRAPH_REPORT.md` | a jelentés (központi csomópontok, meglepő kapcsolatok, kérdések) |
| `inferred_ellenorzes.json` | az INFERRED élek szöveges ellenőrzésének eredménye |
| `korpusz-szabalyok.md` | a kinyeréshez használt közös azonosító-szótár és alias-tábla |
| `forras-terkep.json` | a gráf `source_file` mezőjében szereplő korpusz-fájlok megfeleltetése a `torvenytar/docs/` forrásfájloknak |

## Hogyan olvasd
- Az él **EXTRACTED**, ha a hivatkozó szakasz szövege kifejezetten idézi a célt; **INFERRED**, ha a kapcsolat értelmezés; **AMBIGUOUS**, ha bizonytalan. Az INFERRED/AMBIGUOUS élek nem tények: állítás előtt a hivatkozott szakaszt a `torvenytar/docs/` forrásszövegben kell elolvasni (`.claude/rules/nincs-becsles.md`).
- A csomópont-azonosító: `<törvény>_<szakasz>_par` (pl. `szja_tv_29_a_par`), `fogalom_<név>`, `nav_<forrás>`. A törvények rövid nevei: `korpusz-szabalyok.md`.
- A gráf a **törzsszöveget** fedi; a törvények mellékletei (`*.jogtar.txt`) nincsenek benne.
- Frissítés: `python -I .claude/skills/nav-forrasok/scripts/forras_letoltes.py --korpusz`, a Graphify futtatása, majd `--graf-ellenoriz`.

# Tbj-járulék és szociális hozzájárulási adó (szocho) – 2026

> Forrás: `torvenytar/docs/atalanyado-szabalyok-osszefoglalo.md`. Számok: lásd `atalanyado.md`.

## Mértékek

| Státusz | Tbj-járulék | Szocho |
|---|---:|---:|
| Főfoglalkozású vállalkozó | 18,5% | 13% |
| Heti 36 órás munkaviszony vagy nappali tagozatos tanulmányok mellett vállalkozó (`tb_statusz`: `munkaviszony_36_vagy_nappali`) | 18,5% | 13% |
| Nyugdíjas vállalkozó | nincs | nincs |

## Megállapítás

- **Támogatott `tb_statusz` értékek** (`config/vallalkozas.json`): `fofoglalkozasu`, `munkaviszony_36_vagy_nappali`, `nyugdijas`. A 36 órás/nappalis státusznál a NAV tájékoztató 6.2. pontja szerint az alap a göngyölítéssel megállapított összeg; **minimális alapról a forrás nem szól, ezért a script nem számol minimális alapot** (az `adoszamitas` ezt kiírja). Az adómentes keret alatt sincs fizetendő, de a 2658-as bevallás kötelező. Nyugdíjasnál az anyák kedvezményét érvényesítő saját jogú nyugdíjas szochója (NAV 6.3.) nincs kezelve.
- **Szünetelés:** a `szunetelesek` lista napjai kimaradnak a töredékhónapos minimális alapból és az időarányos bevételi határból; hogy a jogállás a szünetelés alatt a járulék szempontjából fennáll-e, nem ellenőrzött (könyvelő / NAV).

- **Negyedévente, göngyölítéssel** kell megállapítani.
- Bevallás és befizetés: a tárgynegyedévet követő hónap **12. napjáig**, negyedéves bevallással (2026-ban 2658-as, a 2025. IV. negyedévre 2558-as). Az érvényes űrlapszámot a feldolgozott adónaptár adja (`data/adonaptar/`).
- **Töredék hónap** (a vállalkozás hónap közben kezdődött vagy szűnt meg): a minimális alapnál naptári naponként a járulékalap **harmincad részét** kell alapul venni (NAV: `torvenytar/docs/NAV/2026/atalanyado-alapveto-szabalyai-2026-02-20.txt`); teljes hónap = a teljes alap.
- **Minimális alap** (főfoglalkozású vállalkozó): havi járulék- és szocho-alap legalább a minimálbér (**322 800 Ft**); középfokú végzettséget/szakképzettséget igénylő személyes főtevékenységnél a garantált bérminimum (**373 200 Ft**).
- Az adómentes 1 936 800 Ft-os jövedelemrész nem képez járulékalapot, de a **minimum alap miatti fizetési kötelezettség ettől függetlenül fennáll**.
- Nyugdíjas vállalkozó nem fizet tbj-t és szochót. Kivétel: az anyák kedvezményét érvényesítő saját jogú nyugdíjas, bizonyos jövedelemhatár felett szochót fizet.

## Gyors számítás (főfoglalkozású, minimális alapon)

| Alap (havi) | Tbj 18,5% | Szocho 13% | Havi összesen |
|---:|---:|---:|---:|
| 322 800 Ft | 59 718 Ft | 41 964 Ft | 101 682 Ft |
| 373 200 Ft | 69 042 Ft | 48 516 Ft | 117 558 Ft |

Negyedéves összeg = havi × 3, ha a tényleges jövedelemarányos alap nem magasabb a minimálisnál. A pontos összeget a NAV egyenleg és a könyvelő erősítse meg.

## Nyitott pont

- A mértékek és a minimális alap értelmezése évente változhat; frissítsd NAV-forrásból. Jogszabály: [Szo. tv. (2018. évi LII.)](https://njt.jog.gov.hu/jogszabaly/2018-52-00-00)

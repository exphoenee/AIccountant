# Bevétel-elszámolás és nyilvántartás átalányadózóként

> Forrás: `torvenytar/atalanyado-szabalyok-osszefoglalo.md`, `torvenytar/konyveles-szoftver-jegyzetek.md`.

## Mi számít bevételnek és mikor?

- Az átalányadózásnál a bevétel alapja a **kiegyenlített, nettó** bevétel.
- A bevételt akkor kell nyilvántartásba venni, amikor a **pénz ténylegesen megérkezik** (bankszámlára vagy készpénzben) – nem a számla kelte vagy teljesítési dátuma számít.
- **Billingo-adatnál** ezért a `paid_date` (kiegyenlítés napja) a mérvadó dátum, és a `payment_status = paid` számlák számítanak bevételnek. A kiállított, de ki nem fizetett számla **nem** része az adott időszak bevételének.
- Devizás számlánál a forintösszeg (`summary.net_amount_local`) a Billingo (számlán alkalmazott) árfolyamával számolt érték. Szja tv. 6. § (2a) a) (`torvenytar/szja-tv/2026/`): ha az áfa-alap külföldi pénznemben kifejezett, az egyéni vállalkozó azt az árfolyamot alkalmazza, amelyet az ügyletben az áfa-alap átszámításához alkalmaz; a 6. § (4) b) pont szerint választhatja az MNB hivatalos árfolyamát is a bevétel megszerzése napját megelőző hónap 15. napján. **Nem ellenőrzött**, hogy külföldi vevős, alanyi adómentes ügyletnél a (2a) a) pont alkalmazandó-e – egyeztess a könyvelővel.
- Előleg: az átalányadóba beszámító és nem beszámító előleget külön kell kezelni.

## Mit kell vezetni?

- Ha **nem érvényesítesz áfalevonási jogot** (alanyi adómentesként sem): elég a **bevételi nyilvántartás** (a pénztárkönyv bevételi oldala). A költségeket nem kell tételesen elszámolni.
- Ha **áfalevonást érvényesítesz**: teljes pénztárkönyv, kiadásokkal együtt.
- A bizonylatokat (számlák, nyugták, banki kivonatok, költségszámlák is) az adó megállapításához való jog elévüléséig meg kell őrizni.

## A bevételi nyilvántartás rovatai

| Rovat | Tartalom |
|---|---|
| Sorszám | folyó sorszám |
| Keltezés | a pénz beérkezésének napja |
| Bizonylat | számla, nyugta, banki kivonat, készpénzátvételi elismervény |
| Ügyfél / teljesítő | ki fizetett |
| Bevétel jogcíme | szolgáltatás, értékesítés, előleg |
| Nettó összeg | az átalányadó alapjába tartozó bevétel |
| Áfa | ha áfa-alany, a számlán szereplő áfa |
| Bruttó összeg | a ténylegesen beérkezett pénz |
| Megjegyzés | előleg, visszatérítés, különbözet |

## Havi gyakorlat

1. Minden pénzmozgáshoz legyen bizonylat.
2. Banki bevételnél a banki kivonat dátumán és összegén könyvelj, ne a számla kiállítási napján.
3. Hónap végén egyeztesd a könyvelt bevételeket a banki kivonatokkal (és ha van, a pénztárzárással).

## Bevétel-követés (amit a figyelmeztetésekhez számolni kell)

- **YTD bevétel** = az adott adóévben `paid_date` szerint beérkezett nettó bevétel (HUF).
- **Átalányos jövedelem** = YTD bevétel × (1 − költséghányad); értékek: `atalanyado.md`.
- **Adómentes keret kihasználtsága** = átalányos jövedelem / 1 936 800 Ft.
- **Bevételi határ kihasználtsága** = YTD bevétel / időarányos határ, ahol az időarányos határ = 38 736 000 Ft × aktív napok / az adóév napjai (Szja tv. 50. § (8); a nevező értelmezése nem ellenőrzött; lásd `atalanyado.md`). Egész éves tevékenységnél a teljes határ.
- Figyelmeztetési szintek: 🟡 80% fölött, 🔴 95% fölött (mindkét keretnél, a határnál különösen, mert átlépésnél visszamenőleges az átalányadózás megszűnése).

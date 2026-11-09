# Határidők és figyelmeztetési szabályok

> A konkrét dátumok forrása: a feldolgozott adónaptár (`data/adonaptar/<év>.json`, olvasható kivonat: `.claude/memory/adonaptar-<év>.md`). A lenti szabályok az értelmezést adják; ütközésnél az adónaptár és a NAV az irányadó.

## Visszatérő határidők

| Teendő | Határidő |
|---|---|
| Szja-adóelőleg (csak ha az átalányos jövedelem meghaladja az adómentes keretet) | negyedévet követő hónap 12. napja |
| Tbj + szocho befizetés és negyedéves bevallás (2658) | negyedévet követő hónap 12. napja |
| Éves szja-bevallás (25SZJA) | tárgyévet követő május 20. |
| Iparűzési adó bevallás (25HIPAK) | május 31. |
| IPA-előleg (hagyományos adóalap, az önkormányzat rendelete szerint) | március 15. és szeptember 15. |
| IPA-előleg (tételes adóalap, Htv. 39/A. §) | az adóév 5. hónapjának utolsó napja (május 31.); csak tételes adózónál (a választás a vállalkozóé, lásd `helyi-ipa` skill) |
| Kamarai hozzájárulás (évi 5 000 Ft; 1999. évi CXXI. tv. 34/A. §, lásd `kamarai-hozzajarulas.md`) | március 31. |

- Ha a határidő **munkaszüneti napra esik, a következő munkanap** a határidő (az adónaptár már így tartalmazza).
- A kamarai és IPA-hatály a vállalkozó helyzetétől függ (hagyományos vs. tételes IPA-adóalap, kamarai kivétel) – ha nem tudod, kérdezd meg a felhasználót.

## Törvényi helyek a határidőkhöz (letöltött szövegből, 2026-11-08)

- Átalányadó-előleg: a negyedévet követő hó **12.** napjáig: Szja tv. 8. számú melléklet 9. pont.
- Negyedéves bevallás (egyéni vállalkozó, Tbj. 6. § (1) d)): a tárgynegyedévet követő hónap **12.** napjáig: Art. 50. § (1a).
- Éves bevallás, bevallási tervezet: az adóévet követő év **május 20.**: Szja tv. 12/C. § (4), (6) (a tervezet kiegészítésének határideje; az átalányadózó önadózik: 8. melléklet 8. pont).
- Összesítő nyilatkozat (uniós, 37. § szerinti szolgáltatásnyújtás): a tárgyhót/tárgynegyedévet követő hónap **20.** napjáig: Áfa tv. 4/A. melléklet I. 2. (a vállalkozóra való vonatkozása nem ellenőrzött).
- A többi határidő (IPA, kamara) forrása a megfelelő szabályfájl; az adónaptár a munkaszüneti nap miatti eltolást már tartalmazza.

## Figyelmeztetési szintek

| Jel | Feltétel |
|---|---|
| 🔴 | lejárt, vagy ≤ 7 nap |
| 🟡 | 8–30 nap |
| 🟢 | 30 nap felett |

## Mit mutass egy figyelmeztetésben?

1. Teendő, adónem, határidő (dátum + hátralévő napok).
2. Várható összeg, ha számolható (tbj/szocho: `jarulek-szocho.md`; szja-előleg: `atalanyado.md` + YTD bevétel), különben „nem számolható, hiányzó adat: …".
3. Fedezet: a legfrissebb feldolgozott NAV-kivonat (`data/nav-egyenleg/`) alapján van-e túlfizetés vagy tartozás.
4. Forrás (adónaptár-sor vagy szabályfájl).

## Szja-előleg logika

- Nincs előleg-kötelezettség, amíg a göngyölített átalányos jövedelem nem éri el az 1 936 800 Ft-ot.
- Az adónaptár „ha már felhasználásra került az adómentes keret" megjegyzése erre utal: negyedévente a göngyölített jövedelemmel kell számolni.

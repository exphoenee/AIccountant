# Határidők és figyelmeztetési szabályok

> A konkrét dátumok forrása: a feldolgozott adónaptár (`data/adonaptar/<év>.json`, olvasható kivonat: `.claude/memory/adonaptar-<év>.md`). A lenti szabályok az értelmezést adják; ütközésnél az adónaptár és a NAV az irányadó.

## Visszatérő határidők

| Teendő | Határidő |
|---|---|
| Szja-adóelőleg (csak ha az átalányos jövedelem meghaladja az adómentes keretet) | negyedévet követő hónap 12. napja |
| Tbj + szocho befizetés és negyedéves bevallás (2658) | negyedévet követő hónap 12. napja |
| Éves szja-bevallás (25SZJA) | tárgyévet követő május 20. |
| Iparűzési adó bevallás (25HIPAK) | május 31. |
| IPA-előleg (normál IPA) | március 15. és szeptember 15. |
| IPA-előleg (sávos IPA) | május 31. (a sávnak megfelelően) |
| Kamarai hozzájárulás (évi 5 000 Ft; 1999. évi CXXI. tv. 34/A. §, lásd `kamarai-hozzajarulas.md`) | március 31. |

- Ha a határidő **munkaszüneti napra esik, a következő munkanap** a határidő (az adónaptár már így tartalmazza).
- A kamarai és IPA-hatály a vállalkozó helyzetétől függ (normál vs. sávos IPA, kamarai kivétel) – ha nem tudod, kérdezd meg a felhasználót.

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

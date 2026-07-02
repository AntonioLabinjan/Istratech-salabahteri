Evo pregledne tablične usporedbe između ova dva načina spremanja i učitavanja modela u PyTorchu, kako bi točno vidio razliku na prvi pogled:

| Značajka | Spremanje samo težina (`state_dict`) + `weights_only=True` | Spremanje CIJELOG modela (`torch.save(model)`) |
| --- | --- | --- |
| **Što se stvarno sprema?** | **Čisto znanje:** Samo tablica s brojevima (težine i pristranosti slojeva). | **Sve živo:** Težine + definicija klase, putanje do datoteka na disku, struktura projekta. |
| **Sigurnost** | 🔒 **Sigurno.** Koristi restriktivni mehanizam koji blokira izvršavanje malicioznog koda. | ⚠️ **Nesigurno.** Koristi standardni `pickle` koji može izvršiti skriveni zlonamjerni kod s interneta. |
| **Prenosivost na drugo računalo** | 🚀 **Odlična.** Radi bilo gdje, pod uvjetom da na tom drugom računalu imaš istu definiciju klase u kodu. | ❌ **Loša.** Često puca ako se struktura mapa ili nazivi skripti na novom računalu razlikuju. |
| **Kako se sprema?** | `torch.save(model.state_dict(), "model.pth")` | `torch.save(model, "model.pth")` |
| **Kako se učitava?** | `model.load_state_dict(torch.load("model.pth", weights_only=True))` | `model = torch.load("model.pth")` |
| **Preporučena praksa?** | **Da**, ovo je industrijski i produkcijski standard. | **Ne**, izbjegavati osim za brze, lokalne eksperimente unutar iste skripte. |

Ukratko, prva opcija ti daje potpunu kontrolu jer odvajaš "mozak" (kod) od "znanja" (brojevi), dok ti druga opcija pokušava olakšati život tako da spremi sve odjednom, ali dugoročno stvara više problema nego koristi.

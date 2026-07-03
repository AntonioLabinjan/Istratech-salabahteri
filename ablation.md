Kada ti modeli narastu i nakrcaju se milijunima (ili milijardama) parametara, ne možeš više od oka pogađati što radi, a što ne. Tu uskače **ablation study** (studija ablacije).

### Što je uopće Ablation Study?

* **Koncept:** Izraz dolazi iz medicine (gdje označava uklanjanje tkiva). U strojnom učenju to znači **namjerno uklanjanje ili mijenjanje jednog po jednog dijela sustava** kako bi se vidjelo koliko se performanse srozaju bez njega.
* **Cilj:** Dokazati da je svaka komponenta tvog modela stvarno korisna i da nisi bezveze trošio resurse i dodavao parametre.

### Glavne vrste ablacije

* **Ablacija značajki (Feature Ablation):** Ovo je upravo ovo što smo ti i ja napravili. Maknuli smo 12 značajki i ostavili samo top 3 da vidimo možemo li srezati model bez prevelikog gubitka točnosti.
* **Ablacija arhitekture (Structural Ablation):** Uklanjanje cijelih slojeva (npr. izbaciš Dropout sloj, smanjiš broj skrivenih neurona sa 64 na 32 ili makneš Attention mehanizam).
* **Ablacija hiperparametara (Hyperparameter Ablation):** Testiranje modela bez specifičnih tehnika optimizacije (npr. treniranje bez Adam optimizatora, bez *learning rate* skchedulera ili bez augmentacije podataka).

### Zašto je to ključno za velike modele?

* **Rezanje troškova (Efficiency):** Ako model bez 2 skrivenih slojeva ima 98% točnosti, a sa svim slojevima 98.1%, ablacija ti jasno kaže: *"Uštedi memoriju i makni te parametre."*
* **Znanstveni dokaz:** Kada pišeš rad ili dokumentaciju za produkciju, ablation study je dokaz da tvoj sustav radi jer je dobro dizajniran, a ne pukom srećom.

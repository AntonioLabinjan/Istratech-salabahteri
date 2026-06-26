# Git šalabahter

## Inicijalizacija

```bash
git init                    # novi repo u trenutnom folderu
git clone <url>             # kopiraj postojeći repo
```

## Status i pregled

```bash
git status                  # što je promijenjeno
git log --oneline           # kratka povijest commitova
git diff                    # što se promijenilo (unstaged)
```

## Add & Commit

```bash
git add ime_fajla.py        # dodaj jedan fajl
git add .                   # dodaj sve promjene
git commit -m "poruka"      # spremi snapshot
git commit -am "poruka"     # add + commit (samo tracked fajlovi)
```

### Životni ciklus fajla

```
Untracked → [git add] → Staged → [git commit] → Committed
Committed → (uredi fajl)  → Modified → [git add] → Staged
```

## Branch

```bash
git branch                  # lista lokalnih grana
git branch nova-grana       # napravi granu
git switch nova-grana       # prebaci se na granu
git switch -c nova-grana    # napravi + prebaci se (skraćeno)
git branch -d nova-grana    # obriši granu (nakon mergea)
```

## Merge

```bash
# Spoji nova-grana u main:
git switch main
git merge nova-grana
```

### Fast-forward vs merge commit

```
Fast-forward (nema divergencije):
main:       A---B
                 \
nova-grana:       C---D
rezultat:   A---B---C---D  ← main se samo pomiče

Merge commit (obje grane imale commitove):
main:       A---B---C
                 \     \
nova-grana:       D---E--M  ← M je merge commit
```

### Conflict

```bash
# Git označi konflikt u fajlu:
<<<<<<< HEAD
kod s main grane
=======
kod s nove grane
>>>>>>> nova-grana

# 1. Ručno uredi fajl
# 2. git add .
# 3. git commit
```

## Remote

```bash
git remote -v                        # lista remoteova
git push origin main                 # pošalji na remote
git pull                             # dohvati + merge
git fetch                            # dohvati bez mergea
```

## .gitignore

```gitignore
# Fajlovi
.env
secret.txt

# Folderi
.venv/
__pycache__/
node_modules/
dist/

# Ekstenzije
*.log
*.pyc

# Iznimka (ne ignoriraj ovaj fajl)
!vazno.log
```

> ⚠ `.gitignore` mora biti committan da vrijedi za sve
> ⚠ Već trackani fajlovi se ne ignoriraju — makni ih s `git rm --cached ime`

## Korisne naredbe

```bash
git restore ime_fajla.py    # vrati fajl na zadnji commit
git restore --staged .      # unstage sve
git stash                   # privremeno spremi promjene
git stash pop               # vrati stash
```

## Tipičan workflow

```bash
git switch -c feature/nova-stvar   # 1. nova grana
# ... radi ...
git add .                          # 2. stage
git commit -m "dodano X"           # 3. commit
git switch main                    # 4. nazad na main
git merge feature/nova-stvar       # 5. spoji
git branch -d feature/nova-stvar   # 6. počisti
```

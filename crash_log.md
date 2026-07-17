# HANDOFF: Debugging rušenja sustava tijekom PyTorch treninga

Datum: 17.7.2026.

## Simptom

Windows se ruši (hard crash / reboot) tijekom pokretanja `train.py` orkestratora
(`main.py`), specifično oko poziva `run_head2_v9_finetune_OPTUNA` (DINOv2 backbone,
odmrznut zadnji blok, Optuna-optimizirani hiperparametri). Trening s 1 epohom prolazi;
problem se manifestira tek kod višeepohalnog treninga.

## Hardver / okruženje

- Laptop, NVIDIA GeForce RTX 5070 Laptop GPU (Blackwell, sm_120), 8GB VRAM, power cap 95W
- Driver 610.74, CUDA UMD 13.3
- PyTorch 2.11.0+cu128, torch.version.cuda=12.8, cudnn 91900, timm 1.0.27
- sm_120 je nativno u `torch.cuda.get_arch_list()` - arhitektura je službeno podržana
- Windows 11, Virtualization Based Security (VBS) / Memory Integrity: bio Running

## Event Viewer nalazi (kronološki)

1. **volmgr Event ID 162** (`\Device\HarddiskVolume3`) - posljedica pada, ne uzrok
2. **Kernel-Power Event ID 41**, BugcheckCode 131073 (dec) = **0x20001 = HYPERVISOR_ERROR**
   - Tipično vezano uz VBS/Hyper-V/WSL2 sloj
3. Nakon isključivanja Memory Integrity (Core Isolation): drugi pad, **BugCheck 0x1E =
   KMODE_EXCEPTION_NOT_HANDLED**, "Caused By Driver: ntoskrnl.exe", parametar 2 = c0000005
   (ACCESS_VIOLATION)
   - Promjena bugcheck koda iz-u-crash je klasičan znak hardverske/driversko nestabilnosti,
     ne deterministički reproducibilan software bug
4. Memory Integrity vraćen ON nakon što isključivanje nije pomoglo (nije bio uzrok)

## Testovi provedeni (kronološki) i rezultati

| # | Test | Podaci | Model/opterećenje | Trajanje/opseg | Rezultat |
|---|------|--------|--------------------|-----------------|----------|
| 1 | `gpu_stress_test.py` - generički CNN stress | random | plain Conv2d CNN, 30 epoha | par minuta, sustavno 100% GPU | ✅ Prošao |
| 2 | Pravi kod, `run_head2_v9_finetune` (ne-Optuna varijanta) | stvarne slike | DINOv2, unfreeze last block | pun trening | ❌ Pad (HYPERVISOR_ERROR) |
| 3 | `SystemMonitor` (psutil + nvidia-smi) integriran u `main.py` | - | - | monitoring alat, ne test | Alat radi, koristi se dalje |
| 4 | Prvi run s monitoringom, `run_head2_v9_finetune_OPTUNA` | stvarne slike | DINOv2 unfrozen, Optuna hiperparametri | do pada (~21s) | ❌ Pad. VRAM skočio 572MB→7854MB/8151MB (96%) baš prije pada |
| 5 | Fix A: proslijeđen `data=(train_data, val_data)` u main.py (izbjegnut dupli load dataseta u RAM) | stvarne slike | isto | - | Primijenjen |
| 6 | Fix B: `compute_relational_feat_stats` batchiran (batch_size=32) umjesto cijeli dataset odjednom | stvarne slike | isto | - | Primijenjen |
| 7 | Ponovni run s oba fixa | stvarne slike | isto | do pada (~12s, RANIJE nego prije) | ❌ Pad. VRAM ovaj put nizak (max 789MB/8151MB=10%), RAM uredan (49%) - **VRAM spike NIJE bio pravi uzrok**, samo koincidencija |
| 8 | `test_dataload_only.py` - SAMO `load_front_back`, bez GPU-a/modela | stvarne slike | nema modela | pun load (11.7s) + 10s cekanja | ✅ Prošao (542 train + 98 val parova, RAM max 49.8%, GPU nedirnut) |
| 9 | `test_dinov2_isolated.py` - provjera verzija + DINOv2 forward/backward | random, batch=16 | DINOv2 (frozen pa unfrozen) | 1 forward + 1 forward+backward | ✅ Prošao. sm_120 nativno podržan, nema arch mismatch |
| 10 | `test_dinov2_large_batch.py` - DINOv2 forward s batch=542 (frozen i unfrozen) odjednom | random, batch=542 | DINOv2 frozen + unfrozen last block, no_grad | 2x forward frozen + 2x forward unfrozen | ✅ Prošao |
| 11 | `test_dinov2_real_images.py` - stvarne slike kroz DINOv2 forward (frozen), + NaN/Inf provjera tenzora | stvarne slike | DINOv2 frozen, no_grad | forward na cijelom train+val setu | ✅ Prošao. Nema NaN/Inf ni u ulaznim ni u izlaznim tenzorima |
| 12 | `test_multi_epoch_flat.py` - puna flat simulacija: stvarne slike, DINOv2 unfrozen last block, pravi optimizer (2 param grupe), pravi OneCycleLR s Optuna hiperparametrima, 40 epoha, print po batchu | stvarne slike | DINOv2 unfrozen, pravi trening petlja | 40 epoha, svi batchevi | ✅ Prošao do kraja bez pada |

## Trenutno stanje

**Svi izolirani testovi prolaze, uključujući punu flat simulaciju pravog treninga (test #12)
sa svim istim komponentama (stvarne slike, pravi backbone, pravi optimizer/scheduler, pravi
hiperparametri, 40 epoha).** Originalni kod (`run_head2_v9_finetune_OPTUNA` pozvan kroz
`_train_generic` u `train.py`, orkestriran iz `main.py`) i dalje uzrokuje pad kad se pokrene
u punom kontekstu main.py (nakon `diagnose_embedding_separability`,
`diagnose_simple_threshold`, frozen DINOv2 dijagnostike, itd.), ali identična logika
izvučena u flat skriptu bez tog konteksta ne pada.

## Isključeno kao uzrok

- Generička GPU/CPU nestabilnost hardvera (prošao dugi stress test)
- Disk/RAM problem kod čistog učitavanja dataseta
- GPU arhitektura/driver ne podržava karticu (sm_120 nativno podržan)
- DINOv2 model sam po sebi nestabilan (prošao izolirano, frozen i unfrozen, mali i veliki batch)
- Veličina batcha (542 odjednom) sama po sebi
- NaN/Inf u stvarnim slikama ili u DINOv2 izlazu na tim slikama
- Broj epoha / OneCycleLR raspored / Optuna hiperparametri sami po sebi (flat 40-epoha
  simulacija identičnih parametara je prošla)
- `backbone_lr_ratio` iz Optuna funkcije - potvrđeno da se uopće ne koristi u
  `_train_generic` (mrtav kod, hardkodiran `cfg.lr * 0.01` za backbone grupu)

## Preostale hipoteze / sljedeći koraci

1. **Razlika je u punom kontekstu main.py, ne u samom treningu.** Test #12 je izolirana
   flat skripta - ne prolazi kroz `diagnose_embedding_separability`,
   `diagnose_simple_threshold` (2x, za convnext i DINOv2), niti drži `backbone`
   (convnext_tiny) i stari `train_data`/`val_data` u memoriji cijelo vrijeme kao originalni
   `main.py`. Vrijedi napraviti test koji **replicira CIJELI redoslijed poziva iz main.py**
   (svi diagnose_* pozivi, oba frozen backbonea učitana i djelomično oslobođena,
   pa tek onda multi-epoha OPTUNA trening) unutar jedne flat skripte s printom po
   koraku - da vidimo je li kumulativni efekt više modela/dijagnostika na GPU-u prije
   treninga taj koji gura sustav preko ruba, ne sam trening.
2. Provjeriti **redoslijed i broj svih `.to(DEVICE)` poziva i je li nešto od
   `backbone`/`dinov2_backbone` iz `main.py` ostalo rezidentno na GPU-u** dulje nego
   je namjera (npr. `backbone` iz main.py se nikad ne `del`-a niti eksplicitno miče s GPU-a
   prije OPTUNA treninga).
3. Ponoviti test #12 flat simulacije, ali **odmah nakon repliciranja diagnose_* poziva
   iz maina** (dodati te pozive na početak flat skripte prije treninga) kako bi se
   preciznije lokaliziralo je li okidač specifično ta kombinacija/redoslijed.
4. Nastaviti koristiti `system_monitor.py` (psutil + nvidia-smi, flush+fsync po
   redu, preživljava hard crash) tijekom svakog daljnjeg testa radi usporedbe
   VRAM/RAM/CPU trendova s točnim Crash Time iz BlueScreenView/Event Viewera.

## Alati napravljeni tijekom debugiranja (svi u repou)

- `system_monitor.py` - pozadinski monitoring RAM/CPU/disk/GPU (psutil + nvidia-smi
  subprocess), flush+fsync po redu, preživljava hard crash
- `gpu_stress_test.py` - generički GPU stress test (plain CNN, random podaci)
- `test_dataload_only.py` - izolirano testiranje `load_front_back` bez GPU-a
- `test_dinov2_isolated.py` - provjera PyTorch/CUDA/arch kompatibilnosti + DINOv2
  forward/backward na malom random batchu
- `test_dinov2_large_batch.py` - DINOv2 forward na velikom (542) random batchu,
  frozen i unfrozen
- `test_dinov2_real_images.py` - DINOv2 forward na stvarnim slikama + NaN/Inf
  provjera tenzora
- `test_multi_epoch_flat.py` - puna flat simulacija pravog treninga (40 epoha,
  stvarni podaci, pravi optimizer/scheduler/hiperparametri)
- `compute_relational_feat_stats_PATCHED.py` - batchirana zamjena za
  `compute_relational_feat_stats` u `train.py` (već primijenjeno)

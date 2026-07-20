import os
import sys
import copy
import time
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from torch.optim.lr_scheduler import OneCycleLR

import torchvision.transforms as T
from tqdm import tqdm

# Lokalni moduli
from dataset import SingleDoubleDataset, FrontBackPairDataset
from metrics import plot_training_curves, _confusion_matrix, plot_confusion
from config import CustomConfig
from model import (
    make_frozen_backbone,
    make_two_tower_backbones,
    unfreeze_last_block,
    DINOV2_BACKBONE_NAME,
    SingleDoubleHead,
    MinimalRelationalHeadV9,

)

# --- GLOBALNE KONSTANTE I KONFIGURACIJE ---
IMG_SIZE = 224

CFG_single_double = CustomConfig()
CFG_front_back = CustomConfig()
CFG_front_back.lr = 1e-4

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[device] koristim: {DEVICE}")

# --- CENTRALIZIRANE TRANSFORMACIJE I NORMALIZACIJE ---
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

# Standardna transformacija za validaciju/test
transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

geometric_transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
])

# V8 fine-tuning (vidi HANDOFF_v2.md): kad se odmrzava zadnji blok backbonea, rizik
# overfittanja na 224 uzorka raste - blaga augmentacija SAMO na trainu (val ostaje
# bez augmentacije da val_acc ostane usporediv s V1-V7).
augmented_transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.RandomRotation(5),
    T.ColorJitter(brightness=0.15, contrast=0.15),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

inv_normalize = T.Normalize(
    mean=[-0.485 / 0.229, -0.456 / 0.224, -0.406 / 0.225],
    std=[1 / 0.229, 1 / 0.224, 1 / 0.225]
)


# --- FUNKCIJE ZA UCITAVANJE PODATAKA ---

def load_single_double(csv_name, cfg: CustomConfig, preview_samples=False):
    """
    Učitava podatke za klasifikaciju jednostranih/dvostranih dokumenata.
    Očekuje CSV datoteku i direktorij 'clean_images' unutar cfg.data_root.
    """
    csv_path = os.path.join(cfg.data_root, csv_name)
    images_dir = os.path.join(cfg.data_root, "clean_images")

    ds = SingleDoubleDataset(csv_path, images_dir, transform=transform)
    imgs = torch.stack([ds[i][0] for i in range(len(ds))])
    labels = torch.stack([ds[i][1] for i in range(len(ds))]).float()

    if preview_samples:
        folder_name = "load_single_double"
        os.makedirs(folder_name, exist_ok=True)

        num_samples = min(5, len(imgs))
        for i in range(num_samples):
            try:
                denorm = inv_normalize(imgs[i])
                denorm = torch.clamp(denorm, 0.0, 1.0)
                pil_img = T.ToPILImage()(denorm)

                label_val = int(labels[i].item())
                filename = f"sample_{i}_label_{label_val}.png"
                pil_img.save(os.path.join(folder_name, filename))
            except Exception as e:
                print(f"[Warning] Greška pri spremanju slike u {folder_name}: {e}")

        print(f"[{folder_name}] Uspješno spremljeno {num_samples} uzoraka u mapu ./{folder_name}/")

    return imgs, labels


def load_front_back(cfg: CustomConfig, preview_samples=False, train_transform=None):
    """
    Učitava parove prednjih i stražnjih strana (front/back).
    Očekuje 'front_back_train.csv', 'front_back_val.csv' i direktorij 'clean_images' unutar cfg.data_root.

    train_transform: ako je zadan, koristi se SAMO za train split (npr. augmented_transform
    za V8 fine-tuning). Val split UVIJEK koristi standardni `transform` bez augmentacije,
    da val_acc ostane usporediv s prijašnjim run-ovima (V1-V7).
    """
    images_dir = os.path.join(cfg.data_root, "clean_images")
    train_csv = os.path.join(cfg.data_root, "front_back_train.csv")
    val_csv = os.path.join(cfg.data_root, "front_back_val.csv")

    #mix_diff_csv = os.path.join(cfg.data_root, "front_back_diff_mix.csv")
    #extra = [mix_diff_csv] if os.path.exists(mix_diff_csv) else None
    ds_train = FrontBackPairDataset(train_csv, images_dir, transform=train_transform or transform,
                                    extra_csv_paths=None)

    ds_val = FrontBackPairDataset(val_csv, images_dir, transform=transform)

    def build(ds):
        fronts = torch.stack([ds[i][0] for i in range(len(ds))])
        backs = torch.stack([ds[i][1] for i in range(len(ds))])
        labels = torch.stack([ds[i][2] for i in range(len(ds))]).float()
        return fronts, backs, labels

    train_data = build(ds_train)
    val_data = build(ds_val)

    if preview_samples:
        folder_name = "load_front_back"
        os.makedirs(folder_name, exist_ok=True)

        train_fronts, train_backs, train_labels = train_data
        num_samples = min(5, len(train_fronts))
        for i in range(num_samples):
            try:
                f_denorm = torch.clamp(inv_normalize(train_fronts[i]), 0.0, 1.0)
                b_denorm = torch.clamp(inv_normalize(train_backs[i]), 0.0, 1.0)

                pil_front = T.ToPILImage()(f_denorm)
                pil_back = T.ToPILImage()(b_denorm)

                w, h = pil_front.size
                combined = Image.new('RGB', (w * 2, h))
                combined.paste(pil_front, (0, 0))
                combined.paste(pil_back, (w, 0))

                label_val = int(train_labels[i].item())
                filename = f"sample_{i}_label_{label_val}.png"
                combined.save(os.path.join(folder_name, filename))
            except Exception as e:
                print(f"[Warning] Greška pri spremanju slike u {folder_name}: {e}")

        print(f"[{folder_name}] Uspješno spremljeno {num_samples} spojenih uzoraka u mapu ./{folder_name}/")

    return train_data, val_data


# --- POMOĆNE FUNKCIJE ---

def stitch_front_back(front, back, save_samples: bool = True):
    """
    prima prednju i stražnju sliku te ih međusobno stitcha za input u model
    """
    half_height = IMG_SIZE // 2

    front_resized = F.interpolate(front, size=(half_height, IMG_SIZE), mode="bilinear", align_corners=False)
    back_resized = F.interpolate(back, size=(half_height, IMG_SIZE), mode="bilinear", align_corners=False)

    combined = torch.cat([front_resized, back_resized], dim=-2)

    if save_samples:
        folder_name = "stitch_front_back"
        os.makedirs(folder_name, exist_ok=True)

        num_samples = min(5, len(combined))
        for i in range(num_samples):
            try:
                clean_tensor = torch.clamp(combined[i], 0.0, 1.0)
                pil_img = T.ToPILImage()(clean_tensor)
                filename = f"stitched_{i}.png"
                pil_img.save(os.path.join(folder_name, filename))
            except Exception as e:
                print(f"[Warning] Greška pri spremanju slike u {folder_name}: {e}")

        print(f"[{folder_name}] Uspješno spremljeno {num_samples} spojenih uzoraka u mapu ./{folder_name}/")

    return combined


def tensor_to_pil(img_tensor: torch.Tensor) -> Image.Image:
    """Denormalize a single (3,H,W) image tensor and convert to a PIL Image."""
    img = img_tensor.detach().cpu() * STD + MEAN
    img = img.clamp(0, 1)
    img = (img.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
    pil_img = Image.fromarray(img)

    folder_name = "tensor_to_pil"
    if not hasattr(tensor_to_pil, "counter"):
        tensor_to_pil.counter = 0
        os.makedirs(folder_name, exist_ok=True)

    if tensor_to_pil.counter < 5:
        try:
            filename = f"sample_{tensor_to_pil.counter}.png"
            pil_img.save(os.path.join(folder_name, filename))
            tensor_to_pil.counter += 1
            if tensor_to_pil.counter == 5:
                print(f"[{folder_name}] Uspješno spremljeno prvih 5 uzoraka u mapu ./{folder_name}/")
        except Exception as e:
            print(f"[Warning] Greška pri spremanju slike u {folder_name}: {e}")

    return pil_img


def save_checkpoint(model, dummy_onnx_inputs, name, cfg: CustomConfig, input_names, output_names):
    os.makedirs(cfg.models_dir, exist_ok=True)

    pth_path = os.path.join(cfg.models_dir, f"{name}.pth")
    torch.save(model.state_dict(), pth_path)
    print(f"[saved] {pth_path}")

    onnx_path = os.path.join(cfg.models_dir, f"{name}.onnx")
    model.eval()
    torch.onnx.export(
        model, dummy_onnx_inputs, onnx_path,
        input_names=input_names, output_names=output_names,
        dynamic_axes={n: {0: "batch"} for n in input_names + output_names},
        opset_version=18,
        dynamo=False,
    )
    print(f"[saved] {onnx_path}")


def compute_relational_feat_stats(backbone, fronts, backs, extra_feats: bool, batch_size: int = 32):
    """
    Izračunaj feat_mean/feat_std na TRAIN setu, jednom, prije treninga.

    IZMJENA (17.7.): forward pass se sad radi u BATCHEVIMA umjesto da se cijeli
    train set (sve slike odjednom) gura kroz backbone u jednom pozivu. Prijasnja
    verzija je znala izazvati nagli skok VRAM-a na skoro 100% (vidi monitor_log.csv,
    17.7. ~10:37) jer je npr. 500+ slika odjednom prolazilo kroz DINOv2 forward
    bez ikakvog batch ogranicenja - sad je to isto ponasanje kao i sam trening loop
    (koji vec koristi DataLoader s cfg.batch_size).

    extra_feats=False -> samo cos_sim (1 broj)
    extra_feats=True  -> cos_sim + L1 + L2 (3 broja)
    """
    def batched_forward(imgs):
        outs = []
        with torch.no_grad():
            for i in range(0, len(imgs), batch_size):
                chunk = imgs[i:i + batch_size].to(DEVICE)
                outs.append(backbone(chunk).cpu())  # odmah natrag na CPU da GPU ne pati
        return torch.cat(outs, dim=0).to(DEVICE)

    ea = nn.functional.normalize(batched_forward(fronts), dim=-1)
    eb = nn.functional.normalize(batched_forward(backs), dim=-1)

    cos_sim = (ea * eb).sum(dim=-1)
    if not extra_feats:
        feats = cos_sim.unsqueeze(-1)
    else:
        l1 = (ea - eb).abs().mean(dim=-1)
        l2 = (ea - eb).pow(2).mean(dim=-1)
        feats = torch.stack([cos_sim, l1, l2], dim=-1)

    feat_mean = feats.mean(dim=0).cpu().tolist()
    feat_std = feats.std(dim=0).cpu().tolist()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return feat_mean, feat_std

"""
Generička trening petlja koja se može izvoditi neovisno o arhitekturi modela
"""
def _train_generic(model, train_inputs, train_labels, val_inputs, val_labels, forward_fn, cfg: CustomConfig, name: str,
                   onnx_dummy_inputs, onnx_input_names, quiet=False, save_artifacts=True, trial=None):
    model = model.to(DEVICE)

    train_loader = DataLoader(TensorDataset(train_inputs, train_labels), batch_size=cfg.batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(val_inputs, val_labels), batch_size=cfg.batch_size, shuffle=False)

    backbone_trainable = any(p.requires_grad for p in model.backbone.parameters())

    # ovisno dali treniramo i backbone ili samo head
    if backbone_trainable:
        opt = torch.optim.Adam([
            {"params": model.backbone.parameters(), "lr": cfg.lr * 0.01},  # Backbone trenira 100x sporije
            {"params": model.head.parameters(), "lr": cfg.lr}  # Glava trenira normalnom brzinom
        ], weight_decay=cfg.weight_decay)
        print(f"[{name}] Optimizator postavljen s diferencijalnim LR (backbone je uključen u trening).")
    else:
        opt = torch.optim.Adam(model.head.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
        print(f"[{name}] Optimizator postavljen samo za glavu (backbone je zamrznut).")

        print(f"=== [SESSION START: {name}] ===")
        for i, param_group in enumerate(opt.param_groups):
            print(f"  -> Param grupa {i}: learning rate = {param_group['lr']}")
        print("===================================\n")

    # --- OneCycleLR: fiksni raspored po batchu, umjesto reaktivnog ReduceLROnPlateau ---
    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * cfg.epochs

    # Vrh OneCycle rasporeda ne mora biti isti kao dosadašnji "fiksni" LR (cfg.lr) -
    # multiplikator dopušta da vrh bude viši (ili niži) od baznog LR-a po param grupi.
    # Ako cfg nema definiran onecycle_max_lr_multiplier, default je 1.0 (staro ponašanje).
    max_lr_multiplier = getattr(cfg, "onecycle_max_lr_multiplier", 1.0)
    max_lrs = [g["lr"] * max_lr_multiplier for g in opt.param_groups]  # zadržava diferencijalni omjer backbone/head

    scheduler = OneCycleLR(
        opt,
        max_lr=max_lrs,
        total_steps=total_steps,
        pct_start=cfg.pct_start,  # % koraka za warmup do max_lr => model lagano uzima zalet
        div_factor=25.0,          # initial_lr = max_lr / div_factor
        final_div_factor=1e4,    # final_lr = initial_lr / final_div_factor
    )
    print(f"[{name}] OneCycleLR max_lr po param grupi: {[f'{lr:.6f}' for lr in max_lrs]} "
          f"(multiplikator={max_lr_multiplier})")

    loss_fn = nn.BCEWithLogitsLoss()

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_val_loss = float('inf')
    best_val_acc, best_train_loss, best_train_acc = 0.0, float('inf'), 0.0
    best_model_state = None
    best_val_logits, best_val_labels = None, None

    print(f"\n--- {name} train/val ---")
    t_start = time.time()
    pbar = tqdm(range(cfg.epochs), desc=name, unit="epoch", file=sys.stdout)

    for epoch in pbar:
        model.head.train()
        if backbone_trainable:
            model.backbone.train()  # odmrznuti blok treba .train() da LayerNorm/DropPath rade ispravno
        train_loss_sum, train_correct, train_total = 0.0, 0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)

            opt.zero_grad()
            logits = forward_fn(model, xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            scheduler.step()  # OneCycleLR se koraci po batchu, ne po epohi

            train_loss_sum += loss.item() * xb.size(0)
            train_correct += ((logits.sigmoid() > 0.5).float() == yb).sum().item()
            train_total += xb.size(0)

        train_loss = train_loss_sum / train_total
        current_train_acc = train_correct / train_total

        model.head.eval()
        if backbone_trainable:
            model.backbone.eval()
        val_loss_sum, val_correct, val_total = 0.0, 0, 0
        all_val_logits, all_val_labels = [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                logits = forward_fn(model, xb)
                loss = loss_fn(logits, yb)
                val_loss_sum += loss.item() * xb.size(0)
                val_correct += ((logits.sigmoid() > 0.5).float() == yb).sum().item()
                val_total += xb.size(0)
                all_val_logits.append(logits)
                all_val_labels.append(yb)

        val_loss = val_loss_sum / val_total
        current_val_acc = val_correct / val_total
        val_logits_epoch = torch.cat(all_val_logits)
        val_labels_epoch = torch.cat(all_val_labels)

        current_lr = opt.param_groups[-1]['lr']

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(current_train_acc)
        history["val_acc"].append(current_val_acc)

        if not quiet:
            pbar.set_postfix(
                train_loss=f"{train_loss:.4f}", train_acc=f"{current_train_acc:.2f}",
                val_loss=f"{val_loss:.4f}", val_acc=f"{current_val_acc:.2f}",
                lr=f"{current_lr:.6f}",
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_val_acc = current_val_acc
            best_train_loss = train_loss
            best_train_acc = current_train_acc
            best_model_state = copy.deepcopy(model.state_dict())
            best_val_logits, best_val_labels = val_logits_epoch, val_labels_epoch

        # Optuna pruning
        if trial is not None:
            trial.report(val_loss, epoch)
            if trial.should_prune():
                import optuna
                pbar.close()
                raise optuna.TrialPruned()

        if not quiet and (epoch % cfg.log_every == 0 or epoch == cfg.epochs - 1):
            avg_epoch_time = (time.time() - t_start) / (epoch + 1)
            eta = avg_epoch_time * (cfg.epochs - epoch - 1)
            tqdm.write(f"epoch {epoch:3d} | train loss {train_loss:.4f} train_acc {current_train_acc:.2f} "
                       f"| val loss {val_loss:.4f} val_acc {current_val_acc:.2f} | lr {current_lr:.6f} | ETA {eta:5.1f}s")

        if train_loss < cfg.early_stop_loss:
            tqdm.write(f"[early stop] epoch {epoch}: train loss {train_loss:.6f} < {cfg.early_stop_loss}")
            pbar.close()
            break

    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        if not quiet:
            print(f"[best model loaded] Best val_loss: {best_val_loss:.4f} | val_acc: {best_val_acc:.2f}")

    if save_artifacts:
        plot_training_curves(history, name, cfg)
        cm = _confusion_matrix(best_val_logits.cpu(), best_val_labels.cpu())
        plot_confusion(cm, name, cfg)
        model = model.cpu()
        save_checkpoint(model, onnx_dummy_inputs, name, cfg, input_names=onnx_input_names, output_names=["logit"])
    else:
        model = model.cpu()

    return {
        "best_val_loss": best_val_loss,
        "best_val_acc": best_val_acc,
        "best_train_loss": best_train_loss,
        "best_train_acc": best_train_acc,
    }


# --- RUN HEAD EXECUTIONS ---

def run_head1(backbone, emb_dim, cfg: CustomConfig, hidden: int = 32, dropout: float = 0.3,
              data=None, trial=None, quiet: bool = False, save_artifacts: bool = True,
              name: str = "head1_single_double", preview_samples: bool = False):
    model = SingleDoubleHead(backbone, emb_dim, hidden=hidden, dropout=dropout)
    if data is None:
        train_imgs, train_labels = load_single_double("sides_count_train.csv", cfg)
        val_imgs, val_labels = load_single_double("sides_count_val.csv", cfg)
    else:
        (train_imgs, train_labels), (val_imgs, val_labels) = data

    if preview_samples:
        folder_name = "run_head1"
        os.makedirs(folder_name, exist_ok=True)
        num_samples = min(5, len(train_imgs))
        for i in range(num_samples):
            try:
                denorm = inv_normalize(train_imgs[i])
                denorm = torch.clamp(denorm, 0.0, 1.0)
                pil_img = T.ToPILImage()(denorm)

                label_val = int(train_labels[i].item())
                filename = f"sample_{i}_label_{label_val}.png"
                pil_img.save(os.path.join(folder_name, filename))
            except Exception as e:
                print(f"[Warning] Greška pri spremanju slike u {folder_name}: {e}")

        print(f"[{folder_name}] Uspješno spremljeno {num_samples} uzoraka u mapu ./{folder_name}/")

    dummy = torch.randn(1, 3, 224, 224)
    return _train_generic(model, train_imgs, train_labels, val_imgs, val_labels,
                          forward_fn=lambda m, x: m(x), cfg=cfg, name=name,
                          onnx_dummy_inputs=(dummy,), onnx_input_names=["image"],
                          quiet=quiet, save_artifacts=save_artifacts, trial=trial)


def diagnose_embedding_separability(backbone, front_imgs, back_imgs, labels):
    with torch.no_grad():
        emb_f = F.normalize(backbone(front_imgs), dim=-1)
        emb_b = F.normalize(backbone(back_imgs), dim=-1)
        cos_sim = (emb_f * emb_b).sum(dim=-1)

    same_sim = cos_sim[labels == 1]
    diff_sim = cos_sim[labels == 0]
    print(f"same-pair cos sim:  mean={same_sim.mean():.3f} std={same_sim.std():.3f}")
    print(f"diff-pair cos sim:  mean={diff_sim.mean():.3f} std={diff_sim.std():.3f}")


def diagnose_simple_threshold(backbone, train_fronts, train_backs, train_labels,
                              val_fronts, val_backs, val_labels):
    device = train_fronts.device

    with torch.no_grad():
        emb_f_tr = F.normalize(backbone(train_fronts), dim=-1)
        emb_b_tr = F.normalize(backbone(train_backs), dim=-1)
        sim_tr = (emb_f_tr * emb_b_tr).sum(dim=-1)

        emb_f_val = F.normalize(backbone(val_fronts), dim=-1)
        emb_b_val = F.normalize(backbone(val_backs), dim=-1)
        sim_val = (emb_f_val * emb_b_val).sum(dim=-1)

    train_labels = train_labels.to(device)
    val_labels = val_labels.to(device)

    best_thr, best_acc = 0.0, 0.0
    thresholds = torch.linspace(sim_tr.min().item(), sim_tr.max().item(), 200, device=device)
    for thr in thresholds:
        acc = ((sim_tr > thr).float() == train_labels).float().mean().item()
        if acc > best_acc:
            best_acc, best_thr = acc, thr.item()

    val_acc = ((sim_val > best_thr).float() == val_labels).float().mean().item()
    print(f"[simple threshold] best_thr={best_thr:.3f} | train_acc={best_acc:.3f} | val_acc={val_acc:.3f}")

import copy  # Koristit ćemo za sigurnu kopiju konfiguracije


def run_head2_v9_finetune(cfg: CustomConfig, backbone_name: str = DINOV2_BACKBONE_NAME,
                          unfreeze: bool = True,
                          data=None, quiet: bool = False, save_artifacts: bool = True,
                          name: str = "head2_v8_finetune"):
    """
    ... (tvoj postojeći docstring) ...
    """
    print("Treninram novi head2 verzija 9 za koji ne znam ča očekujem")
    # 1. NAPRAVI LOKALNU KOPIJU CONFIGA DA NE PREGAZIŠ GLOBALNI CONFIG
    local_cfg = copy.deepcopy(cfg)

    # 2. SMANJI LEARNING RATE I POJAČAJ REGULARIZACIJU AKO SE BACKBONE TRENIRA (unfreeze=True)
    if unfreeze:
        if "dinov2" in backbone_name.lower():
            local_cfg.lr = 3e-5
            local_cfg.weight_decay = 0.05
            if not quiet:
                print(
                    f"[{name}] DETEKTIRAN UNFREEZE DINOv2: Automatski postavljam lr na {local_cfg.lr} i weight_decay na {local_cfg.weight_decay}")
        else:
            local_cfg.lr = 1e-5
            local_cfg.weight_decay = 0.02
    else:
        local_cfg.lr = 1e-3
        local_cfg.weight_decay = 0.01
        if not quiet:
            print(f"[{name}] BACKBONE FROZEN: Postavljam brži lr={local_cfg.lr} za trening glave.")

    # --- Nastavak tvog koda (koristi isključivo local_cfg umjesto cfg) ---
    backbone = make_frozen_backbone(name=backbone_name).to(DEVICE)
    if unfreeze:
        unfreeze_last_block(backbone, backbone_name=backbone_name)
    emb_dim = backbone.num_features

    if data is None:
        # Ovdje također proslijedi local_cfg
        train_data, val_data = load_front_back(local_cfg, train_transform=augmented_transform)
    else:
        train_data, val_data = data

    train_fronts, train_backs, train_labels = train_data
    val_fronts, val_backs, val_labels = val_data

    feat_mean, feat_std = compute_relational_feat_stats(backbone, train_fronts, train_backs, extra_feats=False)
    feat_mean, feat_std = feat_mean[0], feat_std[0]
    print(f"[{name}] backbone={backbone_name} emb_dim={emb_dim} feat_mean={feat_mean:.4f} feat_std={feat_std:.4f}")

    model = MinimalRelationalHeadV9(backbone, emb_dim, feat_mean=feat_mean, feat_std=feat_std)

    train_inputs = torch.stack([train_fronts, train_backs], dim=1)
    val_inputs = torch.stack([val_fronts, val_backs], dim=1)

    def forward_fn(m, xb):
        return m(xb[:, 0], xb[:, 1])

    dummy_front = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    dummy_back = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)

    # Ovdje šaljemo local_cfg umjesto originalnog cfg!
    return _train_generic(model, train_inputs, train_labels, val_inputs, val_labels,
                          forward_fn=forward_fn, cfg=local_cfg, name=name,
                          onnx_dummy_inputs=(dummy_front, dummy_back),
                          onnx_input_names=["front", "back"],
                          quiet=quiet, save_artifacts=save_artifacts)
#######################################################################################################


# ovo trenira model s parametrima koje je optuna odabrala
def run_head2_v9_finetune_OPTUNA(cfg: CustomConfig,
                               backbone_name: str = "convnext_tiny",
                               unfreeze: bool = True,
                               hidden: int = 8,  # Optuna pobjednik: točno 8
                               dropout: float = 0.4534973557017004,  # Optuna pobjednik: ~0.453
                               data=None, quiet: bool = False, save_artifacts: bool = True,
                               name: str = "head2_v9_finetune_best"):
    """
    Puni trening glave v9 s idealnim hiperparametrima koje je pronašla Optuna.
    Automatski premošćuje zadane CustomConfig vrijednosti za LR, weight decay,
    OneCycle scheduler i backbone_lr_ratio.
    """
    if not quiet:
        print(f"[{name}] Pokrećem V9 trening s OPTUNA-OPTIMALNIM parametrima.")
        print(f"[{name}] Parametri: hidden={hidden}, dropout={dropout:.4f}, unfreeze={unfreeze}")

    # 1. NAPRAVI LOKALNU LOKALNU KOPIJU CONFIGA DA NE PREGAZIŠ GLOBALNI
    local_cfg = copy.deepcopy(cfg)

    # 2. UGRAĐIVANJE NAJBOLJIH OPTUNA PARAMETARA U CONFIG
    local_cfg.lr = 0.00028902778257707955  # Optuna pobjednik: ~2.89e-4
    local_cfg.weight_decay = 0.016060924830479502  # Optuna pobjednik: ~0.016
    local_cfg.onecycle_max_lr_multiplier = 14.093715663885279  # Optuna pobjednik: ~14.09
    local_cfg.pct_start = 0.24016521711561428  # Optuna pobjednik: ~0.24
    local_cfg.backbone_lr_ratio = 10.219812107212613  # Optuna pobjednik: ~10.22 (Diferencijalni LR)

    if not quiet:
        print(f"[{name}] Podešene stope učenja: lr={local_cfg.lr:.6f}, weight_decay={local_cfg.weight_decay:.4f}")
        print(f"[{name}] OneCycle postavke: max_lr_mult={local_cfg.onecycle_max_lr_multiplier:.2f}, pct_start={local_cfg.pct_start:.2f}")
        print(f"[{name}] Diferencijalni LR omjer: backbone_lr_ratio={local_cfg.backbone_lr_ratio:.2f}")

    # 3. UČITAVANJE BACKBONE-A
    backbone = make_frozen_backbone(name=backbone_name).to(DEVICE)
    if unfreeze:
        unfreeze_last_block(backbone, backbone_name=backbone_name)
    emb_dim = backbone.num_features

    # 4. UČITAVANJE PODATAKA
    if data is None:
        train_data, val_data = load_front_back(local_cfg, train_transform=augmented_transform)
    else:
        train_data, val_data = data

    train_fronts, train_backs, train_labels = train_data
    val_fronts, val_backs, val_labels = val_data

    # Računanje statistika embeddinga
    feat_mean, feat_std = compute_relational_feat_stats(backbone, train_fronts, train_backs, extra_feats=False)
    feat_mean, feat_std = feat_mean[0], feat_std[0]

    if not quiet:
        print(f"[{name}] backbone={backbone_name} emb_dim={emb_dim} feat_mean={feat_mean:.4f} feat_std={feat_std:.4f}")

    # 5. INICIJALIZACIJA GLAVE V9 S OPTIMIZIRANIM SKRIVENIM SLOJEVIMA I DROPOUT-om
    model = MinimalRelationalHeadV9(
        backbone, emb_dim,
        feat_mean=feat_mean, feat_std=feat_std,
        hidden=hidden, dropout=dropout
    )

    # 6. PRIPREMA INPUTA I INFERENCIJA
    train_inputs = torch.stack([train_fronts, train_backs], dim=1)
    val_inputs = torch.stack([val_fronts, val_backs], dim=1)

    def forward_fn(m, xb):
        return m(xb[:, 0], xb[:, 1])

    dummy_front = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    dummy_back = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)

    # 7. GENERIČKI TRENING (vraća rječnik s poviješću treninga i najboljim val_loss-om)
    # Primijeti: trial=None jer se više ne natječemo, već treniramo "za ozbiljno"
    return _train_generic(model, train_inputs, train_labels, val_inputs, val_labels,
                          forward_fn=forward_fn, cfg=local_cfg, name=name,
                          onnx_dummy_inputs=(dummy_front, dummy_back),
                          onnx_input_names=["front", "back"],
                          quiet=quiet, save_artifacts=save_artifacts,
                          trial=None)


def run_head2_v10_two_tower(cfg: CustomConfig, backbone_name: str = DINOV2_BACKBONE_NAME,
                            data=None, quiet: bool = False, save_artifacts: bool = True,
                            name: str = "head2_v10_two_tower"):
    print("Treniram V10 (two-tower) -> MLP relacijska glava na spojenim embeddingima")
    local_cfg = copy.deepcopy(cfg)

    # 1. AGRESIVNA REGULACIJA PARAMETARA TRENINGA
    if "dinov2" in backbone_name.lower():
        local_cfg.lr = 1e-5  # Smanjeno s 3e-5 (oprezniji koraci)
        local_cfg.weight_decay = 0.15  # Brutalno kažnjavanje overfitta

        if not quiet:
            print(f"[{name}] DINOv2: Smanjen lr na {local_cfg.lr}, WD podignut na {local_cfg.weight_decay}")
    else:
        local_cfg.lr = 5e-6
        local_cfg.weight_decay = 0.10

    # 2. UČITAVANJE PODATAKA (Mora ići prije računanja statistika!)
    if data is None:
        train_data, val_data = load_front_back(local_cfg, train_transform=augmented_transform)
    else:
        train_data, val_data = data

    train_fronts, train_backs, train_labels = train_data
    val_fronts, val_backs, val_labels = val_data

    # 3. INICIJALIZACIJA TORNJEVA
    backbone_front, backbone_back = make_two_tower_backbones(name=backbone_name)

    # OPCIONALNO: Odkomentiraj ako želiš trenirati i backboneove i  MLP glavu
    for p in backbone_front.parameters(): p.requires_grad = False
    for p in backbone_back.parameters(): p.requires_grad = False

    backbone_front = backbone_front.to(DEVICE)
    backbone_back = backbone_back.to(DEVICE)
    emb_dim = backbone_front.num_features



    print(f"[{name}] backbone={backbone_name} (two-tower) emb_dim={emb_dim} ")

    # 5. INICIJALIZACIJA MODELA S MLP GLAVOM
    model = MinimalRelationalHeadV9(
        backbone_front,
        backbone_back,
        emb_dim=emb_dim,

    )

    train_inputs = torch.stack([train_fronts, train_backs], dim=1)
    val_inputs = torch.stack([val_fronts, val_backs], dim=1)

    def forward_fn(m, xb):
        return m(xb[:, 0], xb[:, 1])

    dummy_front = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    dummy_back = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)

    return _train_generic(model, train_inputs, train_labels, val_inputs, val_labels,
                          forward_fn=forward_fn, cfg=local_cfg, name=name,
                          onnx_dummy_inputs=(dummy_front, dummy_back),
                          onnx_input_names=["front", "back"],
                          quiet=quiet, save_artifacts=save_artifacts)

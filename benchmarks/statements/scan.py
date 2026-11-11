"""StatementBench-Scan: image-only versions of the synthetic statements, for the OCR path (R4).

Each page of a StatementBench PDF is rendered to a grey image, degraded with seeded scanner-like noise (slight
rotation, blur, sensor noise, JPEG compression), and written back as an image-only PDF with the same page size.
Gold files are copied unchanged, so the scorer is identical to the text-layer benchmark.

    python -m benchmarks.statements.scan --src benchmarks/statements/data --out benchmarks/statements/data_scan \
        --profile mild

Profiles (per page, uniform within the range):
    mild:  rotation ±0.3°, Gaussian blur radius 0.2–0.6 px, noise σ 3–7, JPEG quality 70–90, 200 dpi
    rough: rotation ±1.0°, blur 0.5–1.0 px, noise σ 6–12, JPEG quality 45–70, 150 dpi
These are generic office-scanner degradations chosen by the developer; they are not calibrated against real scans.
"""
from __future__ import annotations

import argparse
import io
import json
import random
import shutil
from pathlib import Path

PROFILES = {
    "mild": {"rot": 0.3, "blur": (0.2, 0.6), "noise": (3, 7), "jpeg": (70, 90), "dpi": 200},
    "rough": {"rot": 1.0, "blur": (0.5, 1.0), "noise": (6, 12), "jpeg": (45, 70), "dpi": 150},
}


def degrade_pdf(src: Path, dst: Path, profile: str, seed: int) -> dict:
    import numpy as np
    import pypdfium2 as pdfium
    from PIL import Image, ImageFilter

    prof = PROFILES[profile]
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    pdf = pdfium.PdfDocument(str(src))
    images, applied = [], []
    try:
        for page in pdf:
            img = page.render(scale=prof["dpi"] / 72).to_pil().convert("L")
            rot = rng.uniform(-prof["rot"], prof["rot"])
            blur = rng.uniform(*prof["blur"])
            sigma = rng.uniform(*prof["noise"])
            quality = rng.randint(*prof["jpeg"])
            img = img.rotate(rot, resample=Image.BICUBIC, expand=False, fillcolor=255)
            img = img.filter(ImageFilter.GaussianBlur(blur))
            arr = np.asarray(img, dtype=np.int16) + nrng.normal(0, sigma, (img.height, img.width)).astype(np.int16)
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            images.append(Image.open(io.BytesIO(buf.getvalue())).convert("L"))
            applied.append({"rotation_deg": round(rot, 3), "blur_px": round(blur, 3), "noise_sigma": round(sigma, 2),
                            "jpeg_quality": quality})
    finally:
        pdf.close()
    images[0].save(dst, format="PDF", save_all=True, append_images=images[1:], resolution=prof["dpi"])
    return {"profile": profile, "dpi": prof["dpi"], "pages": applied}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default="benchmarks/statements/data")
    ap.add_argument("--out", default="benchmarks/statements/data_scan")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="mild")
    ap.add_argument("--seed", type=int, default=2027)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for gold_path in sorted(src.glob("*.gold.json")):
        sid = gold_path.name[: -len(".gold.json")]
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        info = degrade_pdf(src / f"{sid}.pdf", out / f"{sid}.pdf", a.profile, a.seed + n)
        gold["scan"] = info
        (out / gold_path.name).write_text(json.dumps(gold, indent=1), encoding="utf-8")
        n += 1
    if (src / "manifest.json").exists():
        shutil.copy(src / "manifest.json", out / "manifest.json")
    print(f"wrote {n} scanned statements ({a.profile}) to {out}")


if __name__ == "__main__":
    main()

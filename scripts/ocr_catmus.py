#!/usr/bin/env python3
"""CATMuS Medieval / Kraken HTR for Vatican Vat. lat. 4030 image 0051.

Reads a local scan, an existing PDF from Codespaces, or the Vatican IIIF manifest.
Transcribes the start of Arnaud Gélis's deposition: bottom left, then right column.
Keeps abbreviations UNEXPANDED (graphematic transcription).
"""
import argparse
import hashlib
import json
import subprocess
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw

MANIFEST = "https://digi.vatlib.it/iiif/MSS_Vat.lat.4030/manifest.json"
MODEL_URL = "https://zenodo.org/records/21488839/files/catmus-medieval-1.6.0.mlmodel?download=1"
MODEL_MD5 = "326a6ea675661ec9ce0bb6b1958de495"
# Measured against the Vatican /0051 screenshot. Adjust after inspecting overlay.
REGIONS = {
    "01_left_start": (0.205, 0.555, 0.485, 0.840),
    "02_right": (0.485, 0.087, 0.765, 0.845),
}

def request(session, url):
    response = session.get(url, timeout=(30, 180))
    response.raise_for_status()
    return response

def load_iiif(session, page, width, folder):
    manifest = request(session, MANIFEST).json()
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if "sequences" in manifest:  # IIIF Presentation 2
        canvases = manifest["sequences"][0]["canvases"]
    else:  # IIIF Presentation 3
        canvases = manifest["items"]
    key = f"{page:04d}"
    selected = None
    for canvas in canvases:
        label = canvas.get("label", "")
        if isinstance(label, dict):
            label = " ".join(str(item) for v in label.values()
                             for item in (v if isinstance(v, list) else [v]))
        ident = str(canvas.get("@id", canvas.get("id", "")))
        if key in str(label) or ident.rstrip("/").endswith("/" + key):
            selected = canvas
            break
    if selected is None:
        selected = canvases[page - 1]
        print("No matching canvas label: using ordered canvas", page)
    if "images" in selected:
        body = selected["images"][0]["resource"]
    else:
        body = selected["items"][0]["items"][0]["body"]
        if isinstance(body, list):
            body = body[0]
    service = body.get("service", [])
    if isinstance(service, dict):
        service = [service]
    urls = []
    if service:
        base = service[0].get("@id", service[0].get("id")).rstrip("/")
        urls += [f"{base}/full/{width},/0/default.jpg",
                 f"{base}/full/full/0/default.jpg",
                 f"{base}/full/max/0/default.jpg"]
    direct = body.get("@id", body.get("id"))
    if direct:
        urls.append(direct)
    errors = []
    for url in urls:
        try:
            with Image.open(BytesIO(request(session, url).content)) as im:
                return im.convert("RGB"), "iiif:" + url
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("Unable to fetch IIIF image: " + "; ".join(errors))

def get_image(args, folder, session):
    if args.image:
        with Image.open(args.image) as im:
            return im.convert("RGB"), "file:" + str(args.image)
    for filename in [
        f"Vat_lat_4030/images_2200px/{args.page:04d}.jpg",
        f"Vat_lat_4030/images_full/{args.page:04d}.jpg",
        f"images_2200px/{args.page:04d}.jpg",
    ]:
        if Path(filename).exists():
            with Image.open(filename) as im:
                return im.convert("RGB"), "file:" + filename
    pdf = Path(args.pdf or "Vat_lat_4030/Vat_lat_4030_complete.pdf")
    if pdf.exists():
        import fitz
        with fitz.open(pdf) as document:
            p = args.pdf_page or args.page
            pix = document[p - 1].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            return Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"), f"pdf:{pdf}#page={p}"
    return load_iiif(session, args.page, args.width, folder)

def ensure_model(session, filename):
    filename.parent.mkdir(exist_ok=True, parents=True)
    if filename.exists() and hashlib.md5(filename.read_bytes()).hexdigest() == MODEL_MD5:
        return filename
    print("Downloading CATMuS Medieval model from Zenodo")
    tmp = filename.with_suffix(".partial")
    with session.get(MODEL_URL, timeout=(30, 180), stream=True) as response:
        response.raise_for_status()
        with tmp.open("wb") as out:
            for part in response.iter_content(chunk_size=1024 * 1024):
                if part:
                    out.write(part)
    checksum = hashlib.md5(tmp.read_bytes()).hexdigest()
    if checksum != MODEL_MD5:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Model checksum does not match Zenodo: {checksum}")
    tmp.replace(filename)
    return filename

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Local PNG/JPEG; overrides PDF and IIIF")
    parser.add_argument("--pdf", help="Local original PDF")
    parser.add_argument("--pdf-page", type=int, help="Page number in PDF, starting from 1")
    parser.add_argument("--page", type=int, default=51)
    parser.add_argument("--width", type=int, default=3200)
    parser.add_argument("--out", default="catmus_results/0051")
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--alto", action="store_true", help="Also produce ALTO XML")
    args = parser.parse_args()
    folder = Path(args.out)
    folder.mkdir(exist_ok=True, parents=True)
    session = requests.Session()
    session.headers["User-Agent"] = "VatLat4030-research-HTR/0.1 (non-commercial study)"
    im, provenance = get_image(args, folder, session)
    im.save(folder / "source.jpg", quality=94)
    print("Image:", im.size, "source:", provenance, flush=True)
    qc = im.copy()
    draw = ImageDraw.Draw(qc)
    for name, (x0, y0, x1, y1) in REGIONS.items():
        box = (round(x0*im.width), round(y0*im.height),
               round(x1*im.width), round(y1*im.height))
        draw.rectangle(box, outline="red", width=5)
        im.crop(box).save(folder / (name + ".png"))
    qc.save(folder / "crop_overlay.jpg")
    (folder / "provenance.json").write_text(json.dumps({
        "manuscript": "Biblioteca Apostolica Vaticana, Vat. lat. 4030",
        "image": "0051", "source": provenance, "model": MODEL_URL,
        "important": "Raw graphematic transcription, abbreviations not expanded",
        "regions": REGIONS
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.preview_only:
        print("Saved preview images; recognition not executed.")
        return
    model = ensure_model(session, Path("models/catmus-medieval-1.6.0.mlmodel"))
    sections = []
    for name in REGIONS:
        source = folder / (name + ".png")
        result = folder / (name + ".txt")
        cmd = ["kraken", "-i", str(source), str(result),
               "segment", "-bl", "ocr", "-m", str(model)]
        print("Running:", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
        sections.append(f"### {name}\n" + result.read_text(encoding="utf-8"))
        if args.alto:
            cmd = ["kraken", "-a", "-i", str(source),
                   str(folder / (name + ".alto.xml")),
                   "segment", "-bl", "ocr", "-m", str(model)]
            subprocess.run(cmd, check=True)
    (folder / "transcription_raw.txt").write_text(
        "\n\n".join(sections) + "\n", encoding="utf-8")
    print("Saved", folder / "transcription_raw.txt")
    print("WARNING: human verification required; no expansion of abbreviations.")

if __name__ == "__main__":
    main()

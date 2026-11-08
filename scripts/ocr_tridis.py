#!/usr/bin/env python3
"""One-model pilot: TRIDIS v2 TrOCR on Arnaud Gélis, Vat. lat. 4030 image 0051.

Latin medieval register HTR. Transcribes segmented lines in reading order.
TRIDIS is SEMI-DIPLOMATIC: it normally expands abbreviations. Not a diplomatic
transcription and not a verified edition.

Usage:
  python scripts/ocr_tridis.py [--max-lines 8] [--image /path/to/0051.jpg]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_catmus import load_iiif  # download logic already tested on Vatican 0051

MODEL_ID = "magistermilitum/tridis_v2_HTR_historical_manuscripts"
REGIONS = {
    "01_left_start": (0.245, 0.553, 0.545, 0.812),
    "02_right": (0.565, 0.118, 0.885, 0.814),
}

def alto_lines(xml_path, width, height):
    """Read Kraken's ALTO TextLine bbox coordinates, ignore false tiny fragments."""
    tree = ET.parse(xml_path)
    items = []
    for node in tree.iter():
        if node.tag.rsplit("}", 1)[-1] != "TextLine":
            continue
        try:
            x, y, w, h = (int(node.get(k)) for k in ("HPOS", "VPOS", "WIDTH", "HEIGHT"))
        except (TypeError, ValueError):
            continue
        if w < width * .13 or h < 10:
            continue
        items.append([x, y, w, h])
    return sorted(items, key=lambda r: (r[1] + r[3] / 2, r[0]))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Use a local 0051 image instead of IIIF")
    parser.add_argument("--width", type=int, default=3200)
    parser.add_argument("--out", default="tridis_results/0051")
    parser.add_argument("--max-lines", type=int, default=0,
                        help="For a quick test: 0 = all detected lines")
    parser.add_argument("--beams", type=int, default=2)
    args = parser.parse_args()
    folder = Path(args.out)
    folder.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "VatLat4030-TRIDIS-HTR/0.1 noncommercial historical research"
    if args.image:
        with Image.open(args.image) as image_file:
            original = image_file.convert("RGB")
        provenance = "local:" + args.image
    else:
        original, provenance = load_iiif(session, 51, args.width, folder)
    original.save(folder / "source.jpg", quality=94)
    print("Source:", provenance, "size:", original.size, flush=True)

    preview = original.copy()
    draw = ImageDraw.Draw(preview)
    lines = []
    for region_name, (fx0, fy0, fx1, fy1) in REGIONS.items():
        crop_box = tuple(int(v) for v in (
            fx0 * original.width, fy0 * original.height,
            fx1 * original.width, fy1 * original.height,
        ))
        crop = original.crop(crop_box)
        draw.rectangle(crop_box, outline="#ff0000", width=6)
        crop_file = folder / (region_name + ".png")
        crop.save(crop_file)
        alto_file = folder / (region_name + ".seg.alto.xml")
        subprocess.run(
            ["kraken", "-a", "-i", str(crop_file), str(alto_file),
             "segment", "-bl"],
            check=True,
        )
        segments = alto_lines(alto_file, *crop.size)
        print(region_name, "segmented lines:", len(segments), flush=True)
        for i, (x, y, w, h) in enumerate(segments):
            # These are baseline polygon bounding boxes; pad to retain ascenders,
            # descenders and medieval superscript abbreviation signs.
            left = max(0, x - 9)
            top = max(0, y - 12)
            right = min(crop.width, x + w + 9)
            bottom = min(crop.height, y + h + 12)
            line_im = crop.crop((left, top, right, bottom))
            line_dir = folder / "lines"
            line_dir.mkdir(exist_ok=True)
            name = f"{region_name}_{i:03d}.png"
            line_im.save(line_dir / name)
            lines.append({"region": region_name, "line": i,
                          "image": "lines/" + name,
                          "bbox_region": [x, y, w, h],
                          "bbox_page": [x + crop_box[0], y + crop_box[1], w, h]})
    preview.save(folder / "crop_overlay.jpg")
    if args.max_lines > 0:
        lines = lines[:args.max_lines]
    (folder / "segmented_lines.json").write_text(
        json.dumps(lines, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Processing {len(lines)} lines with {MODEL_ID}", flush=True)

    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig
    torch.set_num_threads(min(4, os.cpu_count() or 2))
    processor = TrOCRProcessor.from_pretrained(MODEL_ID)
    # The upstream TRIDIS v2 config stores max_position_embeddings=514,
    # but its weight is [514, 1024]. TrOCR automatically adds a 2-position
    # offset: 512 + 2 = 514, so correct the metadata without changing weights.
    config = VisionEncoderDecoderConfig.from_pretrained(MODEL_ID)
    config.decoder.max_position_embeddings = 512
    # The published config also says vocab_size=8000 while its saved tensor is
    # [50265,1024]. Follow the author's model card: use tokenizer vocab size.
    config.decoder.vocab_size = processor.tokenizer.vocab_size
    config.vocab_size = processor.tokenizer.vocab_size
    print("Corrected positional embedding size to 512 (+2 offset)", flush=True)
    print("Corrected decoder vocabulary size:", config.decoder.vocab_size, flush=True)
    model = VisionEncoderDecoderModel.from_pretrained(
        MODEL_ID, config=config, low_cpu_mem_usage=True
    )
    model.eval()
    model.to("cpu")
    output_records = []
    for i, line in enumerate(lines):
        with Image.open(folder / line["image"]) as line_image:
            pixel_values = processor(
                images=line_image.convert("RGB"), return_tensors="pt"
            ).pixel_values
        with torch.inference_mode():
            result = model.generate(pixel_values, num_beams=args.beams,
                                    max_new_tokens=150,
                                    early_stopping=True)
        transcription = processor.batch_decode(
            result, skip_special_tokens=True
        )[0]
        line["text"] = transcription
        output_records.append(line)
        if (i + 1) % 5 == 0:
            print(f"Recognized {i+1}/{len(lines)}: {transcription[:90]}", flush=True)
            (folder / "transcription_partial.json").write_text(
                json.dumps(output_records, ensure_ascii=False, indent=2),
                encoding="utf-8")
    (folder / "transcription_lines.json").write_text(
        json.dumps(output_records, indent=2, ensure_ascii=False),
        encoding="utf-8")
    parts = []
    prev_region = None
    for line in output_records:
        if line["region"] != prev_region:
            parts.append(f"\n### {line['region']}\n")
            prev_region = line["region"]
        parts.append(line["text"])
    (folder / "transcription_raw.txt").write_text(
        "\n".join(parts) + "\n", encoding="utf-8")
    (folder / "provenance.json").write_text(
        json.dumps({"manuscript": "Vat. lat. 4030", "image": "0051",
                    "source": provenance, "htr_model": MODEL_ID,
                    "transcription_standard": "semi-diplomatic; abbreviations expanded",
                    "warning": "machine output only, not verified against manuscript",
                    "regions": REGIONS}, indent=2), encoding="utf-8")
    print("COMPLETE:", folder / "transcription_raw.txt", flush=True)

if __name__ == "__main__":
    main()

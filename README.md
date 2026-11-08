# Vatican 4030 PDF Maker — CATMuS handwritten Latin recognition

This repository now includes a **reproducible, one-page pilot** for the manuscript
**Biblioteca Apostolica Vaticana, Vat. lat. 4030**, image **0051**, containing the
beginning of Arnaud Gélis's deposition.

## Running in GitHub Actions (no Codespaces terminal needed)

Open **Actions** → **CATMuS HTR - Vatican 4030 page 0051** → **Run workflow**.
A run on 2026-11-08 was initiated automatically when the workflow was committed.
On completion, open the run and download the artifact \`catmus-4030-0051\`.

The artifact includes:
- \`transcription_raw.txt\`: uncorrected recognition, left lower column followed by right column;
- \`01_left_start.txt\`, \`02_right.txt\`: each cropped section separately;
- \`*.alto.xml\`: ALTO with line position information;
- \`crop_overlay.jpg\`: red rectangles showing which regions were recognized;
- \`source.jpg\`, \`*.png\`, \`provenance.json\`: source and audit materials.

**Important:** The crop boxes were estimated from the Vatican web screenshot.
Look at \`crop_overlay.jpg\` first, then adjust them in
\`scripts/ocr_catmus.py\` if the raw downloaded IIIF page is framed differently.

## Running in your existing GitHub Codespace

First synchronize the committed GitHub code with your Codespace:
\`\`\`bash
git pull
\`\`\`

Then (with Python 3.11+):
\`\`\`bash
python -m pip install "kraken>=6,<7" Pillow requests PyMuPDF
python scripts/ocr_catmus.py --page 51 --alto
\`\`\`

The program **first looks for the pre-downloaded page image** at
\`Vat_lat_4030/images_2200px/0051.jpg\`, then for your existing
\`Vat_lat_4030/Vat_lat_4030_complete.pdf\`. Only if neither is present
does it download page 0051 from the Vatican IIIF server.

Use an explicitly selected image or PDF page when required:
\`\`\`bash
python scripts/ocr_catmus.py --image /path/to/0051.jpg --alto
python scripts/ocr_catmus.py --pdf /path/to/Vat_lat_4030_complete.pdf --pdf-page 51 --alto
\`\`\`

To check crops without installing the model:
\`\`\`bash
python scripts/ocr_catmus.py --image /path/to/0051.jpg --preview-only
\`\`\`

Results are written to \`catmus_results/0051/\` by default.

## Model, source and textual policy

- CATMuS Medieval v1.6.2 Zenodo record, distributing model file
  \`catmus-medieval-1.6.0.mlmodel\`:
  https://doi.org/10.5281/zenodo.21488839
- Recognition engine: https://github.com/mittagessen/kraken
- Manuscript: https://digi.vatlib.it/view/MSS_Vat.lat.4030/0051
- IIIF: https://digi.vatlib.it/iiif/MSS_Vat.lat.4030/manifest.json

CATMuS is **strictly graphematic**: abbreviations and superscripts are
**not silently expanded**. The result is not a critical edition and must be
checked against the original manuscript and Duvernoy's Latin edition.
Do not publicly redistribute the Vatican images without reviewing the
library's terms.

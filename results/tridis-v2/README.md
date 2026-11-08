# TRIDIS v2 pilot: Vat. lat. 4030, image 0051

This folder contains **uncorrected machine HTR output** from TRIDIS v2 TrOCR, not an authoritative transcription.

- Manuscript: Biblioteca Apostolica Vaticana, Vat. lat. 4030, image [0051](https://digi.vatlib.it/view/MSS_Vat.lat.4030/0051)
- Model: [TRIDIS v2 TrOCR](https://huggingface.co/magistermilitum/tridis_v2_HTR_historical_manuscripts)
- Pipeline: `scripts/ocr_tridis.py`, Kraken line segmentation, TRIDIS v2 semi-diplomatic recognition
- Run: [24-line quick pilot](https://github.com/solhector/vatican-4030-pdf-maker/actions/runs/42499429212)
- Input page width: 3200 pixels, two regions; 17 left + 7 right lines in the 24-line pilot
- Decoding: `--max-lines 24 --beams 1`
- Exact raw machine text: [0051_pilot_24_lines.txt](0051_pilot_24_lines.txt)
- Structured line-level coordinates and crops: download the Actions artifact `tridis-v2-0051-quick-24` from the linked run (artifacts are retained for a limited period).

## Interpretation

Transcription quality is not yet validated against a hand-corrected reference.
The model recognizes many complete Latin words and legal formulas, but makes
errors in proper names, morphology, and line segmentation. Examples in the
**uncorrected** output include `Amaldus` for likely `Arnaldus` and
`aminas` for `animas`. Do not cite it as an edition or silently transform
this text into a diplomatic transcription.

TRIDIS v2 is trained to produce semi-diplomatic, abbreviation-expanded
transcriptions. Compare against the manuscript and Jean Duvernoy's Latin
edition before quotation. Model output is preserved separately from any
future editorial corrections.

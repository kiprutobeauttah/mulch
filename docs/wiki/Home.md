# Mulch

Mulch is a self-contained clinical decision-support app for AI-assisted chest X-ray pneumonia screening. It loads a DenseNet121 classifier locally, highlights suspicious regions with Grad-CAM attention heatmaps, and saves every assessment with patient details and structured diagnosis outputs.

All inference runs on-device. No patient data leaves the machine.

## Quick links

- [Installation](Installation)
- [Usage](Usage)
- [Records and storage](Records-and-storage)
- [Screenshots](Screenshots)
- [Sample test X-rays](Sample-test-X-rays)

## Overview

- Screens a chest X-ray for pneumonia and returns a structured diagnosis: NORMAL or PNEUMONIA
- Shows a confidence gauge and class probabilities for both outcomes
- Generates Grad-CAM attention and overlay views to show which regions the model relies on
- Captures patient details (name, MRN, sex, study date)
- Saves every assessment as a record with case images, searchable in the Saved assessments panel
- Lets you choose where records are stored (default: `mulch/records` in the project root)
- Prints a professional A4 report with a letterhead and reviewer signature block

See the [README](https://github.com/kiprutobeauttah/mulch#readme) for badges, license, and build instructions.
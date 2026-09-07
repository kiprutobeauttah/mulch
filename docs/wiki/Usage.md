# Usage

1. Run Mulch (`./run.sh` or the bundled executable).
2. In **New assessment**, enter the patient details (name, MRN, sex, study date).
3. Upload or drop a chest X-ray into the radiograph area.
4. Pick a screening model from the dropdown.
5. Click **Analyze X-ray**.

## Reading the report

- **Diagnosis**: NORMAL or PNEUMONIA, with color-coded badge.
- **Confidence**: gauge showing the confidence of the prediction.
- **Class probabilities**: probability bars for both classes.
- **Model, confidence level, processing time, case ID**: output metrics.
- **Interpretation**: an automatically generated finding statement.
- **X-ray / Attention / Overlay**: toggle between the original radiograph, the Grad-CAM attention map, and the heatmap overlay.

## Saved assessments

Use **Saved assessments** in the sidebar to browse every recorded case. You can search by patient name, open a record to review it, or delete it. Opening a record restores the full structured report including the radiograph and attention views.

## Print report

After an analysis, use **Print report** to generate an A4 document with the letterhead, patient details, diagnosis summary, radiograph, probabilities, interpretation, and a reviewer signature block.
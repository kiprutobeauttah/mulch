# Records and storage

Every analysis is saved automatically with:

- Patient details (name, MRN, sex, study date)
- Diagnosis and confidence
- Probability of NORMAL and PNEUMONIA
- Confidence level
- Interpretation statement
- The screening model used and processing time
- Case images: original X-ray, attention heatmap, and overlay

## Choosing a storage folder

The **Records storage** box at the bottom of the sidebar shows the current storage folder.

- **Change...**: type an absolute path to a new folder and save. The database and all saved case images are migrated to the new location automatically.
- **Use default**: switch back to the default storage folder.

## Default locations

| Build | Default storage |
| --- | --- |
| From source | `mulch/records` inside the project root |
| Bundled release | `~/.mulch` |

The default can also be overridden with the `MULCH_DATA_DIR` environment variable.

## Data layout

```
<storage-folder>/
  mulch.db        SQLite database of all records
  cases/<id>/     per-case images (xray.png, overlay.png, heatmap.png)
```
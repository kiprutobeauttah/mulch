import base64
import io
import logging
import os
import sys

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from PIL import Image

from mulch import records
from mulch.model import MODEL_REGISTRY, CLASS_NAMES, load_models, analyze

if getattr(sys, "frozen", False):
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    RESOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, "mulch", "templates"),
    static_folder=os.path.join(RESOURCE_DIR, "mulch", "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.json.sort_keys = False
log = logging.getLogger("mulch")


@app.route("/")
def index():
    return render_template(
        "index.html",
        models=[
            {"key": key, "label": info["label"], "note": info["note"]}
            for key, info in MODEL_REGISTRY.items()
        ],
        class_names=CLASS_NAMES,
    )


@app.route("/icons/<path:filename>")
def icons(filename):
    return send_from_directory(os.path.join(RESOURCE_DIR, "mulch", "icons"), filename)


@app.route("/cases/<case_id>/<filename>")
def case_file(case_id, filename):
    if filename not in {"xray.png", "overlay.png", "heatmap.png", "xray.jpg"}:
        return jsonify({"error": "Forbidden."}), 403
    return send_from_directory(records.case_dir(case_id), filename)


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "Image is too large (max 16 MB)"}), 413


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e.description)}), 400


@app.errorhandler(500)
def server_error(_e):
    return jsonify({"error": "Something went wrong on the server."}), 500


def _decode_png(data_url: str) -> bytes:
    if not data_url or "," not in data_url:
        return b""
    return base64.b64decode(data_url.split(",", 1)[1])


def _save_case_images(case_id: str, original: bytes, result: dict):
    cover_dir = records.ensure_case_dir(case_id)
    img = Image.open(io.BytesIO(original))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(cover_dir / "xray.png", format="PNG")

    overlay = result.get("attention")
    heatmap = result.get("heatmap")
    if overlay:
        (cover_dir / "overlay.png").write_bytes(_decode_png(overlay))
    if heatmap:
        (cover_dir / "heatmap.png").write_bytes(_decode_png(heatmap))

    base = url_for("case_file", case_id=case_id, filename="xray.png")
    return {
        "image_url": base,
        "overlay_url": url_for("case_file", case_id=case_id, filename="overlay.png"),
        "heatmap_url": url_for("case_file", case_id=case_id, filename="heatmap.png"),
    }


@app.route("/api/predict", methods=["POST"])
def api_predict():
    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify({"error": "No image file provided."}), 400
    if file.content_type and not file.content_type.startswith("image/"):
        return jsonify({"error": "Uploaded file is not an image."}), 400

    model_key = request.form.get("model") or next(iter(MODEL_REGISTRY))
    if model_key not in MODEL_REGISTRY:
        return jsonify({"error": f"Unknown model '{model_key}'."}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty."}), 400

    try:
        result = analyze(file_bytes, model_key)
    except Exception:
        log.exception("Prediction failed")
        return jsonify({"error": "Could not read the image. Upload a valid chest X-ray (PNG/JPG)."}), 400

    case_id = result["image_id"]
    case_id = case_id[:8]
    result["image_id"] = case_id

    urls = _save_case_images(case_id, file_bytes, result)
    result.update(urls)
    result.pop("attention", None)
    result.pop("heatmap", None)

    result["model_label"] = MODEL_REGISTRY[model_key]["label"]
    result["patient_name"] = (request.form.get("patient_name", "") or "").strip()
    result["patient_mrn"] = (request.form.get("patient_mrn", "") or "").strip()
    result["patient_sex"] = (request.form.get("patient_sex", "") or "").strip()
    result["scan_date"] = (request.form.get("scan_date", "") or "").strip()

    saved = records.save_record(case_id, {
        "case_id": case_id,
        "patient_name": result["patient_name"],
        "patient_mrn": result["patient_mrn"],
        "patient_sex": result["patient_sex"],
        "scan_date": result["scan_date"],
        "diagnosis": result["verdict"],
        "confidence": result["confidence"],
        "probability_normal": result["probabilities"]["NORMAL"],
        "probability_pneumonia": result["probabilities"]["PNEUMONIA"],
        "confidence_level": result["confidence_level"],
        "interpretation": result["interpretation"],
        "model_label": result["model_label"],
        "model_key": model_key,
        "latency_ms": result["latency_ms"],
        "image_path": urls["image_url"],
        "overlay_path": urls["overlay_url"],
        "heatmap_path": urls["heatmap_url"],
    })
    result["record_id"] = saved["case_id"]
    return jsonify(result)


@app.route("/api/records")
def api_records():
    return jsonify({"records": records.list_records()})


@app.route("/api/records/<case_id>")
def api_record(case_id):
    rec = records.get_record(case_id)
    if rec is None:
        return jsonify({"error": "Record not found."}), 404
    return jsonify(rec)


@app.route("/api/records/<case_id>", methods=["DELETE"])
def api_record_delete(case_id):
    if records.delete_record(case_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Record not found."}), 404


@app.route("/api/settings")
def api_settings():
    return jsonify(records.get_settings())


@app.route("/api/settings/storage", methods=["POST"])
def api_settings_storage():
    body = request.get_json(silent=True) or {}
    if body.get("default"):
        info = records.reset_data_dir()
    else:
        path = (body.get("data_dir") or "").strip()
        if not path:
            return jsonify({"error": "Storage path is required."}), 400
        if not os.path.isabs(os.path.expanduser(path)):
            return jsonify({"error": "Store records in an absolute path, e.g. /home/user/mulch-storage."}), 400
        try:
            info = records.set_data_dir(path)
        except Exception as exc:
            return jsonify({"error": f"Could not use that path: {exc}"}), 400
    return jsonify({"ok": True, **info})


def serve(port=None):
    load_models()
    port = int(port or os.environ.get("MULCH_PORT", "5005"))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    serve()
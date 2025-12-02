import os
import uuid
import pathlib
import threading
import time
import torch
from flask import Flask, request, render_template_string, send_file, jsonify
import whisper
from openai import OpenAI
import markdown
from weasyprint import HTML
from werkzeug.utils import secure_filename
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html").read_text(encoding="utf-8")

UPLOAD_FOLDER = pathlib.Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXT = {"wav", "mp3", "m4a", "flac", "ogg", "mp4", "webm", "mkv"}
CLEANUP_INTERVAL = 600

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 900 * 1024 * 1024
app.debug = True

whisper_model = whisper.load_model("turbo")
client = OpenAI(base_url="https://api.moonshot.cn/v1",
                api_key = os.getenv("LLM_KEY"))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def cleanup_old_files():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cutoff = time.time() - CLEANUP_INTERVAL
        for p in UPLOAD_FOLDER.iterdir():
            if p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)

threading.Thread(target=cleanup_old_files, daemon=True).start()

def write_prog(uid: str, percent: int):
    (UPLOAD_FOLDER / f"{uid}.prog").write_text(str(percent))

def transcribe_audio(audio_path: pathlib.Path) -> str:
    result = whisper_model.transcribe(str(audio_path), language="zh", fp16=torch.cuda.is_available())
    return result["text"].strip()

def summarize_with_kimi(text: str) -> str:
    prompt = f"""把以下语音转写全文整理成结构化的 Markdown 总结，要求：
1. 核心摘要（3-5 句）
2. 按逻辑拆成 3-6 个主题，每个主题一级标题，下列要点
3. 逐主题精炼原文（去口语、重复，保留关键信息）

原文：
{text}
"""
    rsp = client.chat.completions.create(model="kimi-k2-thinking-turbo",
                                         messages=[{"role": "user", "content": prompt}],
                                         temperature=0.3)
    return rsp.choices[0].message.content.strip()

def md_to_pdf(md_text: str) -> bytes:
    html = markdown.markdown(md_text, extensions=["extra", "tables", "fenced_code"])
    full_html = f"""<html><head><meta charset="utf-8"><style>
body{{font-family:"Noto Sans SC",sans-serif;line-height:1.6;padding:40px}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#2980b9}} ul{{margin:10px 0}}
</style></head><body>{html}</body></html>"""
    return HTML(string=full_html).write_pdf()

def background_task(uid: str, audio_path: pathlib.Path, pdf_path: pathlib.Path, err_path: pathlib.Path):
    try:
        write_prog(uid, 10)
        text = transcribe_audio(audio_path)
        write_prog(uid, 50)
        md = summarize_with_kimi(text)
        write_prog(uid, 80)
        pdf_bytes = md_to_pdf(md)
        pdf_path.write_bytes(pdf_bytes)
        write_prog(uid, 100)
    except Exception as e:
        err_path.write_text(str(e), encoding="utf-8")
    finally:
        audio_path.unlink(missing_ok=True)

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return render_template_string(TEMPLATE)

    uid   = request.form.get("uid") or str(uuid.uuid4())
    chunk = request.files.get("audio")
    if not chunk:
        return jsonify({"error": "未收到文件块"}), 400

    suffix = pathlib.Path(secure_filename(chunk.filename)).suffix.lower() if chunk.filename else ".tmp"
    audio_path = UPLOAD_FOLDER / f"{uid}{suffix}"
    with open(audio_path, "ab") as f:
        f.write(chunk.read())

    total_size = int(request.form.get("total", 0))
    if total_size and audio_path.stat().st_size >= total_size:
        pdf_path = UPLOAD_FOLDER / f"{uid}.pdf"
        err_path = UPLOAD_FOLDER / f"{uid}.err"
        threading.Thread(target=background_task, args=(uid, audio_path, pdf_path, err_path), daemon=True).start()
        return jsonify({"uid": uid}), 202

    return jsonify({"uid": uid}), 206

@app.route("/status/<uid>")
def status(uid):
    pdf_path = UPLOAD_FOLDER / f"{uid}.pdf"
    err_path = UPLOAD_FOLDER / f"{uid}.err"
    prog_path = UPLOAD_FOLDER / f"{uid}.prog"

    if pdf_path.exists():
        return jsonify({"status": "done", "download": f"/download/{uid}", "percent": 100})
    if err_path.exists():
        error = err_path.read_text(encoding="utf-8")
        err_path.unlink(missing_ok=True)
        return jsonify({"status": "error", "message": error}), 500
    percent = int(prog_path.read_text()) if prog_path.exists() else 0
    return jsonify({"status": "processing", "percent": percent})

@app.route("/download/<uid>")
def download(uid):
    pdf_path = UPLOAD_FOLDER / f"{uid}.pdf"
    err_path = UPLOAD_FOLDER / f"{uid}.err"
    if pdf_path.exists():
        return send_file(pdf_path, as_attachment=True, download_name="会议总结.pdf")
    if err_path.exists():
        error = err_path.read_text(encoding="utf-8")
        err_path.unlink(missing_ok=True)
        return f"<pre>处理失败：{error}</pre>", 500
    return jsonify({"error": "文件还未准备好"}), 404

if __name__ == "__main__":
    print("\n" + "═" * 70)
    print("音频一键转 PDF 总结服务已启动！")
    print("请用浏览器打开 → http://127.0.0.1:5000")
    print("═" * 70 + "\n")
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

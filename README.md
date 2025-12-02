# Audio → AI Summary → PDF

一句话描述  
**拖一段音视频，秒出结构化中文会议纪要 PDF。**

---

## ✨ 功能
- 支持 mp3 / wav / m4a / mp4 / mkv …  
- 自动语音转写（OpenAI Whisper `turbo`）  
- 大模型结构化总结（Moonshot Kimi）  
- 一键生成精美 PDF（WeasyPrint）  
- 10 MB 切片上传，900 MB 大文件无压力  
- 实时进度条，转写→总结→PDF 一目了然  

---

## 🚀 快速开始
```bash
# 1. 克隆
git clone git@github.com:WeissHymmnos/audio_to_pdf_transcription.git
cd audio_to_pdf_transcription

# 2. 创建虚拟环境（可选）
python -m venv venv && source venv/bin/activate  # Linux / macOS
# venv\Scripts\activate                          # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python app.py
```
浏览器自动打开 [http://127.0.0.1:5000](http://127.0.0.1:5000)，拖文件→生成→下载。

---

## 📦 依赖
| 模块 | 用途 |
|---|---|
| Flask | Web 服务 |
| OpenAI Whisper | 语音转写 |
| Moonshot OpenAI | 大模型总结 |
| WeasyPrint | PDF 渲染 |
| torch | Whisper 后端 |

一键安装：
```bash
pip install flask openai whisper weasyprint torch
```

---

## 🔧 配置
默认模型 `whisper turbo` 首次运行自动下载（≈ 1.5 GB）。  
如需换模型或 API，改这两行即可：
```python
whisper_model = whisper.load_model("base")   # 换小模型
client = OpenAI(base_url="https://api.xxx.com/v1", api_key="sk-xxx")
```

---

## 📁 目录说明
```
├─ app.py              # 后端主程序
├─ template.html       # 前端页面
├─ uploads/            # 临时文件（已 .gitignore）
├─ requirements.txt    # 依赖列表
└─ README.md           # 本文件
```

---

## 🌱 进度条原理
Whisper 提供 `progress_callback`，实时写 `.prog` 文件 → 前端轮询 `/status/<uid>` → 进度条平滑上涨。

---

## 🚧 常见问题
| 问题 | 快速解决 |
|---|---|
| 上传 405 | 确认路由已加 `@app.route("/", methods=["GET", "POST"])` |
| 进度卡 10% | 远程仓库非空，先 `git pull --allow-unrelated-histories` |
| 900 MB 失败 | 调大 `MAX_CONTENT_LENGTH` 或使用分片上传（已内置） |

---

MIT © WeissHymmnos

---

Star 一下，持续更新 👀

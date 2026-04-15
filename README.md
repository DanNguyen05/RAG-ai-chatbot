# 🏢 Local RAG AI Chatbot — Vingroup Annual Report Q&A

> **Hệ thống Hỏi-Đáp AI hoàn toàn bảo mật, chạy 100% offline, không rò rỉ dữ liệu.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?logo=streamlit)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-green)](https://langchain.com)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black)](https://ollama.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-vector%20store-purple)](https://trychroma.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://docker.com)

---

## 📌 Giới thiệu

Đây là ứng dụng **RAG (Retrieval-Augmented Generation)** tự xây dựng, cho phép hỏi-đáp thông minh dựa trên nội dung file PDF (Báo cáo Thường niên Vingroup) mà **không cần kết nối internet hay gửi dữ liệu ra ngoài**.

### Điểm nổi bật:
- 🔒 **Zero Data Leakage** — Toàn bộ xử lý AI chạy local trên máy
- ⚡ **ChromaDB Persistence** — Chỉ cần embed 1 lần, lần sau tải ngay lập tức
- 🧠 **Dual Model** — `nomic-embed-text` cho embedding (274MB, nhanh 20-50x), `llama3` cho trả lời
- 📊 **Progress Tracking** — Thanh tiến trình chi tiết theo từng bước embedding
- 🐳 **Docker Ready** — Đóng gói hoàn chỉnh với `docker-compose`

---

## 🏗️ Kiến trúc hệ thống

```
PDF Upload
    │
    ▼
PyPDFLoader ──► RecursiveCharacterTextSplitter (chunk_size=1000)
    │                           │
    │                           ▼
    │               nomic-embed-text (Ollama)
    │                           │
    │                           ▼
    │                    ChromaDB (local disk)
    │
    ▼
User Question ──► Retrieve top-k chunks ──► llama3 (Ollama) ──► Answer
```

---

## 🛠️ Tech Stack

| Thành phần | Công nghệ | Vai trò |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Giao diện web & chat |
| **RAG Framework** | LangChain | Orchestration pipeline |
| **Vector Store** | ChromaDB | Lưu trữ & tìm kiếm embedding |
| **Embedding Model** | nomic-embed-text (Ollama) | Chuyển text → vector |
| **LLM** | llama3 (Ollama) | Sinh câu trả lời |
| **Document Loader** | PyPDF | Đọc file PDF |
| **Containerization** | Docker + Docker Compose | Đóng gói & deploy |

---

## 🚀 Hướng dẫn chạy

### Yêu cầu
- Python 3.11+
- [Ollama](https://ollama.com) đã cài đặt
- Docker (nếu muốn chạy bằng container)

### Chạy local (Development)

```bash
# 1. Clone repo
git clone <repo-url>
cd RAG_ai

# 2. Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/Mac

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Pull các model AI cần thiết
ollama pull llama3
ollama pull nomic-embed-text

# 5. Chạy ứng dụng
streamlit run app.py
```

Mở trình duyệt tại: **http://localhost:8501**

### Chạy bằng Docker

```bash
# Build và khởi động tất cả services
docker compose up --build

# Lần đầu sẽ tự động pull model llama3 + nomic-embed-text (~4.5GB)
```

---

## 📖 Cách sử dụng

1. **Upload PDF** — Tải file báo cáo Vingroup vào sidebar
2. **Chờ embedding** — Hệ thống tự động xử lý và lưu vào ChromaDB (chỉ 1 lần)
3. **Hỏi đáp** — Nhập câu hỏi và nhận câu trả lời dựa trên nội dung file
4. **Lần sau** — Mở app lại, dữ liệu tải ngay lập tức từ disk (~2 giây)

---

## 📁 Cấu trúc thư mục

```
RAG_ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker build config
├── docker-compose.yml  # Multi-service orchestration
├── .gitignore
├── .dockerignore
└── chroma_db/          # Vector store (auto-generated, gitignored)
```

---

## 🔧 Cấu hình

Các hằng số có thể điều chỉnh trong `app.py`:

```python
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL       = "llama3"           # Thay bằng "mistral", "gemma2", v.v.
EMBED_MODEL     = "nomic-embed-text" # Model embedding chuyên dụng
CHROMA_DB_DIR   = "./chroma_db"      # Thư mục lưu vector store
BATCH_SIZE      = 50                 # Số chunk xử lý mỗi batch
```

---

## 👤 Tác giả

Dự án được xây dựng như một demo thực tế về **Local RAG system** — áp dụng các kỹ thuật:
- Retrieval-Augmented Generation (RAG)
- Vector Similarity Search
- Local LLM deployment với Ollama
- Persistent Vector Store với ChromaDB

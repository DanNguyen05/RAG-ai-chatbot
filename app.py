import streamlit as st
import tempfile
import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM, OllamaEmbeddings

# Hỗ trợ Docker: đọc URL Ollama từ biến môi trường
# - Chạy local:  OLLAMA_BASE_URL mặc định là http://localhost:11434
# - Chạy Docker: docker-compose truyền vào http://ollama:11434
OLLAMA_BASE_URL  = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL        = "llama3"           # Model LLM để trả lời câu hỏi
EMBED_MODEL      = "nomic-embed-text" # ✅ Model CHUYÊN DỤNG cho embedding (nhanh gấp 20-50x)
CHROMA_DB_DIR    = "./chroma_db"      # Thư mục lưu vector store xuống ổ đĩa
BATCH_SIZE       = 50                 # Tăng từ 10 → 50 vì nomic-embed-text rất nhanh

# --- GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="Vingroup AI Assistant", page_icon="🏢", layout="wide")
st.title("🏢 Hệ thống Hỏi-Đáp AI Bảo mật (Local RAG)")
st.markdown("Phân tích Báo cáo Thường niên Vingroup - *Zero Data Leakage*")
st.divider()

# --- KHỞI TẠO BIẾN TRẠNG THÁI ---
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "llm" not in st.session_state:
    st.session_state.llm = None

# ============================================================
# TỰ ĐỘNG LOAD TỪ DISK NẾU ĐÃ CÓ SẴN
# ============================================================
db_exists = os.path.isdir(CHROMA_DB_DIR) and len(os.listdir(CHROMA_DB_DIR)) > 0

if db_exists and st.session_state.vectorstore is None:
    try:
        with st.spinner("⚡ Đang tải dữ liệu đã lưu từ ổ đĩa..."):
            embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
            vs = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=embeddings
            )
            # Kiểm tra DB có dữ liệu thực sự không (tránh load DB bị corrupt)
            doc_ids = vs.get()["ids"]
            if len(doc_ids) == 0:
                raise ValueError("DB rỗng hoặc bị lỗi")
            st.session_state.vectorstore = vs
            st.session_state.llm = OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_BASE_URL)
        st.toast(f"✅ Đã tải {len(doc_ids):,} đoạn từ ổ đĩa!", icon="⚡")
    except Exception as e:
        # DB bị corrupt → xóa và yêu cầu upload lại
        st.warning(f"⚠️ DB bị lỗi ({e}), đang xóa để tạo lại...")
        shutil.rmtree(CHROMA_DB_DIR, ignore_errors=True)
        st.session_state.vectorstore = None
        st.rerun()

# --- THANH BÊN ---
with st.sidebar:
    st.header("1. Nạp Dữ Liệu 📂")

    if st.session_state.vectorstore is not None:
        st.success("✅ Dữ liệu đã sẵn sàng")
        col_a, col_b = st.columns(2)
        with col_a:
            # Dùng public API thay vì _collection (private)
            chunk_count = len(st.session_state.vectorstore.get()["ids"])
            st.metric("Số đoạn", f"{chunk_count:,}")
        with col_b:
            if db_exists:
                size_mb = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, filenames in os.walk(CHROMA_DB_DIR)
                    for f in filenames
                ) / (1024 * 1024)
                st.metric("Dung lượng", f"{size_mb:.1f} MB")

        st.divider()
        if st.button("🗑️ Xóa DB & Tải File Mới", type="secondary", use_container_width=True):
            if os.path.isdir(CHROMA_DB_DIR):
                shutil.rmtree(CHROMA_DB_DIR)
            st.session_state.vectorstore = None
            st.session_state.llm = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.caption(f"🤖 LLM: `{LLM_MODEL}`")
        st.caption(f"🧮 Embedding: `{EMBED_MODEL}`")

    else:
        uploaded_file = st.file_uploader("Tải file Báo cáo Vingroup (PDF)", type="pdf")
        if uploaded_file:
            st.info("⏳ Đang xử lý ở màn hình chính...")
        st.divider()
        st.caption(f"🧮 Embedding: `{EMBED_MODEL}` ⚡")

# ============================================================
# KHU VỰC TIẾN TRÌNH — hiển thị ở màn hình chính
# ============================================================
uploaded_file = locals().get("uploaded_file", None)

if uploaded_file and st.session_state.vectorstore is None:

    st.subheader("⚙️ Đang nạp dữ liệu vào AI, vui lòng chờ...")
    st.caption("Quá trình này chỉ cần làm **1 lần**. Lần sau mở app sẽ tải ngay lập tức ⚡")

    _, col, _ = st.columns([1, 5, 1])
    with col:
        step_label   = st.empty()
        overall_bar  = st.progress(0)
        detail_label = st.empty()
        embed_bar    = st.empty()

    def update_progress(pct: int, step: str, detail: str):
        step_label.markdown(f"### {step}")
        overall_bar.progress(pct)
        detail_label.caption(detail)

    # Bước 1: Lưu file tạm
    update_progress(5, "📥 Bước 1 / 4 — Đọc file PDF...", "Đang lưu file tạm...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    # Bước 2: Load từng trang
    update_progress(15, "📄 Bước 2 / 4 — Phân tích nội dung trang...", "Đang tải văn bản từng trang...")
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    update_progress(28, "📄 Bước 2 / 4 — Phân tích nội dung trang...",
                    f"✅ Đọc xong **{len(docs)} trang** PDF")

    # Bước 3: Tách chunks
    update_progress(30, "✂️ Bước 3 / 4 — Băm nhỏ văn bản...", "Đang chia thành các đoạn nhỏ...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    total_chunks = len(splits)
    update_progress(35, "✂️ Bước 3 / 4 — Băm nhỏ văn bản...",
                    f"✅ Tạo ra **{total_chunks} đoạn** từ {len(docs)} trang")

    # Bước 4: Embedding bằng nomic-embed-text (nhanh hơn nhiều!)
    update_progress(36, "🧠 Bước 4 / 4 — Tạo Embedding...", f"Khởi tạo {EMBED_MODEL}...")
    st.session_state.llm = OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_BASE_URL)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    batches = [splits[i:i + BATCH_SIZE] for i in range(0, total_chunks, BATCH_SIZE)]
    total_batches = len(batches)
    vectorstore = None

    for i, batch in enumerate(batches):
        done = min((i + 1) * BATCH_SIZE, total_chunks)
        overall_pct = 36 + int(((i + 1) / total_batches) * 59)

        update_progress(
            overall_pct,
            f"🧠 Bước 4 / 4 — Tạo Embedding  ({done} / {total_chunks} đoạn)",
            f"Batch {i + 1} / {total_batches} — dùng `{EMBED_MODEL}` ⚡ **Sẽ lưu tự động sau khi xong** 💾"
        )
        embed_bar.progress(
            int(((i + 1) / total_batches) * 100),
            text=f"Embedding: {done} / {total_chunks} đoạn  ▸  Batch {i + 1}/{total_batches}"
        )

        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=CHROMA_DB_DIR
            )
        else:
            vectorstore.add_documents(batch)

    # Hoàn tất
    st.session_state.vectorstore = vectorstore
    os.remove(tmp_path)

    overall_bar.progress(100)
    embed_bar.empty()
    step_label.markdown("### ✅ Hoàn tất & Đã lưu xuống ổ đĩa! 💾")
    detail_label.empty()

    with col:
        st.success(
            f"🎉 Sẵn sàng! Đã nạp **{total_chunks} đoạn** từ **{len(docs)} trang**.\n\n"
            f"💾 Dữ liệu đã lưu vào `{CHROMA_DB_DIR}` — **Lần sau mở app không cần chờ nữa!**"
        )
    st.balloons()
    st.rerun()

# ============================================================
# GIAO DIỆN CHAT
# ============================================================
if st.session_state.vectorstore is not None:
    st.header("2. Tương Tác AI 🤖")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("Hỏi Vingroup AI điều gì đó..."):
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("AI đang đọc báo cáo..."):
                retriever    = st.session_state.vectorstore.as_retriever()
                docs         = retriever.invoke(user_input)
                context_text = "\n\n".join([doc.page_content for doc in docs])
                final_prompt = (
                    "Bạn là chuyên gia phân tích tài liệu Vingroup. "
                    "Dựa CHÍNH XÁC vào thông tin sau đây để trả lời câu hỏi. "
                    "Tuyệt đối không tự bịa ra thông tin bên ngoài.\n\n"
                    f"THÔNG TIN:\n{context_text}\n\n"
                    f"CÂU HỎI:\n{user_input}\n\nTRẢ LỜI:"
                )
                answer = st.session_state.llm.invoke(final_prompt)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

elif not uploaded_file and st.session_state.vectorstore is None:
    st.header("2. Tương Tác AI 🤖")
    st.error("⚠️ Vui lòng tải file PDF ở thanh bên trái trước khi hỏi!")
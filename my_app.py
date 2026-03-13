import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 財務稽核-全格式版", layout="wide")
st.title("⚖️ AI 全能財務稽核 (PDF/Word/Excel/圖片)")

# --- 側邊欄設定 ---
with st.sidebar:
    api_key = st.text_input("🔑 請貼上 API Key", type="password").strip()
    st.info("💡 建議：若一直失敗，請換個 Google 帳號申請新 Key。")

# --- 多檔案上傳 ---
uploaded_files = st.file_uploader(
    "上傳檔案 (可同時選取 PDF, Word, Excel, 圖片)", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
    """將不同格式轉為文字或圖片數據"""
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"表格數據:\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f)
            if img.mode != 'RGB': img = img.convert('RGB')
            img.thumbnail((1600, 1600))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"[圖片附件: {f.name}]", img_str
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

if uploaded_files:
    all_texts = []
    all_imgs = []
    
    with st.spinner("正在讀取檔案內容..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 檔案: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    tab1, tab2 = st.tabs(["📝 預覽提取內容", "📊 AI 稽核分析"])
    
    with tab1:
        st.text_area("所有提取的文字數據：", full_context, height=300)
    
    with tab2:
        if st.button("🚀 啟動 AI 跨檔案分析", type="primary"):
            if not api_key:
                st.error("請在左側輸入 API Key")
            else:
                with st.status("AI 正在閱讀並比對數據...", expanded=True) as status:
                    # 組合內容：

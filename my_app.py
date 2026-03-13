import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 全能財務稽核", layout="wide")
st.title("⚖️ AI 全能財務稽核員 (多格式支援)")

# --- 側邊欄：API 與設定 ---
with st.sidebar:
    api_key = st.text_input("🔑 API Key", type="password").strip()
    st.info("支援格式：PDF, Word, Excel, PNG/JPG")

# --- 檔案上傳 ---
uploaded_files = st.file_uploader(
    "上傳簽呈、清單或照片 (可多選)", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
    """根據副檔名處理檔案"""
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"Excel 表格數據：\n{df.to_string()}", None
        
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            # 處理圖片：壓縮並轉 Base64
            img = Image.open(f)
            if img.mode != 'RGB': img = img.convert('RGB')
            img.thumbnail((1200, 1200))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"[圖片附件: {f.name}]", img_str
            
    except Exception as e:
        return f"錯誤讀取 {f.name}: {str(e)}", None
    return "", None

if uploaded_files:
    all_texts = []
    all_imgs = []
    
    with st.spinner("正在解析檔案..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 檔案: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    tab1, tab2 = st.tabs(["📄 內容預覽", "📊 AI 稽核分析"])
    
    with tab1:
        st.text_area("所有提取文字 (包含 Excel/Word/PDF)：", full_context, height=300)
    
    with tab2:
        if st.button("🚀 啟動 AI 跨檔案分析", type="primary"):
            if not api_key:
                st.warning("請輸入 API Key")
            else:
                with st.status("AI 正在閱讀所有文字與圖片...", expanded=True) as status:
                    # 組合 Payload：文字 + 圖片
                    parts = [{"text": f"你是一位財務審核員。請核對以下 113年 與 114年 的保費數據並比對差異：\n\n{full_context}"}]
                    for b64 in all_imgs:
                        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                    
                    payload = {"contents": [{"parts": parts}]}
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    
                    res = requests.post(url, json=payload, timeout=60)
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"分析失敗：{res.text}")

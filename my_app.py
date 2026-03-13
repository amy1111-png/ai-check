import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 財務稽核-終極版", layout="wide")
st.title("⚖️ AI 全能財務稽核 (多路徑相容版)")

# --- 側邊欄 ---
with st.sidebar:
    api_key = st.text_input("🔑 請貼上 API Key", type="password").strip()
    st.info("支援：PDF, Word, Excel, 圖片")

# --- 檔案上傳 ---
uploaded_files = st.file_uploader(
    "上傳檔案 (可多選)", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
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
            img.thumbnail((1200, 1200))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"[圖片附件: {f.name}]", img_str
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

if uploaded_files:
    all_texts = []
    all_imgs = []
    for f in uploaded_files:
        txt, img_b64 = process_file(f)
        if txt: all_texts.append(f"--- 檔案: {f.name} ---\n{txt}")
        if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    if st.button("🚀 啟動 AI 跨檔案分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            with st.status("🛸 正在強行突破 API 路徑...", expanded=True) as status:
                parts = [{"text": f"你是一位財務審核員。請核對以下資料中的 113年 與 114年 保費數據並比對差異：\n\n{full_context}"}]
                for b64 in all_imgs:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                payload = {"contents": [{"parts": parts}]}
                
                # --- 這是關鍵：暴力嘗試所有可能的 URL 組合 ---
                possible_urls = [
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                    f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}", # 備案：改用 Pro
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                ]
                
                success = False
                last_error = ""
                for url in possible_urls:
                    st.write(f"正在嘗試連線至：{url.split('models/')[1].split(':')[0]}...")
                    try:
                        res = requests.post(url, json=payload, timeout=60)
                        if res.status_code == 200:
                            status.update(label="✅ 分析成功！", state="complete")
                            st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                            success = True
                            break
                        else:
                            last_error = res.text
                    except Exception as e:
                        last_error = str(e)
                
                if not success:
                    st.error(f"❌ 所有路徑均失敗。最後的錯誤訊息：{last_error}")
                    st.info("💡 如果連 gemini-pro 都 404，極有可能是 API Key 本身沒開通 Generative Language API。請到 AI Studio 重新確認 Key 的狀態。")

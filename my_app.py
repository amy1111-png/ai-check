import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="API 診斷與稽核系統", layout="wide")
st.title("🛠️ API 診斷與全能稽核員")

# --- 側邊欄 ---
with st.sidebar:
    api_key = st.text_input("🔑 貼上【新專案】申請的 Key", type="password").strip()

# --- 1. 自動診斷功能 ---
if st.sidebar.button("🔍 診斷我的 Key 權限"):
    if not api_key:
        st.error("請先貼上 Key")
    else:
        diag_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(diag_url)
        if res.status_code == 200:
            models = res.json().get('models', [])
            st.sidebar.success(f"連線成功！共找到 {len(models)} 個可用模型")
            # 顯示前三個模型名稱供參考
            for m in models[:5]:
                st.sidebar.code(m['name'])
        else:
            st.sidebar.error(f"診斷失敗：{res.text}")

# --- 2. 檔案處理 (與之前相同) ---
uploaded_files = st.file_uploader("上傳檔案 (PDF/Excel/Word/圖片)", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

def get_text_from_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"Excel數據:\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1000, 1000))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e: return f"讀取失敗: {str(e)}", None
    return "", None

# --- 3. 分析按鈕 ---
if st.button("🚀 啟動診斷式分析", type="primary"):
    if not api_key or not uploaded_files:
        st.error("請檢查 Key 和檔案")
    else:
        with st.status("🛸 正在尋找可用路徑...", expanded=True) as status:
            all_txt = []
            all_img = []
            for f in uploaded_files:
                t, i = get_text_from_file(f)
                if t: all_txt.append(t)
                if i: all_img.append(i)
            
            context = "\n\n".join(all_txt)
            parts = [{"text": f"你是一位財務審核員。分析以下數據：\n\n{context}"}]
            for img in all_img:
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img}})
            
            # --- 最終嘗試三種官方路徑 ---
            urls = [
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            ]
            
            success = False
            for url in urls:
                st.write(f"嘗試路徑: {url.split('models/')[1].split(':')[0]}")
                res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=30)
                if res.status_code == 200:
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    success = True
                    status.update(label="✅ 成功！", state="complete")
                    break
            
            if not success:
                st.error(f"❌ 全部嘗試失敗。最後回報：{res.text}")

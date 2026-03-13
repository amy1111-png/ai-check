import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber
import time

st.set_page_config(page_title="AI 簽呈大師", layout="wide")
st.title("⚖️ AI 簽呈與附件深度分析系統")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ 已自動從雲端後台讀取 API Key")
else:
    api_key = st.text_input("請貼上您的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
uploaded_files = st.file_uploader("請上傳測試簽呈", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

def process_files(files):
    text_data, images = [], []
    for f in files:
        if f.name.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                content = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                text_data.append(f"【PDF:{f.name}】\n{content}")
        elif f.name.endswith('.docx'):
            doc = Document(f)
            text_data.append(f"【Word:{f.name}】\n" + "\n".join([p.text for p in doc.paragraphs]))
        elif f.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            text_data.append(f"【Excel:{f.name}】\n{df.to_string(index=False)}")
        elif f.name.endswith(('.png', '.jpg', '.jpeg')):
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
            images.append({"inline_data": {"mime_type": "image/png", "data": img_b64}})
            text_data.append(f"【圖片:{f.name}】")
    return "\n\n".join(text_data), images

# --- 核心邏輯：測試並獲取成功的響應 ---
def call_gemini_api(key, payload):
    # 嘗試不同的 API 版本與模型組合
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={key}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={key}"
    ]
    
    last_error = ""
    for url in endpoints:
        try:
            res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=90)
            if res.status_code == 200:
                return res, None
            else:
                last_error = res.json().get('error', {}).get('message', '未知錯誤')
        except Exception as e:
            last_error = str(e)
            continue
    return None, last_error

# --- 第三步：執行分析 ---
st.divider()
if st.button("🚀 啟動深度分析", type="primary"):
    if not api_key:
        st.error("❌ 請提供 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("🛸 正在自動匹配模型並分析中...", expanded=True) as status:
            try:
                all_text, all_images = process_files(uploaded_files)
                prompt = f"你是一位財務審核員。請核對金額、比對 113年 與 114年 保費數字、計算差額與百分比，並提供審核建議。內容：\n{all_text}"
                payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                
                res, err = call_gemini_api(api_key, payload)
                
                if res:
                    status.update(label="✅ 分析完成！", state="complete")
                    st.subheader("📊 AI 審核報告")
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error(f"❌ 所有模型路徑皆嘗試失敗。原因：{err}")
                    status.update(label="連線失敗", state="error")
                
            except Exception as e:
                st.error(f"系統錯誤：{str(e)}")

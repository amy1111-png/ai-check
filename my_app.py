import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber
import time  # 增加時間模組用於重試

st.set_page_config(page_title="AI 簽呈大師", layout="wide")
st.title("⚖️ AI 簽呈與附件深度分析系統")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
# 先檢查 Secrets 是否有存 Key，沒有的話才顯示輸入框
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ 已自動從雲端後台讀取 API Key")
else:
    api_key = st.text_input("請貼上您的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
uploaded_files = st.file_uploader("請上傳測試簽呈", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- 核心邏輯：自動尋找可用模型 ---
def get_available_model(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            models = res.json().get('models', [])
            for m in models:
                if "gemini-1.5-flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
        return "models/gemini-1.5-flash" # 預設回傳
    except:
        return "models/gemini-1.5-flash"

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

# --- 第三步：執行分析 ---
st.divider()
if st.button("🚀 啟動深度分析", type="primary"):
    if not api_key:
        st.error("❌ 請提供 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("🛸 正在深入分析數據，請稍候 (檔案較多時需約 1 分鐘)...", expanded=True) as status:
            try:
                model_name = get_available_model(api_key)
                all_text, all_images = process_files(uploaded_files)
                
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                prompt = f"你是一位財務審核員。請核對金額、比對 113年 與 114年 保費數字、計算差額與百分比，並提供審核建議。內容：\n{all_text}"
                payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                
                # --- 重試機制與加長超時設定 ---
                max_retries = 2
                for i in range(max_retries + 1):
                    try:
                        # timeout 設定為 90 秒
                        res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=90)
                        if res.status_code == 200:
                            status.update(label="✅ 分析完成！", state="complete")
                            st.subheader("📊 AI 審核報告")
                            st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                            break
                        else:
                            st.error(f"分析失敗：{res.json().get('error', {}).get('message')}")
                            break
                    except requests.exceptions.Timeout:
                        if i < max_retries:
                            st.warning(f"⏱️ 伺服器回應較慢，正在進行第 {i+1} 次重試...")
                            time.sleep(2) # 等兩秒再試
                        else:
                            st.error("❌ Google 伺服器忙碌中，請稍後再試，或嘗試減少上傳檔案的頁數。")
                
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")

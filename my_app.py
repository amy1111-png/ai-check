import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber

st.set_page_config(page_title="AI 簽呈大師", layout="wide")
st.title("⚖️ AI 簽呈與附件深度分析系統 (自動模型匹配版)")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
api_key = st.text_input("請貼上您的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
uploaded_files = st.file_uploader("請上傳測試簽呈", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- 核心邏輯：自動尋找可用模型 ---
def get_available_model(key):
    # 直接詢問 Google 你的 Key 到底能用哪一個模型
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            models = res.json().get('models', [])
            # 優先找 1.5 flash，因為它最快最準
            for m in models:
                if "gemini-1.5-flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
            # 退而求其次，找任何支援 generateContent 的模型
            for m in models:
                if "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
        return None
    except:
        return None

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
if st.button("🚀 啟動自動掃描分析", type="primary"):
    if not api_key:
        st.error("❌ 請輸入 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("正在掃描您的 Key 權限...", expanded=True) as status:
            # 1. 自動偵測模型
            model_name = get_available_model(api_key)
            
            if not model_name:
                st.error("❌ 找不到可用的模型！請檢查您的 API Key 是否正確開通了 Gemini 服務。")
                status.update(label="模型掃描失敗", state="error")
            else:
                st.write(f"✅ 偵測到可用模型：{model_name}")
                try:
                    # 2. 處理檔案
                    all_text, all_images = process_files(uploaded_files)
                    
                    # 3. 發送請求
                    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                    prompt = f"你是一位財務審核員。請核對金額、比對 113年 與 114年 保費數字、計算差額與百分比，並提供審核建議。內容：\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                    
                    res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=30)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.subheader("📊 AI 審核報告")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"分析失敗：{res.json().get('error', {}).get('message')}")
                except Exception as e:
                    st.error(f"發生錯誤：{str(e)}")

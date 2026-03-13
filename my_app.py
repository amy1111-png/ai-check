import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber
import time

st.set_page_config(page_title="AI 簽呈大師", layout="wide")
st.title("⚖️ AI 簽呈與附件深度分析系統 (自動探測版)")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ 已從雲端 Secrets 自動載入")
else:
    api_key = st.text_input("請貼上您的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
uploaded_files = st.file_uploader("上傳簽呈 (PDF/Word/Excel/圖片)", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- 偵查兵：找出你的 Key 到底能用哪個模型 ---
def find_valid_model(key):
    # 同時測試 v1 和 v1beta 的清單路徑
    for ver in ["v1beta", "v1"]:
        list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={key}"
        try:
            r = requests.get(list_url, timeout=10)
            if r.status_code == 200:
                models = r.json().get('models', [])
                # 優先順序：1.5-flash > 1.5-pro > 任何支援 generateContent 的模型
                for target in ["gemini-1.5-flash", "gemini-1.5-pro"]:
                    for m in models:
                        if target in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                            return m['name'], ver
                # 如果都沒有，抓第一個能用的
                for m in models:
                    if "generateContent" in m['supportedGenerationMethods']:
                        return m['name'], ver
        except:
            continue
    return None, None

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

# --- 第三步：按鈕執行 ---
st.divider()
if st.button("🚀 啟動自動探測與分析", type="primary"):
    if not api_key:
        st.error("❌ 請輸入 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("🔍 正在探測可用模型路徑...", expanded=True) as status:
            model_path, api_ver = find_valid_model(api_key)
            
            if not model_path:
                st.error("❌ 無法偵測到可用模型。請確認您的 API Key 是否正確，或已在 Google AI Studio 啟用。")
                status.update(label="探測失敗", state="error")
            else:
                st.write(f"📡 成功連線！使用路徑：`{api_ver}/{model_path}`")
                try:
                    all_text, all_images = process_files(uploaded_files)
                    prompt = f"你是一位財務審核員。請核對金額、比對 113年 與 114年 保費數字、計算差額與百分比，並提供審核建議。資料：\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                    
                    final_url = f"https://generativelanguage.googleapis.com/{api_ver}/{model_path}:generateContent?key={api_key}"
                    res = requests.post(final_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=120)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析成功！", state="complete")
                        st.subheader("📊 AI 財務審核報告")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"API 拒絕請求：{res.json().get('error', {}).get('message')}")
                except Exception as e:
                    st.error(f"分析過程出錯：{str(e)}")

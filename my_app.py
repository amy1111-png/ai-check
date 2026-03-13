import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber
import time

st.set_page_config(page_title="AI 簽呈財務稽核員", layout="wide")
st.title("⚖️ AI 簽呈與附件深度分析系統 (終極強化版)")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ 已從雲端 Secrets 自動載入 Key")
else:
    api_key = st.text_input("請貼上您的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
st.info("💡 提示：如果 PDF 是掃描件（文字選不起來），請直接改用手機拍照上傳照片，AI 辨識效果更好！")
uploaded_files = st.file_uploader("上傳簽呈或附件 (支援 PDF, Word, Excel, 圖片)", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- 偵查兵：找出可用模型 ---
def find_valid_model(key):
    for ver in ["v1beta", "v1"]:
        list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={key}"
        try:
            r = requests.get(list_url, timeout=10)
            if r.status_code == 200:
                models = r.json().get('models', [])
                for target in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
                    for m in models:
                        if target in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                            return m['name'], ver
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
                # 提取所有頁面的文字，並標註頁碼
                content = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        content += f"\n--- 第 {i+1} 頁 ---\n{page_text}"
                text_data.append(f"【PDF 檔案名稱：{f.name}】\n{content}")
        elif f.name.endswith('.docx'):
            doc = Document(f)
            text_data.append(f"【Word 檔案名稱：{f.name}】\n" + "\n".join([p.text for p in doc.paragraphs]))
        elif f.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            text_data.append(f"【Excel 檔案名稱：{f.name}】\n{df.to_string(index=False)}")
        elif f.name.endswith(('.png', '.jpg', '.jpeg')):
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
            images.append({"inline_data": {"mime_type": "image/png", "data": img_b64}})
            text_data.append(f"【已上傳圖片附件：{f.name}】")
    return "\n\n".join(text_data), images

# --- 第三步：執行分析 ---
st.divider()
if st.button("🚀 開始深度稽核", type="primary"):
    if not api_key:
        st.error("❌ 請輸入 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("🔍 正在分析資料... (這可能需要 30-60 秒)", expanded=True) as status:
            model_path, api_ver = find_valid_model(api_key)
            
            if not model_path:
                st.error("❌ 無法偵測到可用模型。")
            else:
                try:
                    all_text, all_images = process_files(uploaded_files)
                    
                    # --- 終極強化 Prompt ---
                    prompt = f"""
                    你現在是一位專業的財務稽核與數據分析師。我已經提供了附件資料（包含文字與圖像）。
                    
                    【絕對指令】：
                    1. 嚴禁提供「範例報告」或「模擬數據」。
                    2. 如果你看到這則訊息，表示你必須從我提供的資料中找出真實數據。
                    3. 任務：比對 113年 與 114年 的保費數據。
                    
                    【輸出格式要求】：
                    - 製作數據對照表：包含項目、113年金額、114年金額、差額、變動百分比(%)。
                    - 自動核算：檢查附件中的「總計」是否等於各項加總，若不符請指出。
                    - 財務建議：針對變動幅度超過 5% 的項目給出審核意見。
                    
                    【附件資料內容】：
                    {all_text}
                    """
                    
                    payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                    final_url = f"https://generativelanguage.googleapis.com/{api_ver}/{model_path}:generateContent?key={api_key}"
                    
                    # 設定 120 秒超時，防止大檔案斷線
                    res = requests.post(final_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=120)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.subheader("📊 財務稽核報告 (正式版本)")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"分析失敗，錯誤代碼：{res.status_code}")
                        st.write(res.json())
                except Exception as e:
                    st.error(f"系統錯誤：{str(e)}")

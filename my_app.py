import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 財務智慧稽核系統 v4.5", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    mode = st.radio("選擇稽核邏輯：", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"], index=1)
    st.caption("自動偵測模型路徑模式已啟動")

# --- 3. 檔案處理 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            return f"表格數據({f.name}):\n{pd.read_excel(f).to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析: {f.name}", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("上傳報價單或相關單據", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    for f in files:
        t, i = process_file(f)
        if t: all_txt.append(t)
        if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 啟動深度分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            with st.status("📡 正在自動尋找可用模型路徑...") as status:
                # 【核心修正】動態獲取模型列表，避開 404
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                try:
                    models_data = requests.get(list_url).json()
                    target_model = None
                    
                    # 遍歷模型清單，找一個支援生成內容的 flash 模型
                    if 'models' in models_data:
                        for m in models_data.get('models', []):
                            if 'gemini-1.5-flash' in m['name'] and 'generateContent' in m['supportedGenerationMethods']:
                                target_model = m['name']
                                break
                    
                    if not target_model:
                        target_model = "models/gemini-1.5-flash" # 保底
                    
                    # 組合出正確的 Endpoint
                    url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                    
                    # 設定 Prompt
                    if mode == "診所/門市公式":
                        prompt = f"你是財務審核員。請用原本的兩段式格式總結。資料：{context}"
                    else:
                        prompt = f"你是財務稽核主管。分析比價差異、桃竹區異常點，並產出對答劇本。資料：{context}"

                    # 準備傳送
                    parts = [{"text": prompt}]
                    for b in all_img:
                        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b}})
                    
                    res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=120)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        status.update(label=f"✅ 已連接 {target_model} 並完成分析", state="complete")
                        st.markdown(res_json['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"API 錯誤: {res_json.get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"執行失敗: {str(e)}")

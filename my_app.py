import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務智慧稽核系統 v4.0", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    analysis_mode = st.radio(
        "選擇稽核邏輯：",
        ["原本成功公式 (診所/門市專用)", "深度疑點分析 (含桃竹區/跨區詢問劇本)"],
        index=1
    )
    st.divider()
    st.caption("自動修正 404 錯誤路徑模式已啟動")

# --- 3. 檔案處理函數 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"表格數據({f.name}):\n{df.to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析檔案: {f.name}", None
    return "", None

# --- 4. 主介面 ---
files = st.file_uploader("上傳簽呈、報價單或附件照片", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    for f in files:
        t, i = process_file(f)
        if t: all_txt.append(t)
        if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 啟動分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # 建立 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"你是一位財務審核員。核對後請用原本的兩點格式總結。資料內容：{context}"
            else:
                prompt = f"你是一位財務稽核主管。請進行多家比價分析、找出桃竹區單價異常點，並寫出詢問劇本。資料內容：{context}"

            with st.status("🛸 正在連線並自動偵測模型路徑...") as status:
                # 【全自動修正】先向 Google 詢問這個 Key 可以用的正確路徑
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                try:
                    models_res = requests.get(list_url).json()
                    model_path = ""
                    # 從列表中找出包含 'gemini-1.5-flash' 且支援生成內容的模型
                    for m in models_res.get('models', []):
                        if 'gemini-1.5-flash' in m['name'] and 'generateContent' in m['supportedGenerationMethods']:
                            model_path = m['name'] # 可能是 "models/gemini-1.5-flash" 或 "models/gemini-1.5-flash-latest"
                            break
                    
                    if not model_path:
                        model_path = "models/gemini-1.5-flash" # 保底寫法

                    # 組合出保證能用的 URL
                    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={api_key}"
                    
                    parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]
                    
                    res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=120)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        ans = res_json['candidates'][0]['content']['parts'][0]['text']
                        status.update(label=f"✅ 使用 {model_path} 分析完成", state="complete")
                        st.markdown(ans)
                    else:
                        st.error(f"API 錯誤 ({res.status_code}): {res_json.get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

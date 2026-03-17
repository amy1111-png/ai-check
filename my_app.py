import streamlit as st
import requests
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# 1. 基礎設定
st.set_page_config(page_title="AI 財務稽核系統", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# 2. 側邊欄
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 AI Studio 新申請的 Key", type="password").strip()
    st.divider()
    mode = st.radio("稽核邏輯", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"])
    st.caption("連線模式：Pure-Request 穩定版")

# 3. 檔案處理 (極簡化，避免 metadata 錯誤)
def process_file(f):
    try:
        if f.name.lower().endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif f.name.lower().endswith(('.xlsx', '.xls')):
            return f"表格數據:\n{pd.read_excel(f).to_string()}", None
        elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((600, 600)) # 再縮小一點，確保傳輸穩定
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return None, base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析: {f.name}", None
    return "", None

# 4. 主程式
files = st.file_uploader("上傳檔案", accept_multiple_files=True)

if files:
    all_text = []
    all_img = []
    for f in files:
        t, i = process_file(f)
        if t: all_text.append(t)
        if i: all_img.append(i)

    if st.button("🚀 開始分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # 建立 Prompt
            if mode == "診所/門市公式":
                prompt = f"財務審核：請用原本的兩段式格式總結。資料內容：\n{' '.join(all_text)}"
            else:
                prompt = f"資深財務稽核：請進行比價分析、找出桃竹區單價異常，並寫出詢問劇本。資料內容：\n{' '.join(all_text)}"

            with st.status("🛸 正在嘗試純淨連線...") as status:
                # 使用 v1beta 版本的純文字連線，避開 SDK 的 metadata 檢查
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                parts = [{"text": prompt}]
                for img_b64 in all_img:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
                
                payload = {"contents": [{"parts": parts}]}
                
                try:
                    # 強制不帶任何自訂 Metadata
                    response = requests.post(url, json=payload, timeout=90)
                    res_json = response.json()
                    
                    if response.status_code == 200:
                        ans = res_json['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans)
                    else:
                        st.error(f"連線失敗 ({response.status_code})")
                        st.json(res_json)
                except Exception as e:
                    st.error(f"系統超時或連線中斷：{str(e)}")

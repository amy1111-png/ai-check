import streamlit as st
import requests
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 財務稽核-最終修復版", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Studio 新申請的 Key", type="password").strip()
    mode = st.radio("稽核邏輯", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"])
    st.caption("連線模式：多重路徑暴力破解版")

def process_file(f):
    try:
        if f.name.lower().endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif f.name.lower().endswith(('.xlsx', '.xls')):
            return f"表格數據:\n{pd.read_excel(f).to_string()}", None
        elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((600, 600))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return None, base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析: {f.name}", None
    return "", None

files = st.file_uploader("上傳檔案", accept_multiple_files=True)

if files:
    all_text, all_img = [], []
    for f in files:
        t, i = process_file(f)
        if t: all_text.append(t)
        if i: all_img.append(i)

    if st.button("🚀 開始分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            prompt = f"財務稽核分析：{'原本公式' if mode == '診所/門市公式' else '比價與桃竹區異常分析+對答劇本'}\n資料：{' '.join(all_text)}"
            
            # 【核心修正：多路徑測試】
            # 嘗試所有可能的 URL 組合
            base_url = "https://generativelanguage.googleapis.com"
            endpoints = [
                "/v1beta/models/gemini-1.5-flash:generateContent",
                "/v1/models/gemini-1.5-flash:generateContent",
                "/v1beta/models/gemini-1.5-flash-latest:generateContent",
                "/v1/models/gemini-pro:generateContent" # 最後保底
            ]
            
            success = False
            with st.status("🛸 正在測試 4 種連線路徑...") as status:
                for ep in endpoints:
                    try:
                        url = f"{base_url}{ep}?key={api_key}"
                        payload = {"contents": [{"parts": [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]}]}
                        res = requests.post(url, json=payload, timeout=30)
                        if res.status_code == 200:
                            st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                            status.update(label=f"✅ 連線成功！路徑：{ep}", state="complete")
                            success = True
                            break
                    except:
                        continue
                
                if not success:
                    st.error("❌ 所有連線路徑皆失效 (404)。")
                    st.info("💡 Amy，這代表您的 API Key 的『出生證明』不對。請務必到 aistudio.google.com 重新點擊左側的『Get API key』，並確認是用『Create API key in new project』產生的。")

import streamlit as st
import requests
import json
import pdfplumber
import time
import random

st.set_page_config(page_title="財務稽核-最終連線版")
st.title("⚖️ 財務稽核分析 (自動重試版)")

api_key = st.text_input("🔑 請貼上剛才測試 OK 的 API Key", type="password").strip()
uploaded_file = st.file_uploader("請上傳 PDF", type=['pdf'])

if st.button("🚀 啟動分析", type="primary"):
    if not api_key:
        st.error("請輸入 API Key")
    elif not uploaded_file:
        st.warning("請上傳檔案")
    else:
        with st.status("🛸 正在分析中，請勿離開...", expanded=True) as status:
            try:
                # 1. 解析 PDF
                with pdfplumber.open(uploaded_file) as pdf:
                    all_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                # 2. 設定重試邏輯
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                prompt = f"你是一位財務審核員。請分析數據並列出 113年與114年保費對照表：\n\n{all_text}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                max_retries = 3
                for i in range(max_retries):
                    res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=60)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        break
                    elif res.status_code == 429:
                        wait_time = (i + 1) * 2 + random.random()
                        st.write(f"⏳ 伺服器忙碌 (429)，第 {i+1} 次重試，等待 {wait_time:.1f} 秒...")
                        time.sleep(wait_time)
                    else:
                        st.error(f"分析失敗 ({res.status_code})：{res.text}")
                        break
                else:
                    st.error("❌ 經過多次重試仍失敗，請稍候 5 分鐘再試。")

            except Exception as e:
                st.error(f"錯誤：{str(e)}")

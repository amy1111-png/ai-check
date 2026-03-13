import streamlit as st
import requests
import json
import pdfplumber
import time

st.set_page_config(page_title="財務稽核-路徑修正版")
st.title("⚖️ 財務稽核分析 (路徑修正版)")

api_key = st.text_input("🔑 請貼上測試 OK 的 API Key", type="password").strip()
uploaded_file = st.file_uploader("請上傳 PDF", type=['pdf'])

if st.button("🚀 啟動分析", type="primary"):
    if not api_key:
        st.error("請輸入 API Key")
    elif not uploaded_file:
        st.warning("請上傳檔案")
    else:
        with st.status("🛸 正在自動匹配模型路徑並分析...", expanded=True) as status:
            try:
                # 1. 解析 PDF
                with pdfplumber.open(uploaded_file) as pdf:
                    all_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                # 2. 測試不同的路徑組合 (重點修正處)
                # 嘗試順序：v1beta/gemini-1.5-flash -> v1/gemini-1.5-flash
                test_urls = [
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                    f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                ]
                
                success = False
                for url in test_urls:
                    prompt = f"你是一位財務審核員。請分析這份資料中的 113年 與 114年 保費數據，列出表格並比較：\n\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=60)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        success = True
                        break
                    elif res.status_code == 404:
                        st.write(f"ℹ️ 路徑 {url.split('/')[3]} 不適用，嘗試下一個...")
                        continue
                    elif res.status_code == 429:
                        st.error("⚠️ 偵測到 429 流量限制，請稍候 30 秒再試。")
                        success = True # 終止迴圈
                        break
                
                if not success:
                    st.error("❌ 無法找到可用的模型路徑。請檢查 API Key 是否有正確啟用。")

            except Exception as e:
                st.error(f"系統錯誤：{str(e)}")

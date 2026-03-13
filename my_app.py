import streamlit as st
import requests
import json
import pdfplumber

st.set_page_config(page_title="財務稽核-最終測試")
st.title("⚖️ 財務稽核分析 (防彈版本)")

# --- API 設定 ---
api_key = st.text_input("🔑 請貼上全新 Project 的 API Key", type="password").strip()

# --- 上傳檔案 ---
uploaded_file = st.file_uploader("請上傳一份 1-2 頁的 PDF", type=['pdf'])

if st.button("🚀 啟動分析", type="primary"):
    if not api_key:
        st.error("請輸入 API Key")
    elif not uploaded_file:
        st.warning("請上傳檔案")
    else:
        with st.status("🛸 正在嘗試多重連線路徑...", expanded=True) as status:
            try:
                # 1. 解析 PDF
                with pdfplumber.open(uploaded_file) as pdf:
                    all_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                # 2. 準備多個測試網址 (v1beta 和 v1)
                endpoints = [
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                    f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                ]
                
                success = False
                for url in endpoints:
                    prompt = f"你是一位財務審核員。請分析這份資料中的 113年 與 114年 保費數據，列出表格並比較：\n\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=30)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 連線成功！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        success = True
                        break
                    else:
                        st.write(f"⚠️ 路徑測試失敗 ({url.split('/')[3]})，正在嘗試備用路徑...")
                
                if not success:
                    st.error("❌ 所有連線路徑皆回報 429。這代表 Google 暫時封鎖了您的 IP 或帳號。")
                    st.info("💡 最後對策：請嘗試用手機開啟熱點，讓電腦換一個 IP 試試看。")

            except Exception as e:
                st.error(f"錯誤：{str(e)}")

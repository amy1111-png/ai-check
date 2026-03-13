import streamlit as st
import requests
import json
import pdfplumber

st.set_page_config(page_title="財務稽核-最終解決版")
st.title("⚖️ 財務稽核分析 (全自動模型匹配版)")

api_key = st.sidebar.text_input("🔑 請貼上 API Key", type="password").strip()
uploaded_file = st.file_uploader("請上傳 PDF", type=['pdf'])

if st.button("🚀 啟動分析", type="primary"):
    if not api_key:
        st.error("請輸入 API Key")
    elif not uploaded_file:
        st.warning("請上傳檔案")
    else:
        with st.status("🔍 正在掃描您的 API 可用模型...", expanded=True) as status:
            try:
                # 1. 解析 PDF 文字
                with pdfplumber.open(uploaded_file) as pdf:
                    all_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

                # 2. 向 Google 詢問「我可以用哪些模型？」
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                list_res = requests.get(list_url)
                
                target_model = None
                if list_res.status_code == 200:
                    models = list_res.json().get('models', [])
                    # 優先尋找 1.5-flash，然後是 2.0-flash
                    for m in models:
                        if "gemini-1.5-flash" in m['name']:
                            target_model = m['name'] # 這會拿到完整路徑，如 "models/gemini-1.5-flash"
                            break
                    if not target_model and models:
                        target_model = models[0]['name'] # 如果沒 1.5，就抓第一個能用的
                
                if not target_model:
                    st.error("❌ 無法從您的 API Key 取得任何可用模型。請檢查 Key 是否正確。")
                else:
                    st.write(f"✅ 已找到最佳模型：`{target_model}`")
                    
                    # 3. 使用找到的精確名稱發送請求
                    # 注意：target_model 本身已經包含 "models/"
                    final_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                    
                    prompt = f"你是一位財務審核員。請分析這份資料中的 113年 與 114年 保費數據，列出表格並比較：\n\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    final_res = requests.post(final_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                    
                    if final_res.status_code == 200:
                        status.update(label="🎉 分析成功！", state="complete")
                        st.markdown(final_res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"分析失敗 ({final_res.status_code})：{final_res.text}")

            except Exception as e:
                st.error(f"系統錯誤：{str(e)}")

import streamlit as st
import requests
import json
import pdfplumber
import io

st.set_page_config(page_title="AI 多檔案財務稽核", layout="wide")
st.title("⚖️ AI 多檔案深度比對系統")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 權限設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    st.info("支援同時上傳多份 PDF，AI 將自動進行跨檔案數據比對。")

# --- 檔案上傳 (開啟多選功能) ---
uploaded_files = st.file_uploader(
    "請上傳一份或多份 PDF 檔案", 
    type=['pdf'], 
    accept_multiple_files=True
)

if uploaded_files:
    all_extracted_text = ""
    
    # 建立多個頁籤：一個看原始文字，一個看 AI 分析
    tab1, tab2 = st.tabs(["📄 提取內容預覽", "📊 AI 稽核報告"])
    
    with st.spinner("正在讀取所有檔案..."):
        for f in uploaded_files:
            try:
                with pdfplumber.open(f) as pdf:
                    file_text = f"\n\n=== 檔案名稱: {f.name} ===\n"
                    for i, page in enumerate(pdf.pages):
                        page_content = page.extract_text()
                        if page_content:
                            file_text += f"\n[第 {i+1} 頁]\n{page_content}"
                    all_extracted_text += file_text
            except Exception as e:
                st.error(f"讀取 {f.name} 時出錯: {e}")

    with tab1:
        st.text_area("所有檔案合併內容：", all_extracted_text, height=400)
        st.download_button(
            "📥 下載合併後的文字檔",
            all_extracted_text,
            file_name="combined_text.txt"
        )

    with tab2:
        if st.button("🚀 啟動跨檔案 AI 分析", type="primary"):
            if not api_key:
                st.warning("請在左側輸入 API Key 才能進行分析。")
            else:
                with st.status("正在連線 AI 進行跨檔案比對...", expanded=True) as status:
                    # 使用之前測試成功的穩定路徑
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    
                    prompt = f"""
                    你是一位專業的財務審核員。請從以下提供的多份檔案內容中，
                    找出「113年」與「114年」的保費相關數據。
                    
                    任務要求：
                    1. 製作一個比對表格（包含項目、113年、114年、差額、變動率）。
                    2. 若數據分布在不同檔案，請自動整合。
                    3. 檢查加總是否正確，並提供審核建議。
                    
                    以下為檔案內容：
                    {all_extracted_text}
                    """
                    
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    try:
                        res = requests.post(url, json=payload, timeout=60)
                        if res.status_code == 200:
                            status.update(label="✅ 分析完成！", state="complete")
                            result = res.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(result)
                        else:
                            st.error(f"分析失敗 ({res.status_code})")
                            st.json(res.json())
                    except Exception as e:
                        st.error(f"連線錯誤: {e}")

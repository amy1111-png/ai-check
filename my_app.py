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

# 網頁基本設定
st.set_page_config(page_title="AI 財務稽核與 Word 導出", layout="wide")
st.title("⚖️ AI 財務全能稽核系統 (Word 導出版)")

# --- 側邊欄：API 與說明 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    st.info("💡 建議同時上傳：\n1. 簽呈檔案\n2. 所有的廠商報價單(PDF或照片)\n3. 114年舊資料")

# --- 檔案上傳區 ---
uploaded_files = st.file_uploader(
    "上傳所有相關檔案", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"Excel 表格數據 ({f.name}):\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1200, 1200)) 
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

# --- 核心功能：產出 Word 檔案 ---
def create_word_report(content):
    doc = Document()
    doc.add_heading('AI 財務稽核報告', 0)
    doc.add_paragraph(f"產出日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("-" * 30)
    
    # 簡單將 Markdown 內容轉入 Word (處理分段)
    for line in content.split('\n'):
        if line.startswith('###'):
            doc.add_heading(line.replace('###', '').strip(), level=2)
        elif line.startswith('##'):
            doc.add_heading(line.replace('##', '').strip(), level=1)
        else:
            doc.add_paragraph(line)
            
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 主分析邏輯 ---
if uploaded_files:
    all_texts = []
    all_imgs = []
    
    with st.spinner("🔍 正在讀取所有檔案與報價單..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 來源檔案: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    tab1, tab2 = st.tabs(["📝 檔案數據預覽", "📊 AI 稽核勾稽報告"])
    
    with tab1:
        st.subheader("📁 已提取數據匯總")
        st.text_area("合併內容：", full_context, height=300)

    with tab2:
        if st.button("🚀 開始深度勾稽與年度分析", type="primary"):
            if not api_key:
                st.error("請輸入 API Key")
            else:
                with st.status("🛸 AI 正在進行數據驗證...", expanded=True) as status:
                    # 動態偵測模型
                    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    try:
                        models_res = requests.get(list_url).json()
                        target_model = next((m['name'] for m in models_res.get('models', []) if 'flash' in m['name']), "models/gemini-1.5-flash")
                        
                        # 核心指令：加強驗證比對
                        prompt = f"""
                        你是一位嚴謹的財務審核員。請針對提供的資料進行「三方勾稽」與「年度比對」。

                        【驗證重點】：
                        1. 請逐一核對各廠商提供的「原始報價單檔案」中的金額，與「簽呈」中的數字是否完全相符。
                        2. 檢查 115年 預算總額 $489,000 的加總是否正確，細項有無遺漏。
                        3. 如果有找到任何「報價單與簽呈不一致」的地方，請用【‼️錯誤警告】明顯標示。
                        4. 比對 115年 與 114年 的費用差異。

                        【報告格式】：
                        - 勾稽驗證結果
                        - 115 vs 114 年度比對表
                        - 變動原因分析
                        - 審核建議

                        以下為檔案內容：
                        {full_context}
                        """
                        
                        user_parts = [{"text": prompt}]
                        for b64 in all_imgs:
                            user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                        
                        final_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                        res = requests.post(final_url, json={"contents": [{"parts": user_parts}]}, timeout=120)
                        
                        if res.status_code == 200:
                            status.update(label="✅ 分析完成！", state="complete")
                            result_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(result_text)
                            
                            # --- 下載 Word 檔案 ---
                            st.divider()
                            st.subheader("📥 匯出專業報告")
                            word_data = create_word_report(result_text)
                            
                            st.download_button(
                                label="📥 下載 Word 稽核報告 (.docx)",
                                data=word_data,
                                file_name=f"115年度財務稽核報告_{time.strftime('%Y%m%d')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        else:
                            st.error(f"分析失敗：{res.text}")
                    except Exception as e:
                        st.error(f"異常：{str(e)}")

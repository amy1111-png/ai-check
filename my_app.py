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
st.title("⚖️ AI 財務全能稽核系統 (Gemini 3 專版)")

# --- 側邊欄：API 與說明 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    st.info("💡 提醒：\n1. 請上傳 114年 與 115年 檔案。\n2. 系統會自動比對金額差異。")

# --- 檔案處理 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return f"\n--- [文件內容: {f.name}] ---\n" + "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"\n--- [表格內容: {f.name}] ---\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return f"\n--- [Word 內容: {f.name}] ---\n" + "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1200, 1200)) 
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"\n[附件圖片: {f.name}]\n", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

# --- Word 導出功能 ---
def create_word_report(content):
    doc = Document()
    doc.add_heading('AI 財務稽核報告', 0)
    doc.add_paragraph(f"產出日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("-" * 30)
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
uploaded_files = st.file_uploader("上傳所有相關檔案", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    all_texts = []
    all_imgs = []
    for f in uploaded_files:
        txt, img_b64 = process_file(f)
        if txt: all_texts.append(txt)
        if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    if st.button("🚀 開始深度勾稽與年度分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            with st.status("🛸 Gemini 3 正在進行數據驗證...", expanded=True) as status:
                # 【關鍵修正】針對您的帳號鎖定 Gemini 3 Flash Preview 路徑
                final_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
                
                prompt = f"""
                你是一位資深財務稽核。請針對提供的資料進行「跨年度數據勾稽」與「文件比對」。

                【任務重點】：
                1. **自動識別總額**：主動識別 114年(2025) 與 115年(2026) 簽呈中的預算總額，計算增減額與百分比。
                2. **三方勾稽**：核對廠商報價單細項加總，是否與簽呈總額吻合。
                3. **文字糾錯**：自動修正文件中的錯別字（如：辨識錯誤產生的怪詞）。
                4. **稅務提醒**：確認報價是否含 5% 營業稅，給出稅務建議。

                【報告格式】：
                ## 財務審核結論 (含年度增減對比)
                ## 勾稽驗證細節 (報價單 vs 簽呈)
                ## 文字與計算糾錯建議
                ## 專業反問台詞 (代表財務詢問承辦人)

                以下為檔案內容：
                {full_context}
                """
                
                user_parts = [{"text": prompt}]
                for b64 in all_imgs:
                    user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                try:
                    res = requests.post(final_url, json={"contents": [{"parts": user_parts}]}, timeout=120)
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        result_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(result_text)
                        
                        st.divider()
                        st.subheader("📥 匯出報告")
                        word_data = create_word_report(result_text)
                        st.download_button(
                            label="📥 下載 Word 稽核報告 (.docx)",
                            data=word_data,
                            file_name=f"財務稽核報告_{time.strftime('%Y%m%d')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    else:
                        st.error(f"連線失敗：{res.json().get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"連線異常：{str(e)}")

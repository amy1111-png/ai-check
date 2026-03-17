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
st.set_page_config(page_title="AI 財務稽核系統", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    # 模式切換：確保原本成功的邏輯永遠在那裡
    analysis_mode = st.radio(
        "選擇分析公式：",
        ["1. 診所/門市專用 (原本最成功的)", "2. 智慧萬用風格 (保險/維修/稅務)"],
        index=0
    )
    st.divider()
    st.caption("v2.1 穩定版")

# --- 核心檔案處理函數 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                return text, None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"Excel數據({f.name}):\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1000, 1000))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法讀取檔案: {f.name}", None
    return "", None

def create_word(content):
    doc = Document()
    doc.add_heading('AI 財務稽核報告', 0)
    for line in content.split('\n'):
        if line.startswith('##'):
            doc.add_heading(line.replace('#','').strip(), level=1)
        else:
            doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 上傳區 ---
files = st.file_uploader("上傳所有相關單據", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    for f in files:
        t, i = process_file(f)
        if t: all_txt.append(t)
        if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 開始執行分析", type="primary"):
        if not api_key:
            st.error("請先輸入 API Key")
        else:
            # 根據模式決定 Prompt
            if "診所/門市" in analysis_mode:
                prompt = f"""你是一位財務審核員。核對報價單與簽呈。
                最後請嚴格按照以下格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年額]元增加約[百分比]，係[原因]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市金額]元。
                資料：{context}"""
            else:
                prompt = f"""你是一位財務審核員。請依據資料性質(維修/保險/軟體/稅務)彈性產出結論。
                參考範例風格：
                - 比對年度金額與人數異動原因。
                - 提醒國外Invoice稅務風險(5%營業稅)。
                - 標示附件公式錯誤。
                ## 財務審核結論
                (請以此標題開始撰寫最適合的專業結語)
                資料：{context}"""

            with st.status("分析中...") as status:
                # 使用最穩定的 1.5 Flash 接口
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                parts = [{"text": prompt}]
                for b64 in all_img:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                try:
                    res = requests.post(url, json={"contents": [{"parts": parts}]})
                    res_json = res.json()
                    ans = res_json['candidates'][0]['content']['parts'][0]['text']
                    
                    st.markdown(ans)
                    st.download_button("📥 下載 Word 報告", create_word(ans), "Report.docx")
                    status.update(label="分析成功！", state="complete")
                except Exception as e:
                    st.error(f"發生錯誤：{str(e)}")
                    st.write(res_json) # 顯示錯誤細節方便排錯

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

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務稽核系統", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄：API Key 與 模式選擇 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    # 讓使用者可以選擇要跑哪一種邏輯
    analysis_mode = st.radio(
        "選擇稽核邏輯：",
        ["原本成功公式 (診所/門市專用)", "全新彈性風格 (智慧判定萬用型)"],
        index=0
    )
    st.divider()
    st.info("💡 提示：若遇到 404 錯誤，請檢查 API Key 是否正確。")

# --- 3. 核心處理函數 ---
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
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return f"讀取 {f.name} 失敗", None
    return "", None

def create_word(content):
    doc = Document()
    doc.add_heading('AI 財務稽核分析報告', 0)
    for line in content.split('\n'):
        if line.strip().startswith('##'):
            doc.add_heading(line.replace('#','').strip(), level=1)
        elif line.strip():
            doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 4. 主介面：檔案上傳 ---
files = st.file_uploader("上傳簽呈、報價單或附件照片", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    with st.spinner("🔍 正在讀取檔案內容..."):
        for f in files:
            t, i = process_file(f)
            if t: all_txt.append(t)
            if i: all_img.append(i)
    
    context_data = "\n\n".join(all_txt)

    if st.button("🚀 啟動稽核分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key 以繼續")
        else:
            # 設定 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"""你是一位嚴謹的財務審核員。最後請務必嚴格使用此格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年額]元增加約[百分比]，係[原因]所致。
                2.費用由各家合作診所自行申請([診小計]元)，大學光僅須負擔[門市小計]元。
                
                資料數據：
                {context_data}"""
            else:
                prompt = f"""你是一位財務審核專家。請分析資料並彈性產出結論。
                請參考風格：比對年度增減、提醒稅務風險(5%營業稅)、人數變動影響、公式糾錯。
                ## 財務審核結論
                (請根據資料彈性撰寫最專業的結語)
                
                資料數據：
                {context_data}"""

            with st.status("🛸 AI 正在分析數據...") as status:
                # 使用最穩定的 v1beta 介面，這在大部分帳號都通用
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                user_parts = [{"text": prompt}]
                for b64 in all_img:
                    user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                payload = {"contents": [{"parts": user_parts}]}
                
                try:
                    res = requests.post(url, json=payload, timeout=90)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        ans_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans_text)
                        
                        st.divider()
                        st.download_button("📥 下載 Word 報告", create_word(ans_text), "Audit_Report.docx")
                    else:
                        st.error(f"API 出錯 ({res.status_code}): {res_json.get('error', {}).get('message', '未知錯誤')}")
                        st.json(res_json)
                except Exception as e:
                    st.error(f"系統錯誤：{str(e)}")

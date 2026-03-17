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
st.set_page_config(page_title="AI 財務稽核系統 (安全測試版)", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 側邊欄：API 與 模式切換 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    # 【關鍵：安全開關】讓你可以隨時切換回原本成功的邏輯
    analysis_mode = st.radio(
        "選擇稽核公式：",
        ["原本成功公式 (診所/門市專用)", "全新彈性公式 (智慧判定五大風格)"],
        index=0,
        help="如果你擔心新功能失敗，請選第一個。想嘗試新功能請選第二個。"
    )
    
    st.divider()
    st.info("💡 建議：若是處理例行消防簽呈，用原本公式即可；若是保險、軟體或維修，請試試全新公式。")

# --- 檔案處理與 Word 導出函數 (保留不變) ---
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

def create_word_report(content):
    doc = Document()
    doc.add_heading('AI 財務稽核報告', 0)
    for line in content.split('\n'):
        if line.strip().startswith('###'):
            doc.add_heading(line.replace('###', '').strip(), level=2)
        elif line.strip().startswith('##'):
            doc.add_heading(line.replace('##', '').strip(), level=1)
        elif line.strip():
            doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 主程式區 ---
uploaded_files = st.file_uploader("上傳簽呈、附件或報價單", type=['pdf', 'docx', 'xlsx', 'png', 'jpg'], accept_multiple_files=True)

if uploaded_files:
    all_texts = []
    all_imgs = []
    with st.spinner("🔍 正在解析檔案..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 來源: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)
    full_context = "\n\n".join(all_texts)

    if st.button("🚀 開始分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # --- 根據選擇的模式設定不同的 Prompt ---
            if analysis_mode == "原本成功公式 (診所/門市專用)":
                prompt = f"""
                你是一位嚴謹的財務審核員。請核對報價單與簽呈。
                報告最後請務必使用此格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年總額]元增加約[百分比]，係[原因]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市金額]元。
                
                資料內容：{full_context}
                """
            else:
                prompt = f"""
                你是一位嚴謹的財務審核員。請根據資料性質（保修、保險、軟體、消防）從以下五種風格中自動選擇最適合的撰寫結論：
                風格1: 比對增減原因。
                風格2: 權責分攤(A自行申請/B公司負擔)。
                風格3: 國外軟體稅務風險(Invoice 5%)。
                風格4: 人數異動導致保費變動。
                風格5: 附件公式糾錯與補充。
                
                ## 財務審核結論
                (請根據資料彈性產出最專業的結語)
                
                資料內容：{full_context}
                """

            with st.status("🛸 AI 正在分析...", expanded=True) as status:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}] + 
                                 [{"inline_data": {"mime_type": "image/jpeg", "data": b}} for b in all_imgs]
                    }]
                }
                res = requests.post(api_url, json=payload)
                if res.status_code == 200:
                    status.update(label="✅ 分析完成", state="complete")
                    result_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(result_text)
                    st.download_button("📥 下載 Word 報告", data=create_word_report(result_text), file_name="稽核報告.docx")
                else:
                    st.error("分析失敗")

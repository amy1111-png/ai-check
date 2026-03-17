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
st.set_page_config(page_title="AI 財務智慧稽核系統 v3.5", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄：API 與 模式設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    analysis_mode = st.radio(
        "選擇稽核邏輯：",
        ["原本成功公式 (診所/門市專用)", "深度疑點分析 (含桃竹區/跨區詢問劇本)"],
        index=1,
        help="模式二會自動偵測多家廠商比價、不合理檢核點，並產出專業對答劇本。"
    )
    st.divider()
    st.info("💡 若出現 Error，請點右下角 Manage app -> Reboot 重啟。")

# --- 3. 核心處理函數 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"表格數據({f.name}):\n{df.to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800)) # 縮圖以節省記憶體，避免 Oh no 錯誤
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析檔案: {f.name}", None
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
files = st.file_uploader("上傳簽呈、報價單或附件照片 (PDF/Excel/圖片)", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    with st.spinner("🔍 檔案解析中..."):
        for f in files:
            t, i = process_file(f)
            if t: all_txt.append(t)
            if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 啟動智慧稽核分析", type="primary"):
        if not api_key:
            st.error("請在左側輸入 API Key")
        else:
            # 建立針對性的 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"""你是一位嚴謹的財務審核員。核對報價單與簽呈。
                最後請嚴格按照以下格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年總額]元增加約[百分比]，係[原因]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市小計]元。
                資料內容：{context}"""
            else:
                prompt = f"""你是一位資深財務稽核主管。請分析多份報價單資料，並產出以下章節：
                1. ## 財務審核結論：
                   - 注意：若有兩份以上報價單，請進行「比價分析」而非年度比較。
                   - 標註總保費/費用，指出選商邏輯。
                   - 提醒稅務(保險免稅、軟體/工程款5%營業稅)。
                
                2. ## 不合理檢核點：
                   - 針對「新區域(桃竹區)」的單價異常或跨區價差進行質疑。
                   - 檢查附件公式是否有誤(如附件四公式誤植)。
                
                3. ## 建議詢問劇本：
                   - 提供給申請人的詢問台詞。針對價差、新點費用增加等問題，要求對方提供具體說明。
                
                資料內容：{context}"""

            with st.status("🛸 AI 深度勾稽中...") as status:
                # 【關鍵修正】使用官方標準 v1beta 路徑，避免 404
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                parts = [{"text": prompt}]
                for b64 in all_img:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                payload = {"contents": [{"parts": parts}]}
                headers = {"Content-Type": "application/json"}
                
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=120)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        ans = res_json['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans)
                        st.divider()
                        st.download_button("📥 下載 Word 報告", create_word(ans), "Audit_Report.docx")
                    else:
                        st.error(f"API 錯誤 ({res.status_code}): {res_json.get('error', {}).get('message', '未知錯誤')}")
                        st.write("請確認您的 API Key 是否有效，或嘗試 Reboot App。")
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

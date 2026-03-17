import streamlit as st
import requests
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務智慧稽核系統", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    analysis_mode = st.radio(
        "選擇稽核邏輯：",
        ["原本成功公式 (診所/門市專用)", "深度疑點分析 (含桃竹區/跨區詢問劇本)"],
        index=1,
        help="模式二會自動偵測多家廠商價差、不合理檢核點，並產出對答劇本。"
    )
    st.divider()
    st.caption("版本: v3.0 (對答強化版)")

# --- 3. 核心功能定義 ---
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
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析檔案: {f.name}", None
    return "", None

# --- 4. 主介面 ---
files = st.file_uploader("上傳所有相關報價單、簽呈、附件", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    with st.spinner("🔍 檔案掃描中..."):
        for f in files:
            t, i = process_file(f)
            if t: all_txt.append(t)
            if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 開始智慧稽核", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # 建立針對性的 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"""你是一位財務審核員。核對報價單與簽呈。
                最後請嚴格按照以下格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年總額]元增加約[百分比]，係[原因]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市小計]元。
                資料內容：{context}"""
            else:
                prompt = f"""你是一位資深財務稽核主管。請分析多份報價單資料，並產出以下章節：
                1. ## 財務審核結論：
                   - 若提供多家廠商，請進行「比價分析」而非年度比較。
                   - 標註總保費/總工程費，並指出最低價與選商邏輯。
                   - 提醒稅務(如保險免營業稅、工程款5%營業稅)。
                
                2. ## 不合理檢核點 (稽核發現)：
                   - 找出金額異常、不同區域(如桃竹區 vs 南區)的單價差異、或附件公式錯誤。
                   - 針對「新區域(桃竹區)」的費用合理性進行質疑。
                
                3. ## 建議詢問劇本 (給申請人)：
                   - 針對上述不合理點，提供專業的詢問台詞。
                   - 語氣需專業，迫使申請人提供具體數據(如：樓地板面積、出險紀錄等)。
                
                資料內容：{context}"""

            with st.status("🛸 AI 正在拆解複雜邏輯...") as status:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]
                
                try:
                    res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=120)
                    if res.status_code == 200:
                        ans = res.json()['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 深度分析完成", state="complete")
                        st.markdown(ans)
                    else:
                        st.error(f"API 錯誤: {res.text}")
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

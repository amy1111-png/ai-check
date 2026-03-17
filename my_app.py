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
st.set_page_config(page_title="AI 財務稽核系統 v2.2", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    # 模式切換：保留成功的舊邏輯，同時測試新功能
    analysis_mode = st.radio(
        "選擇稽核邏輯：",
        ["原本成功公式 (診所/門市專用)", "全新彈性風格 (智慧判定萬用型)"],
        index=0,
        help="診所模式會嚴格執行您指定的兩段式總結；彈性模式則會根據檔案內容自動調整口吻。"
    )
    st.divider()
    st.caption("狀態：穩定運行中 (Gemini 1.5 Flash)")

# --- 檔案處理函數 ---
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
            img.save(buf, format="JPEG", quality=80)
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

# --- Word 導出函數 ---
def create_word(content):
    doc = Document()
    doc.add_heading('AI 財務稽核分析報告', 0)
    doc.add_paragraph(f"產出日期: {time.strftime('%Y-%m-%d')}")
    
    for line in content.split('\n'):
        if line.strip().startswith('##'):
            doc.add_heading(line.replace('#','').strip(), level=1)
        elif line.strip().startswith('###'):
            doc.add_heading(line.replace('#','').strip(), level=2)
        elif line.strip():
            doc.add_paragraph(line)
            
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 主程式區 ---
files = st.file_uploader("上傳簽呈、附件或報價單", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    with st.spinner("🔍 檔案解析中..."):
        for f in files:
            t, i = process_file(f)
            if t: all_txt.append(t)
            if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 開始智慧稽核", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # 根據選擇設定不同 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"""你是一位嚴謹的財務審核員。請核對報價單與簽呈。
                報告最後請務必嚴格使用此格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年總額]元增加約[百分比]，係[原因分析]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市小計]元。
                
                待稽核數據如下：
                {context}"""
            else:
                prompt = f"""你是一位財務審核專家。請分析資料並根據業務性質產出結論。
                請參考以下風格進行彈性撰寫：
                - 維修/保養案：比對年度增減%與原因。
                - 保險案：分析人數變動對保費的影響。
                - 國外採購：提醒 Invoice 稅務風險(5%營業稅)與抬頭規範。
                - 錯誤偵測：標示附件公式計算錯誤或金額不符。
                
                ## 財務審核結論
                (請根據上傳內容選擇最適合的風格撰寫)
                
                待稽核數據如下：
                {context}"""

            with st.status("🛸 AI 思考中...") as status:
                # 修正後的 API URL (v1beta 格式)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}] + 
                                 [{"inline_data": {"mime_type": "image/jpeg", "data": b}} for b in all_img]
                    }]
                }
                
                try:
                    res = requests.post(url, json=payload, timeout=120)
                    res_data = res.json()
                    
                    if res.status_code == 200:
                        ans = res_data['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans)
                        
                        st.divider()
                        st.download_button(
                            "📥 下載 Word 報告", 
                            data=create_word(ans), 
                            file_name=f"稽核報告_{time.strftime('%H%M%S')}.docx"
                        )
                    else:
                        st.error(f"API 錯誤: {res_data.get('error', {}).get('message', '未知錯誤')}")
                        st.expander("詳細錯誤碼").write(res_data)
                except Exception as e:
                    st.error(f"執行失敗：{str(e)}")

import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

# 1. 基礎設定
st.set_page_config(page_title="AI 財務稽核", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# 2. 側邊欄設定
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    mode = st.radio("選擇模式", ["診所/門市公式", "智慧彈性總結"], index=0)

# 3. 檔案處理 (極簡版)
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"表格數據:\n{df.to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析: {f.name}", None
    return "", None

# 4. 主程式
files = st.file_uploader("上傳檔案", accept_multiple_files=True)

if files:
    all_txt = []
    all_img = []
    for f in files:
        t, i = process_file(f)
        if t: all_txt.append(t)
        if i: all_img.append(i)
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 開始分析", type="primary"):
        if not api_key:
            st.warning("請輸入 API Key")
        else:
            # 建立 Prompt
            if mode == "診所/門市公式":
                prompt = f"你是財務審核員。核對資料後請依此格式總結：\n## 財務審核結論\n1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年額]元增加約[百分比]，係[原因]所致。\n2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市小計]元。\n\n資料內容：{context}"
            else:
                prompt = f"你是財務專家。請依資料性質(維修/保險/稅務)彈性寫結論。## 財務審核結論\n(請根據內容彈性撰寫，包含年度增減、稅務風險或公式錯誤等重點)\n\n資料內容：{context}"

            with st.status("分析中...") as status:
                # 使用最穩定的 v1beta 路徑
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                parts = [{"text": prompt}]
                for b64 in all_img:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                try:
                    res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=60)
                    res_json = res.json()
                    if res.status_code == 200:
                        ans = res_json['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 完成", state="complete")
                        st.markdown(ans)
                    else:
                        st.error(f"錯誤: {res_json.get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"連線失敗: {str(e)}")

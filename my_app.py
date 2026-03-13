import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 財務稽核-最終修復版", layout="wide")
st.title("⚖️ AI 全能稽核 (修復 404 路徑問題)")

with st.sidebar:
    api_key = st.text_input("🔑 請貼上那把【之前成功過】的 Key", type="password").strip()

uploaded_files = st.file_uploader(
    "上傳 PDF, Word, Excel 或照片", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def get_data(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"表格數據:\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1024, 1024)) # 限制尺寸以增加穩定性
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"錯誤: {str(e)}", None
    return "", None

if uploaded_files:
    all_txt = []
    all_img_parts = []
    for f in uploaded_files:
        t, i = get_data(f)
        if t: all_txt.append(t)
        if i: all_img_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": i}})

    context = "\n\n".join(all_txt)
    
    if st.button("🚀 啟動分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            with st.status("🛸 正在使用【穩定版路徑】傳輸數據...", expanded=True) as status:
                # 組合 Payload
                # 重點：文字必須放在第一個 Part
                user_parts = [{"text": f"你是一位財務審核員。請核對以下資料中的 113年 與 114年 保費數據：\n\n{context}"}]
                user_parts.extend(all_img_parts)
                
                payload = {"contents": [{"parts": user_parts}]}
                
                # 這是針對「多模態」最穩定的 v1beta 路徑格式
                # 注意：模型名稱必須是 gemini-1.5-flash，不能帶後綴
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                res = requests.post(url, json=payload, timeout=60)
                
                if res.status_code == 200:
                    status.update(label="✅ 分析成功！", state="complete")
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                elif res.status_code == 404:
                    # 如果還是 404，嘗試將「圖片」拿掉只傳文字，測試是否是圖片導致路徑失效
                    st.warning("⚠️ 偵測到路徑異常，嘗試改用『純文字模式』自動修復...")
                    payload_text_only = {"contents": [{"parts": [{"text": f"分析以下文字數據：\n{context}"}]}]}
                    res_retry = requests.post(url, json=payload_text_only)
                    if res_retry.status_code == 200:
                        st.markdown("### (僅文字分析結果)\n" + res_retry.json()['candidates'][0]['content']['parts'][0]['text'])
                        status.update(label="✅ 文字模式分析完成", state="complete")
                    else:
                        st.error(f"修復失敗: {res_retry.text}")
                else:
                    st.error(f"失敗 ({res.status_code}): {res.text}")

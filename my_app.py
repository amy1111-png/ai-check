import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

st.set_page_config(page_title="AI 財務稽核-最終解決版", layout="wide")
st.title("⚖️ AI 財務稽核 (自動路徑匹配版)")

api_key = st.sidebar.text_input("🔑 請貼上 API Key", type="password").strip()
uploaded_files = st.file_uploader("上傳 PDF, Word, Excel 或照片", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return f"Excel數據:\n{df.to_string()}", None
        elif fname.endswith('.docx'):
            doc = Document(f)
            return "\n".join([p.text for p in doc.paragraphs]), None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e: return f"錯誤: {str(e)}", None
    return "", None

if uploaded_files:
    all_txt = []
    all_img_parts = []
    for f in uploaded_files:
        t, i = process_file(f)
        if t: all_txt.append(t)
        if i: all_img_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": i}})
    
    context = "\n\n".join(all_txt)

    if st.button("🚀 啟動診斷並分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            with st.status("🔍 正在偵測模型路徑...", expanded=True) as status:
                # --- 第一步：抓取正確的模型名稱 ---
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                try:
                    models_res = requests.get(list_url).json()
                    # 從清單中找出包含 flash 的第一個模型
                    target_model = next((m['name'] for m in models_res.get('models', []) if 'flash' in m['name']), None)
                    
                    if not target_model:
                        # 如果找不到 flash，改找 pro
                        target_model = next((m['name'] for m in models_res.get('models', []) if 'pro' in m['name']), "models/gemini-1.5-flash")
                    
                    st.write(f"✅ 已鎖定模型名稱：`{target_model}`")
                    
                    # --- 第二步：使用正確名稱進行分析 ---
                    final_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                    user_parts = [{"text": f"你是一位財務審核員。分析以下 113年 與 114年 保費數據並比對差異：\n\n{context}"}]
                    user_parts.extend(all_img_parts)
                    
                    res = requests.post(final_url, json={"contents": [{"parts": user_parts}]}, timeout=60)
                    
                    if res.status_code == 200:
                        status.update(label="🎉 分析完成！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        st.error(f"分析失敗 ({res.status_code}): {res.text}")
                        
                except Exception as e:
                    st.error(f"連線診斷失敗: {str(e)}")

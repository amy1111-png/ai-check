import streamlit as st
import requests
import json
import base64
import pandas as pd
from docx import Document
import pdfplumber
import time
from PIL import Image
import io

st.set_page_config(page_title="AI 財務稽核大師", layout="wide")
st.title("⚖️ AI 簽呈深度分析系統 (優化版)")

# --- 第一步：API 設定 ---
st.subheader("🔑 第一步：設定 API Key")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ 已自動載入雲端 Key")
else:
    api_key = st.text_input("請貼上新的 Gemini API Key：", type="password").strip()

# --- 第二步：上傳檔案 ---
st.subheader("📤 第二步：上傳檔案")
uploaded_files = st.file_uploader("上傳簽呈 (PDF/Word/Excel/圖片)", type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- 模型偵測：優先選 1.5-flash (免費額度最高) ---
def find_valid_model(key):
    for ver in ["v1beta", "v1"]:
        list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={key}"
        try:
            r = requests.get(list_url, timeout=10)
            if r.status_code == 200:
                models = r.json().get('models', [])
                # 調整順序：1.5-flash 額度最慷慨
                for target in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
                    for m in models:
                        if target in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                            return m['name'], ver
        except:
            continue
    return None, None

# --- 圖片壓縮：省流量利器 ---
def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    # 如果是 RGBA (PNG)，轉成 RGB 才能存 JPG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # 縮放：最大寬度 1600 像素，維持比例
    max_size = 1600
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size))
    
    output = io.BytesIO()
    # 壓縮品質設為 70%，肉眼看不出差異但體積剩 1/5
    img.save(output, format="JPEG", quality=70)
    return base64.b64encode(output.getvalue()).decode('utf-8')

def process_files(files):
    text_data, images = [], []
    for f in files:
        if f.name.lower().endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                content = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        content += f"\n[P.{i+1}]\n{page_text}"
                text_data.append(f"【檔案:{f.name}】\n{content}")
        elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            # 呼叫壓縮函式
            img_b64 = compress_image(f)
            images.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
            text_data.append(f"【圖片附件:{f.name}】")
        # ... 其餘格式處理略同
    return "\n\n".join(text_data), images

# --- 第三步：分析 ---
st.divider()
if st.button("🚀 啟動稽核分析", type="primary"):
    if not api_key:
        st.error("❌ 請輸入 API Key")
    elif not uploaded_files:
        st.warning("⚠️ 請上傳檔案")
    else:
        with st.status("🛸 數據分析中，請耐心等候...", expanded=True) as status:
            model_path, api_ver = find_valid_model(api_key)
            if not model_path:
                st.error("❌ API Key 偵測失敗，請檢查 Key 是否有效")
            else:
                try:
                    all_text, all_images = process_files(uploaded_files)
                    prompt = f"你是一位財務審核員。請核對 113年 與 114年 保費數字、計算差額與百分比、檢查加總並給出審核意見。禁止給範例，請分析以下數據：\n{all_text}"
                    payload = {"contents": [{"parts": [{"text": prompt}] + all_images}]}
                    
                    final_url = f"https://generativelanguage.googleapis.com/{api_ver}/{model_path}:generateContent?key={api_key}"
                    res = requests.post(final_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=120)
                    
                    if res.status_code == 200:
                        status.update(label="✅ 分析完成！", state="complete")
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                    elif res.status_code == 429:
                        st.error("⚠️ 流量超出免費限制！請等待 1 分鐘後再試，或減少上傳的圖片數量。")
                    else:
                        st.error(f"分析失敗，錯誤代碼：{res.status_code}")
                        st.json(res.json())
                except Exception as e:
                    st.error(f"系統錯誤：{str(e)}")

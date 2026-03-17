import streamlit as st
import requests
import json
import pdfplumber
import pandas as pd
from docx import Document
from PIL import Image
import io
import base64

# 網頁基本設定
st.set_page_config(page_title="AI 財務稽核系統", layout="wide")
st.title("⚖️ AI 全能財務稽核員 (115 vs 114 年度比對版)")

# --- 側邊欄：API 與說明 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    st.info("""
    **使用說明：**
    1. 支援 PDF, Word, Excel, 圖片。
    2. 可同時上傳多份檔案進行跨檔案比對。
    3. 系統會自動鎖定最穩定的 AI 模型路徑。
    """)

# --- 檔案上傳區 ---
uploaded_files = st.file_uploader(
    "請上傳 115年與114年 的相關檔案 (可多選)", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
    """處理各種檔案格式並轉換為文字或圖片數據"""
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
            img.thumbnail((1200, 1200)) # 壓縮尺寸
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

# --- 主程式邏輯 ---
if uploaded_files:
    all_texts = []
    all_imgs = []
    
    with st.spinner("🔍 正在解析檔案內容..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 來源檔案: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    # 分頁顯示內容
    tab1, tab2 = st.tabs(["📝 內容預覽", "📊 AI 年度比對報告"])
    
    with tab1:
        st.subheader("提取出的原始數據")
        st.text_area("合併內容：", full_context, height=300)

    with tab2:
        if st.button("🚀 啟動 115 vs 114 深度分析", type="primary"):
            if not api_key:
                st.error("請在左側輸入 API Key")
            else:
                with st.status("🛸 正在進行跨檔案數據比對...", expanded=True) as status:
                    # 1. 動態偵測模型路徑
                    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    try:
                        models_res = requests.get(list_url).json()
                        target_model = next((m['name'] for m in models_res.get('models', []) if 'flash' in m['name']), "models/gemini-1.5-flash")
                        st.write(f"✅ 已鎖定模型：`{target_model}`")
                        
                        # 2. 準備分析指令 (Prompt)
                        prompt = f"""
                        你是一位專業的財務審核員。請針對提供的資料進行年度費用比對。
                        目前的目標是：比對「115年度」與「114年度」的費用（包含保費、消防檢修費等）。

                        任務要求：
                        1. 找出 115年 預計支出與 114年 實際支出的數據。
                        2. 製作一個比對表格（項目、114年金額、115年預估、差額、變動率、備註）。
                        3. 分析費用變動的主要原因（例如：新增門市、廠商報價調漲、法規更新等）。
                        4. 檢查加總是否正確，並給予財務審核建議。

                        以下為檔案內容：
                        {full_context}
                        """
                        
                        # 3. 組合多模態 Payload
                        user_parts = [{"text": prompt}]
                        for b64 in all_imgs:
                            user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                        
                        # 4. 發送請求
                        final_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                        res = requests.post(final_url, json={"contents": [{"parts": user_parts}]}, timeout=90)
                        
                        if res.status_code == 200:
                            status.update(label="✅ 分析完成！", state="complete")
                            st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        else:
                            st.error(f"分析失敗 ({res.status_code}): {res.text}")
                            
                    except Exception as e:
                        st.error(f"系統故障: {str(e)}")

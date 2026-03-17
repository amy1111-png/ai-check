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
st.set_page_config(page_title="AI 財務稽核系統", layout="wide")
st.title("⚖️ AI 全能財務稽核與自動勾稽系統")
st.caption("支援 115 vs 114 年度比對 | PDF、Excel、Word、照片自動辨識")

# --- 側邊欄：API 與說明 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    st.info("""
    **💡 操作小撇步：**
    1. **同時上傳**：建議同時上傳「115年簽呈」與「廠商原始報價單」。
    2. **跨年比對**：若有「114年資料」請一併丟入，AI 會自動做差額分析。
    3. **圖片辨識**：手機拍的報價單照片也可以直接上傳。
    """)

# --- 檔案上傳區 ---
uploaded_files = st.file_uploader(
    "上傳所有相關檔案 (簽呈、報價單、去年報表...)", 
    type=['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

def process_file(f):
    """處理各類格式並轉為文字或圖片"""
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
            return f"[圖片附件預覽: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"讀取 {f.name} 失敗: {str(e)}", None
    return "", None

# --- 主分析邏輯 ---
if uploaded_files:
    all_texts = []
    all_imgs = []
    
    with st.spinner("🔍 正在讀取所有檔案與報價單..."):
        for f in uploaded_files:
            txt, img_b64 = process_file(f)
            if txt: all_texts.append(f"--- 來源檔案: {f.name} ---\n{txt}")
            if img_b64: all_imgs.append(img_b64)

    full_context = "\n\n".join(all_texts)
    
    tab1, tab2 = st.tabs(["📝 檔案數據預覽", "📊 AI 稽核勾稽報告"])
    
    with tab1:
        st.subheader("📁 已提取數據匯總")
        st.text_area("合併內容 (AI 將閱讀以下資訊)：", full_context, height=300)

    with tab2:
        if st.button("🚀 開始全自動勾稽分析", type="primary"):
            if not api_key:
                st.error("請在左側輸入 API Key")
            else:
                with st.status("🛸 AI 正在進行三方勾稽與年度比對...", expanded=True) as status:
                    # 1. 動態偵測可用模型 (避免 404)
                    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    try:
                        models_res = requests.get(list_url).json()
                        target_model = next((m['name'] for m in models_res.get('models', []) if 'flash' in m['name']), "models/gemini-1.5-flash")
                        st.write(f"✅ 已啟動 AI 引擎：`{target_model}`")
                        
                        # 2. 定製化勾稽指令 (包含 115 vs 114 以及 報價單核對)
                        prompt = f"""
                        你是一位專業的財務審核員。請針對提供的多份資料進行「三方勾稽」與「年度比對」。

                        任務要求：
                        1. 【三方勾稽】：核對「各家廠商原始報價單」上的含稅總額，是否與「簽呈內容」中的各區金額、總計金額完全一致？如有錯誤請立刻指出。
                        2. 【年度比對】：比對「115年度」預計支出與「114年度」實際支出（包含消防費、保費等）。
                        3. 【分析變動】：找出費用增減的原因（如新增門市、場所類別變更等）。
                        4. 【報表產出】：製作一個比對表格，包含項目、114年金額、115年金額、差額、變動率、備註。
                        5. 【最後審核】：確認所有加總是否正確，並給予專業財務建議（如預算編列、合約風險）。

                        以下為檔案內容：
                        {full_context}
                        """
                        
                        # 3. 多模態封裝
                        user_parts = [{"text": prompt}]
                        for b64 in all_imgs:
                            user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                        
                        # 4. 呼叫 API
                        final_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
                        res = requests.post(final_url, json={"contents": [{"parts": user_parts}]}, timeout=120)
                        
                        if res.status_code == 200:
                            status.update(label="✅ 稽核報告產出成功！", state="complete")
                            result_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(result_text)
                            
                            # --- 下載功能 ---
                            st.divider()
                            st.subheader("📥 匯出報告")
                            st.download_button(
                                label="💾 下載分析結果 (.txt)",
                                data=result_text,
                                file_name=f"財務稽核報告_{time.strftime('%Y%m%d')}.txt",
                                mime="text/plain"
                            )
                            st.success("勾稽完成！建議同步核對各家廠商的統編與發票抬頭。")
                        else:
                            st.error(f"分析失敗：{res.text}")
                            
                    except Exception as e:
                        st.error(f"連線異常：{str(e)}")

import streamlit as st
import google.generativeai as genai
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 財務智慧稽核系統 v5.0", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    mode = st.radio("選擇稽核邏輯：", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"], index=1)
    st.caption("連線模式：Google SDK 標準版")

# --- 3. 檔案處理函數 ---
def process_file(f):
    fname = f.name.lower()
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            return f"表格數據({f.name}):\n{pd.read_excel(f).to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            return None, img # SDK 直接支援 PIL Image 物件
    except Exception as e:
        return f"無法解析: {f.name} ({str(e)})", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("上傳報價單或相關單據", accept_multiple_files=True)

if files:
    all_content = [] # 存放文字與圖片
    with st.spinner("🔍 檔案解析中..."):
        for f in files:
            t, i = process_file(f)
            if t: all_content.append(t)
            if i: all_content.append(i)

    if st.button("🚀 啟動深度分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            try:
                # 設定 API Key
                genai.configure(api_key=api_key)
                # 初始化模型 (SDK 會自動處理 models/ 前綴與版本)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 設定 Prompt
                if mode == "診所/門市公式":
                    prompt = "你是一位專業財務審核員。請核對資料並以兩段式結論總結（1.經確認... 2.費用由...）。"
                else:
                    prompt = """你是一位資深財務稽核主管。請分析報價單並產出：
                    1. 財務審核結論 (比價分析、稅務提醒)。
                    2. 不合理檢核點 (針對桃竹區等新點的異常、公式錯誤)。
                    3. 建議詢問劇本 (給申請人的專業反問台詞)。"""

                with st.status("🛸 AI 深度勾稽中...") as status:
                    # 發送請求 (SDK 支援混合文字與圖片)
                    response = model.generate_content([prompt] + all_content)
                    
                    status.update(label="✅ 分析完成", state="complete")
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"分析失敗：{str(e)}")
                if "404" in str(e):
                    st.write("提示：如果還是 404，代表您的 API Key 可能未啟用 Gemini 1.5 權限，請至 Google AI Studio 建立新 Key。")

import streamlit as st
import google.generativeai as genai
import pdfplumber
import pandas as pd
from PIL import Image
import io

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務稽核 v6.0", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上「新」的 API Key", type="password").strip()
    st.divider()
    mode = st.radio("稽核邏輯", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"], index=1)
    if st.button("🛠️ 診斷我的 API Key 權限"):
        if api_key:
            try:
                genai.configure(api_key=api_key)
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write("您的 Key 可以使用的模型清單：")
                st.json(models)
            except Exception as e:
                st.error(f"診斷失敗：{str(e)}")
        else:
            st.warning("請先輸入 Key")

# --- 3. 檔案處理 ---
def process_file(f):
    try:
        if f.name.lower().endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif f.name.lower().endswith(('.xlsx', '.xls')):
            return f"表格數據({f.name}):\n{pd.read_excel(f).to_string()}", None
        elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            return None, img
    except:
        return f"無法解析: {f.name}", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("上傳簽呈或報價單", accept_multiple_files=True)

if files:
    all_content = []
    for f in files:
        t, i = process_file(f)
        if t: all_content.append(t)
        if i: all_content.append(i)

    if st.button("🚀 啟動深度分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            try:
                genai.configure(api_key=api_key)
                # 這裡強制使用最保險的模型名稱
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 設定 Prompt
                if mode == "診所/門市公式":
                    prompt = "財務審核：核對後請用原本的兩點格式總結（1.經確認...2.費用由...）。"
                else:
                    prompt = """資深財務稽核：請分析資料，並產出：
                    1. 財務審核結論 (比價與稅務)。
                    2. 不合理檢核點 (桃竹區異常、公式誤植)。
                    3. 建議詢問劇本 (給申請人的專業反問)。"""

                with st.status("🛸 正在分析...") as status:
                    response = model.generate_content([prompt] + all_content)
                    status.update(label="✅ 分析完成", state="complete")
                    st.markdown(response.text)
            
            except Exception as e:
                st.error(f"分析失敗：{str(e)}")
                st.info("💡 如果還是 404，請確認您在 AI Studio 申請時是選擇 'Free of charge' 方案。")

import streamlit as st
import requests
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# 1. 基礎設定
st.set_page_config(page_title="AI 財務稽核-Gemini 3 專版", layout="wide")
st.title("⚖️ AI 財務全能稽核系統 (Gemini 3)")

# 2. 側邊欄
with st.sidebar:
    st.header("🔑 系統設定")
    # 請點擊妳截圖左下角的 "Get API key" 來獲取 Key
    api_key = st.text_input("請貼上新的 API Key", type="password").strip()
    st.divider()
    mode = st.radio("稽核邏輯", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"])
    st.info("💡 已依據您的截圖，將模型路徑修正為：gemini-3-flash-preview")

# 3. 檔案處理
def process_file(f):
    try:
        if f.name.lower().endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif f.name.lower().endswith(('.xlsx', '.xls')):
            return f"表格數據:\n{pd.read_excel(f).to_string()}", None
        elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return None, base64.b64encode(buf.getvalue()).decode()
    except:
        return f"無法解析檔案: {f.name}", None
    return "", None

# 4. 主程式
files = st.file_uploader("上傳簽呈、報價單或照片附件", accept_multiple_files=True)

if files:
    all_text, all_img = [], []
    for f in files:
        t, i = process_file(f)
        if t: all_text.append(t)
        if i: all_img.append(i)

    if st.button("🚀 啟動 Gemini 3 深度稽核", type="primary"):
        if not api_key:
            st.error("請在側邊欄貼上 API Key")
        else:
            # 針對妳的需求強化 Prompt
            if mode == "診所/門市公式":
                prompt = f"你是專業財務審核員。請核對資料並依格式總結：1.經確認... 2.費用由...。資料內容：\n{' '.join(all_text)}"
            else:
                prompt = f"""你是資深財務稽核主管。請針對提供的報價單與簽呈進行分析：
                1. 財務審核結論：進行比價分析，並特別針對「桃竹區(如藝文、竹北店)」的新增費用進行合理性評估。
                2. 不合理檢核點：找出金額異常、公式錯誤或跨區單價顯著差異之處。
                3. 建議詢問劇本：針對上述疑點，寫出專業且能讓申請人無法迴避的詢問台詞。
                資料內容：\n{' '.join(all_text)}"""

            # 【關鍵修復】使用截圖中顯示的模型路徑
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]
                }]
            }
            
            with st.status("🛸 Gemini 3 正在進行深度勾稽...") as status:
                try:
                    res = requests.post(url, json=payload, timeout=60)
                    if res.status_code == 200:
                        ans = res.json()['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans)
                    else:
                        st.error(f"連線失敗 ({res.status_code})")
                        st.write("錯誤詳情：", res.json().get('error', {}).get('message', '未知錯誤'))
                except Exception as e:
                    st.error(f"連線超時，請重試：{str(e)}")

import streamlit as st
import requests
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# --- 1. 頁面配置 ---
st.set_page_config(page_title="AI 萬用財務稽核系統", layout="wide")
st.title("⚖️ AI 財務全能稽核系統 (通用對比版)")

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請輸入 API Key", type="password").strip()
    st.divider()
    st.info("💡 核心邏輯：自動勾稽跨年度金額、單價漲幅與文字異常。")
    st.caption("適用情境：任何需要「今年 vs 去年」或「廠商 A vs 廠商 B」的比對案件。")

# --- 3. 檔案處理 (強化標籤化以利對比) ---
def process_file(f):
    fname = f.name.lower()
    label = f"\n\n### [來源文件: {f.name}] ###\n"
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                return label + "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()]), None
        elif fname.endswith(('.xlsx', '.xls')):
            return label + f"表格數據：\n{pd.read_excel(f).to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return f"[附件圖片: {f.name}]", base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"無法解析檔案: {f.name} ({str(e)})", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("請上傳多份文件（如：不同年份簽呈、多家報價單）", accept_multiple_files=True)

if files:
    all_text, all_img = [], []
    for f in files:
        t, i = process_file(f)
        if t: all_text.append(t)
        if i: all_img.append(i)

    if st.button("🚀 執行萬用智慧稽核", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # --- 萬用稽核 Prompt：不針對特定品項，只針對財務邏輯 ---
            prompt = f"""你是一位擁有 15 年資歷、極度細緻的資深財務稽核主管。
            請針對提供的『所有文件』進行全方位的財務勾稽分析。

            【你的稽核邏輯】
            1. **跨期數據追蹤**：主動識別不同年度(例如 114與115, 或 2025與2026)的總預算。
            2. **自動計算減法**：若存在多個年份，請計算：(今年金額 - 去年金額) = 增減額，並算出變動百分比(%)。
            3. **語意糾錯 (不限品項)**：檢查文件中是否存在明顯的 OCR 辨識錯誤、錯別字或不合常理的專業術語(例如：字體重疊導致的怪詞)。
            4. **人均/單價分析**：若有提到人數或數量，請計算單價。若單價有異常漲跌，請列為重點。

            【輸出的固定格式】
            ## 財務審核結論
            1. **數據總結**：[項目名稱]之核核。本期金額為[金額]元，前期為[金額]元，[增加/減少]了[金額]元，幅度為[百分比]%。
            2. **稅務提醒**：[判斷是否含 5% 營業稅，並給出建議]。
            
            ## 詳細稽核發現
            - **變動主因分析**：[分析為何金額會波動？是量變、價變、還是項目新增？]
            - **文件異常糾錯**：[指出檔案中語法不通、錯字、或數字計算不吻合之處]
            - **勾稽重點**：[例如：人數與採購量不符、單價高於市場行情等]

            ## 建議詢問劇本 (由妳代表財務向承辦人發問)
            - [針對上述異常點，產出 2~3 個專業、強硬且精準的反問台詞]

            資料來源內容：
            {' '.join(all_text)}"""

            # 鎖定 Gemini 3 Flash Preview
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]
                }]
            }
            
            with st.status("🛸 萬用稽核大腦運作中...") as status:
                try:
                    res = requests.post(url, json=payload, timeout=90)
                    if res.status_code == 200:
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        status.update(label="✅ 分析完成", state="complete")
                    else:
                        st.error(f"分析失敗: {res.json().get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

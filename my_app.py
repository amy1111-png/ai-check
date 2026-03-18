import streamlit as st
import requests
import pdfplumber
import pandas as pd
from PIL import Image
import io
import base64

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務智慧稽核系統 v7.0", layout="wide")
st.title("⚖️ AI 財務全能稽核系統 (跨年度/多廠商比價版)")

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    
    analysis_mode = st.radio(
        "選擇稽核情境：",
        ["年度對比 + 廠商比價 (全能模式)", "新案異常偵測 (含劇本)"],
        index=0
    )
    st.info("💡 提示：請同時選取「去年簽呈」、「今年簽呈」及「所有廠商報價單」一起上傳。")

# --- 3. 強製標籤化檔案處理 ---
def process_file(f):
    fname = f.name.lower()
    # 加入檔案名稱標籤，讓 AI 知道這份資料的來源
    label = f"\n\n===== [文件來源: {f.name}] =====\n"
    try:
        if fname.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                content = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                return label + content, None
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(f)
            return label + f"表格數據內容：\n{df.to_string()}", None
        elif fname.endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(f).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return f"[圖片附件: {f.name}]", base64.b64encode(buf.getvalue()).decode()
        # 如果是 Word 內容，建議 Amy 直接將 Word 內容轉存 PDF 上傳，或在此擴充 docx 讀取
    except Exception as e:
        return f"無法解析檔案: {f.name} ({str(e)})", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("選取所有相關檔案 (可多選)", accept_multiple_files=True)

if files:
    all_text, all_img = [], []
    for f in files:
        t, i = process_file(f)
        if t: all_text.append(t)
        if i: all_img.append(i)

    if st.button("🚀 開始全維度分析", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # --- 極致強化版 Prompt：要求三方會審 ---
            prompt = f"""你是一位擁有15年經驗的資深財務稽核。
            
            【你的任務】
            你手上現在有多份文件，包含「114年度簽呈」、「115年度簽呈」以及「各家廠商報價單」。
            請執行以下連環勾稽：
            1. **年度對比**：找出114年與115年的採購金額差異、人數變動。
            2. **比價分析**：從所有報價單中，列出不同廠商的單價對照表，並驗證選商(如：奎瑞斯)是否為最低價或最優選。
            3. **公式驗算**：重新計算 831,000 元的加總是否正確，並加上 5% 營業稅提醒。
            
            【輸出的固定格式】
            ## 財務審核結論 (舉一反三版)
            1. 經確認[項目名稱]之內容。115年總額為[金額]元，較114年[金額]元[增加/減少][金額]元(幅度[百分比]%)。
            2. 費用分攤：本案共[數量]人，診所負擔[金額]元，公司負擔[金額]元。
            
            ## 比價與勾稽發現
            - **廠商比價表**：[列出 A 廠商 vs B 廠商 vs 歷史廠商的單價差異]
            - **不合理點**：[例如：某品項單價漲幅過高、公式錯誤、或像「揮子」等贅字糾錯]
            
            ## 建議詢問劇本 (對應不合理點)
            - [針對漲幅或單價異常，提供專業的反問台詞]
            
            資料來源：
            {' '.join(all_text)}"""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": i}} for i in all_img]
                }]
            }
            
            with st.status("🛸 正在執行三方會審(年度對比+多廠比價)...") as status:
                try:
                    res = requests.post(url, json=payload, timeout=90)
                    if res.status_code == 200:
                        st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                        status.update(label="✅ 分析完成", state="complete")
                    else:
                        st.error(f"分析失敗: {res.json().get('error', {}).get('message', '未知錯誤')}")
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

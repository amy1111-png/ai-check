import streamlit as st
import google.generativeai as genai
import pdfplumber
import pandas as pd
from PIL import Image
import io

# --- 1. 基本設定 ---
st.set_page_config(page_title="AI 財務稽核 v5.5", layout="wide")
st.title("⚖️ AI 財務全能稽核系統")

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("🔑 系統設定")
    api_key = st.text_input("請貼上 API Key", type="password").strip()
    st.divider()
    mode = st.radio("選擇稽核邏輯：", ["診所/門市公式", "深度疑點分析 (含桃竹區劇本)"], index=1)
    st.caption("連線模式：全自動相容偵測")

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
    except Exception as e:
        return f"無法解析: {f.name}", None
    return "", None

# --- 4. 主程式 ---
files = st.file_uploader("上傳檔案", accept_multiple_files=True)

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
                
                # 【關鍵修復：窮舉測試邏輯】
                # 嘗試不同的模型名稱組合，避開 404
                model_names = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-flash-latest']
                success = False
                
                with st.status("🛸 正在尋找可用連線路徑...") as status:
                    for name in model_names:
                        try:
                            model = genai.GenerativeModel(name)
                            # 測試 Prompt
                            prompt = "分析資料並給出稽核結論與詢問劇本：" if mode != "診所/門市公式" else "核對資料並依格式總結："
                            response = model.generate_content([prompt] + all_content)
                            
                            status.update(label=f"✅ 已透過 {name} 連線成功", state="complete")
                            st.markdown(response.text)
                            success = True
                            break # 成功就跳出循環
                        except Exception as inner_e:
                            if "404" in str(inner_e):
                                continue # 404 就換下一個名字試
                            else:
                                raise inner_e # 其他錯誤就報出來
                    
                    if not success:
                        st.error("所有模型路徑均返回 404。這通常代表您的 API Key 沒有該模型的存取權限。")
                        st.info("💡 解決建議：請到 Google AI Studio (aistudio.google.com) 重新點擊 'Create API key'，並確認您可以手動在該網頁跑通 Gemini 1.5 Flash。")
            
            except Exception as e:
                st.error(f"系統錯誤：{str(e)}")

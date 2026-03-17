if st.button("🚀 開始智慧稽核", type="primary"):
        if not api_key:
            st.error("請輸入 API Key")
        else:
            # 根據模式設定不同 Prompt
            if "原本成功公式" in analysis_mode:
                prompt = f"""你是一位嚴謹的財務審核員。請核對報價單與簽呈。
                報告最後請務必嚴格使用此格式總結：
                ## 財務審核結論
                1.經確認報價單及簽呈內容無誤，本年度合作診所共[數量]間，另含門市[數量]間，費用共[總額]元。較114年度[去年總額]元增加約[百分比]，係[原因分析]所致。
                2.費用由各家合作診所自行申請([診所小計]元)，大學光僅須負擔[門市小計]元。
                
                待稽核數據如下：
                {context}"""
            else:
                prompt = f"""你是一位財務審核專家。請分析資料並根據業務性質產出結論。
                請參考以下風格進行彈性撰寫：
                - 維修/保養案：比對年度增減%與原因。
                - 保險案：分析人數變動對保費的影響。
                - 國外採購：提醒 Invoice 稅務風險(5%營業稅)與抬頭規範。
                - 錯誤偵測：標示附件公式計算錯誤或金額不符。
                
                ## 財務審核結論
                (請根據內容選擇最適合風格，如有多項重點可分點敘述)
                
                待稽核數據如下：
                {context}"""

            with st.status("🛸 AI 思考中...") as status:
                # 【關鍵修正】改用 v1 穩定版路徑
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                # 確保圖片與文字正確組合
                user_parts = [{"text": prompt}]
                for b64 in all_img:
                    user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                
                payload = {
                    "contents": [{"parts": user_parts}]
                }
                
                headers = {"Content-Type": "application/json"}
                
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=120)
                    res_data = res.json()
                    
                    if res.status_code == 200:
                        ans = res_data['candidates'][0]['content']['parts'][0]['text']
                        status.update(label="✅ 分析完成", state="complete")
                        st.markdown(ans)
                        
                        st.divider()
                        st.download_button(
                            "📥 下載 Word 報告", 
                            data=create_word(ans), 
                            file_name=f"稽核報告_{time.strftime('%Y%m%d')}.docx"
                        )
                    else:
                        # 顯示具體錯誤
                        st.error(f"API 錯誤碼 {res.status_code}")
                        st.write(res_data)
                except Exception as e:
                    st.error(f"連線失敗：{str(e)}")

import yfinance as yf
import requests
import json

# --- 🔑 密鑰 ---
LINE_ACCESS_TOKEN = 'au4RHmJTa0taGK4wCfLMlAt4/tJCEeQhRkvjhPxtts4jn4VBdPQNn8lt7NtCo88s/IaW3jaWSM9Xhan5f8CAPcgdUIhb6OzcNNQECWpKhEy8XMPAHzHAF6fLO+fZiPfk2MCzDxvEFgVZyhf+0DJGowdB04t89/1O/w1cDnyilFU=' 
MY_USER_ID = 'U3d7020cc4eefdca67e5a160feca76446'

# --- 📈 股票與大盤清單 (含中文名稱) ---
STOCK_MAP = {
    '^TWII': '🚩台股大盤',
    '006208.TW': '富邦台50',
    '00878.TW': '國泰高股息',
    '00915.TW': '凱基優選30',
    '00919.TW': '群益精選高息',
    '00929.TW': '復華科技優息',
    '00939.TW': '統一高息動能',
    '00940.TW': '元大價值高息',
    '00943.TW': 'FT臺灣高息',
    '00944.TW': '凱基臺灣50',
    '2356.TW': '英業達',
    '2883.TW': '凱基金'
}

def get_stock_report():
    msg = "📊 【台股戰報】\n"
    has_data = False
    
    for s, name in STOCK_MAP.items():
        try:
            stock = yf.Ticker(s)
            data = stock.history(period='5d')
            if data.empty or len(data) < 2:
                continue
            
            price = data['Close'].iloc[-1]
            change = price - data['Close'].iloc[-2]
            pct = (change / data['Close'].iloc[-2]) * 100
            
            icon = "🔴" if change > 0 else "🟢"
            if change == 0: icon = "⚪"
            
            if s == '^TWII':
                msg += f"{name}\n指數: {price:.0f} ({pct:+.2f}%){icon}\n"
                msg += "================"
            else:
                msg += f"\n{name} ({s[:5]})\n價位: {price:.2f} ({pct:+.2f}%){icon}"
            
            has_data = True
        except Exception as e:
            print(f"抓取 {name} 失敗: {e}")
            continue
            
    return msg if has_data else "❌ 暫時抓不到資料"

def send_to_line(text):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    payload = {
        'to': MY_USER_ID,
        'messages': [{'type': 'text', 'text': text}]
    }
    return requests.post(url, headers=headers, data=json.dumps(payload))

# --- 執行執行 ---
print("正在執行任務...")
msg = get_stock_report()
print(msg)
response = send_to_line(msg)

if response.status_code == 200:
    print("✅ 成功傳送到 LINE")
else:
    print(f"❌ 傳送失敗，原因: {response.text}")

from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# ===== CSVを読み込む =====
# 文字化け対策で encoding を明示
jiko_df = pd.read_csv('jiko.csv', encoding='utf-8')
signal_df = pd.read_csv('seigzo.csv', encoding='utf-8')

# 緯度・経度を数値に変換（文字列を安全に処理）
jiko_df['地点　緯度（北緯）'] = pd.to_numeric(jiko_df['地点　緯度（北緯）'], errors='coerce')
jiko_df['地点　経度（東経）'] = pd.to_numeric(jiko_df['地点　経度（東経）'], errors='coerce')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form['keyword']

    # --- 信号データで交差点番号を検索 ---
    signal_match = signal_df[signal_df['交差点番号'].astype(str).str.contains(keyword, case=False, na=False)]

    # --- 事故データで地点コードや路線コードを検索 ---
    jiko_match = jiko_df[
        jiko_df['地点コード'].astype(str).str.contains(keyword, case=False, na=False) |
        jiko_df['路線コード'].astype(str).str.contains(keyword, case=False, na=False)
    ]

    # --- 地図用に緯度経度を抽出 ---
    map_points = jiko_match[['地点　緯度（北緯）', '地点　経度（東経）']].dropna().to_dict(orient='records')

    return render_template('result.html',
                           keyword=keyword,
                           signal_data=signal_match.to_dict(orient='records'),
                           jiko_data=jiko_match.to_dict(orient='records'),
                           map_points=map_points,
                           jiko_count=len(jiko_match))

if __name__ == '__main__':
    app.run(debug=True)

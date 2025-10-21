from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
import os

app = Flask(__name__)

# --- データ読み込み ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
honhyo = pd.read_csv(os.path.join(DATA_DIR, 'honhyo_2024.csv'))
seigzo = pd.read_csv(os.path.join(DATA_DIR, 'seigzo.csv'))
teigi = pd.read_csv(os.path.join(DATA_DIR, 'teigi.csv'))

# --- トップページ ---
@app.route('/')
def index():
    # 地域選択や交差点検索フォームを表示
    areas = sorted(seigzo['地区名'].dropna().unique()) if '地区名' in seigzo.columns else []
    return render_template('index.html', areas=areas)

# --- 分析結果表示 ---
@app.route('/results', methods=['POST'])
def results():
    area = request.form.get('area')
    # 地域でフィルタリング
    if area and '地区名' in seigzo.columns:
        filtered = seigzo[seigzo['地区名'] == area]
    else:
        filtered = seigzo.copy()

    # 交差点ごとの事故件数集計
    if '交差点ID' in honhyo.columns:
        accident_counts = honhyo.groupby('交差点ID').size().reset_index(name='事故件数')
        merged = pd.merge(filtered, accident_counts, on='交差点ID', how='left')
    else:
        merged = filtered.copy()

    merged['事故件数'] = merged['事故件数'].fillna(0).astype(int)

    # 地図描画
    fmap = folium.Map(location=[36.0652, 136.2216], zoom_start=13)
    for _, row in merged.iterrows():
        if pd.notnull(row.get('緯度')) and pd.notnull(row.get('経度')):
            folium.CircleMarker(
                location=[row['緯度'], row['経度']],
                radius=5 + row['事故件数'] * 0.5,
                popup=f"{row.get('交差点名', '不明')}：{row['事故件数']}件",
                color="red" if row['事故件数'] > 0 else "blue",
                fill=True,
                fill_opacity=0.6
            ).add_to(fmap)

    map_html = fmap._repr_html_()
    return render_template('results.html', area=area, map_html=map_html, data=merged.to_dict(orient='records'))

# --- API形式でデータ返却（将来の分析用） ---
@app.route('/api/accidents')
def api_accidents():
    data = honhyo.to_dict(orient='records')
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)

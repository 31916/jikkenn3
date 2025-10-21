from flask import Flask, render_template, request
import pandas as pd
import folium

app = Flask(__name__)

# CSV読み込み（Windows日本語CSVの文字化け防止）
seigzo = pd.read_csv('data/seigzo.csv', encoding='utf-8-sig')
honhyo = pd.read_csv('data/honhyo.csv', encoding='utf-8-sig')

# --- トップページ ---
@app.route('/')
def index():
    # 地区名リストを取得（空白列は除外）
    areas = sorted(seigzo['地区名'].dropna().unique()) if '地区名' in seigzo.columns else []
    return render_template('index.html', areas=areas)

# --- 分析結果表示 ---
@app.route('/results', methods=['POST'])
def results():
    area = request.form.get('area')
    intersection = request.form.get('intersection')  # 交差点名検索

    # 地域でフィルタリング
    filtered = seigzo.copy()
    if area and '地区名' in filtered.columns:
        filtered = filtered[filtered['地区名'] == area]

    # 交差点名で部分一致検索（大文字小文字無視）
    if intersection and '交差点名' in filtered.columns:
        filtered = filtered[filtered['交差点名'].str.contains(intersection, case=False, na=False)]

    # 交差点ごとの事故件数集計
    if '交差点ID' in honhyo.columns:
        accident_counts = honhyo.groupby('交差点ID').size().reset_index(name='事故件数')
        merged = pd.merge(filtered, accident_counts, on='交差点ID', how='left')
    else:
        merged = filtered.copy()

    merged['事故件数'] = merged['事故件数'].fillna(0).astype(int)

    # 地図描画
    fmap = folium.Map(location=[36.0652, 136.2216], zoom_start=13)  # 中心座標を適宜変更
    for _, row in merged.iterrows():
        lat = row.get('緯度')
        lon = row.get('経度')
        if pd.notnull(lat) and pd.notnull(lon):
            folium.CircleMarker(
                location=[lat, lon],
                radius=5 + row['事故件数'] * 0.5,
                popup=f"{row.get('交差点名', '不明')}：{row['事故件数']}件",
                color="red" if row['事故件数'] > 0 else "blue",
                fill=True,
                fill_opacity=0.6
            ).add_to(fmap)

    map_html = fmap._repr_html_()
    return render_template(
        'results.html',
        area=area,
        intersection=intersection,
        map_html=map_html,
        data=merged.to_dict(orient='records')
    )

if __name__ == '__main__':
    app.run(debug=True)

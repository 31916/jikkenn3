from flask import Flask, render_template, request
import pandas as pd
import folium

app = Flask(__name__)
# 文字コード自動検出用
import chardet
def read_csv_auto(path):
    with open(path, 'rb') as f:
        result = chardet.detect(f.read(10000))
    encoding = result['encoding']
    print(f"{path} detected as {encoding}")
    return pd.read_csv(path, encoding=encoding)
# CSV読み込み（Windows日本語CSVの文字化け防止）
seigzo = pd.read_auto('data/seigzo.csv')#, encoding='utf-8-sig')
honhyo = pd.read_auto('data/honhyo_2024.csv')#, encoding='utf-8-sig')

print(seigzo.head())
print(honhyo.head())
# --- トップページ ---
@app.route('/')
def index():
    # 地区名（規制データにあれば）を取得
    areas = sorted(seigzo['都道府県コード'].dropna().unique()) if '都道府県コード' in seigzo.columns else []
    return render_template('index.html', areas=areas, selected_area="", intersection="")

# --- 分析結果表示 ---
@app.route('/results', methods=['POST'])
def results():
    area = request.form.get('area')
    intersection = request.form.get('intersection')

    # 規制データでフィルタリング
    filtered = seigzo.copy()
    if area and '都道府県コード' in filtered.columns:
        filtered = filtered[filtered['都道府県コード'] == int(area)]

    if intersection and '交差点名称(踏切名含む)' in filtered.columns:
        filtered = filtered[filtered['交差点名称(踏切名含む)'].str.contains(intersection, case=False, na=False, regex=False)]

    # 事故件数を交差点ごとに集計
    if '交差点名称(踏切名含む)' in honhyo.columns:
        accident_counts = honhyo.groupby('交差点名称(踏切名含む)').size().reset_index(name='事故件数')
        merged = pd.merge(filtered, accident_counts, left_on='交差点名称(踏切名含む)', right_on='交差点名称(踏切名含む)', how='left')
    else:
        merged = filtered.copy()

    merged['事故件数'] = merged['事故件数'].fillna(0).astype(int)

    # 地図中心の決定
    if not merged.empty and '規制場所の経度緯度' in merged.columns:
        # 経度緯度列が "lat,lon" 形式なら分割
        merged[['緯度', '経度']] = merged['規制場所の経度緯度'].str.split(',', expand=True).astype(float)
        center_lat = merged['緯度'].mean()
        center_lon = merged['経度'].mean()
    else:
        center_lat, center_lon = 36.0652, 136.2216  # デフォルト福井市中心

    # Folium地図作成
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    for _, row in merged.iterrows():
        lat = row.get('緯度')
        lon = row.get('経度')
        if pd.notnull(lat) and pd.notnull(lon):
            popup_text = f"{row.get('交差点名称(踏切名含む)', '不明')}<br>事故件数: {row['事故件数']}件"
            if '規制内容' in row:
                popup_text += f"<br>規制: {row['規制内容']}"
            folium.CircleMarker(
                location=[lat, lon],
                radius=5 + row['事故件数'] * 0.5,
                popup=popup_text,
                color="red" if row['事故件数'] > 0 else "blue",
                fill=True,
                fill_opacity=0.6
            ).add_to(fmap)

    map_html = fmap._repr_html_()

    return render_template(
        'results.html',
        selected_area=area,
        intersection=intersection,
        map_html=map_html,
        data=merged.to_dict(orient='records')
    )

if __name__ == '__main__':
    app.run(debug=True)
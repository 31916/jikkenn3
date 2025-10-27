from flask import Flask, render_template, request
import pandas as pd
import folium
import os

app = Flask(__name__)

# --- データの読み込み ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        return pd.read_csv(path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding='cp932')

honhyo = load_csv("honhyo_2024.csv")
seigzo = load_csv("seigzo.csv")
teigi = load_csv("teigi.csv")

# --- 地図表示の初期中心位置（福井駅あたり） ---
CENTER = [36.0617, 136.2229]

@app.route('/')
def index():
    # 地域や交差点名の一覧（あれば）
    area_options = []
    if '地区名' in seigzo.columns:
        area_options = sorted(seigzo['地区名'].dropna().unique())
    elif '市区町村名' in seigzo.columns:
        area_options = sorted(seigzo['市区町村名'].dropna().unique())
    return render_template('index.html', areas=area_options)

@app.route('/results', methods=['POST'])
def results():
    area = request.form.get('area')

    # --- データ整形 ---
    df = honhyo.copy()
    # 「交差点ID」カラムが一致するようにjoin
    if '交差点ID' in df.columns and '交差点ID' in seigzo.columns:
        merged = pd.merge(seigzo, df, on='交差点ID', how='left')
    else:
        merged = seigzo.copy()

    # 地域で絞り込み（もし地区名がある場合）
    if area:
        if '地区名' in merged.columns:
            merged = merged[merged['地区名'] == area]
        elif '市区町村名' in merged.columns:
            merged = merged[merged['市区町村名'] == area]

    # --- 事故件数集計 ---
    if '交差点ID' in df.columns:
        count_df = df.groupby('交差点ID').size().reset_index(name='事故件数')
        merged = pd.merge(merged, count_df, on='交差点ID', how='left')
    else:
        merged['事故件数'] = 1

    merged['事故件数'] = merged['事故件数'].fillna(0).astype(int)

    # --- 地図描画 ---
    fmap = folium.Map(location=CENTER, zoom_start=13)

    for _, row in merged.iterrows():
        if '緯度' in row and '経度' in row and pd.notna(row['緯度']) and pd.notna(row['経度']):
            folium.CircleMarker(
                location=[row['緯度'], row['経度']],
                radius=5 + row['事故件数'] * 0.5,
                popup=f"交差点: {row.get('交差点名', '不明')}<br>事故件数: {row['事故件数']}",
                color='red' if row['事故件数'] > 0 else 'blue',
                fill=True,
                fill_opacity=0.6
            ).add_to(fmap)

    map_html = fmap._repr_html_()

    return render_template('results.html', area=area, map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)

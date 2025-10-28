from flask import Flask, render_template, request
import pandas as pd
import folium

app = Flask(__name__)

# ===== CSVを読み込む =====
try:
    jiko_df = pd.read_csv("jiko.csv", encoding="utf-8")
except UnicodeDecodeError:
    jiko_df = pd.read_csv("jiko.csv", encoding="cp932")

try:
    signal_df = pd.read_csv("seigzo.csv", encoding="utf-8")
except UnicodeDecodeError:
    signal_df = pd.read_csv("seigzo.csv", encoding="cp932")

# ===== 緯度経度の列を安全に数値変換 =====
jiko_df["地点　緯度（北緯）"] = pd.to_numeric(jiko_df["地点　緯度（北緯）"], errors="coerce")
jiko_df["地点　経度（東経）"] = pd.to_numeric(jiko_df["地点　経度（東経）"], errors="coerce")

# ===== 都道府県コード一覧 =====
areas = sorted(jiko_df["都道府県コード"].dropna().unique().tolist())

@app.route("/")
def index():
    return render_template("index.html", areas=areas, selected_area="", intersection="")

@app.route("/results", methods=["POST"])
def results():
    selected_area = request.form.get("area", "")
    intersection = request.form.get("intersection", "").strip()

    df_filtered = jiko_df.copy()

    # ===== 都道府県コードでフィルタ =====
    if selected_area:
        df_filtered = df_filtered[df_filtered["都道府県コード"].astype(str) == str(selected_area)]

    # ===== 交差点名（部分一致） =====
    if intersection:
        df_filtered = df_filtered[
            df_filtered["交差点名称(踏切名含む)"].astype(str).str.contains(intersection, case=False, na=False)
        ]

    # ===== 件数集計 =====
    grouped = (
        df_filtered.groupby("交差点名称(踏切名含む)", dropna=False)
        .size()
        .reset_index(name="事故件数")
    )

    # ===== 信号規制情報との結合（交差点番号や名称が共通している場合） =====
    merged = pd.merge(
        grouped,
        signal_df,
        left_on="交差点名称(踏切名含む)",
        right_on="交差点番号",
        how="left"
    )

    # ===== 地図を作成 =====
    if not df_filtered.empty:
        lat_mean = df_filtered["地点　緯度（北緯）"].mean() / 10000000
        lon_mean = df_filtered["地点　経度（東経）"].mean() / 10000000
        m = folium.Map(location=[lat_mean, lon_mean], zoom_start=11)
        for _, row in df_filtered.iterrows():
            if pd.notna(row["地点　緯度（北緯）"]) and pd.notna(row["地点　経度（東経）"]):
                folium.Marker(
                    location=[
                        row["地点　緯度（北緯）"] / 10000000,
                        row["地点　経度（東経）"] / 10000000,
                    ],
                    popup=f"{row.get('交差点名称(踏切名含む)','不明')}<br>事故内容: {row.get('事故内容','')}"
                ).add_to(m)
        map_html = m._repr_html_()
    else:
        map_html = "<p>地図データがありません。</p>"

    data = merged.to_dict(orient="records")

    return render_template(
        "results.html",
        selected_area=selected_area,
        intersection=intersection,
        map_html=map_html,
        data=data
    )

if __name__ == "__main__":
    app.run(debug=True)

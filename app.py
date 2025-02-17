import gradio as gr
import requests
import re
import json
import os
import pandas as pd
from xml.etree import ElementTree
from geopy.distance import geodesic

# 設定檔案路徑 (請自行調整)
SEVEN_ELEVEN_FILE = "seven_eleven_products.json"
FAMILY_MART_STORES_FILE = "family_mart_stores.json"
FAMILY_MART_PRODUCTS_FILE = "family_mart_products.json"

# 限制搜尋範圍 3 公里 (3000 公尺)
MAX_DISTANCE = 3000

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def find_nearest_store(address, lat, lon):
    """
    主要的查詢函式：
    1. 讀取 7-11 與全家的 JSON
    2. 在 Logs 中印出前 10 筆資料 (供檢查結構)
    3. 假設 7-11 和全家都各有「店家經緯度」，計算與使用者的距離
    4. 顯示 3 公里內所有店家
    5. (若要顯示「即期食品」，請自行加條件篩選)
    """

    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")
    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)

    # ========== 讀取 7-11 JSON & 印出前 10 筆 ==========
    seven_data = load_json(SEVEN_ELEVEN_FILE)
    print(f"7-11 JSON 筆數: {len(seven_data)}")
    print("7-11 JSON 前 10 筆範例:")
    print(seven_data[:10])  # 印出前 10 筆原始資料

    # 將 7-11 資料轉成 DataFrame
    # 假設 7-11 JSON 裡真的有經緯度欄位叫 'latitude' / 'longitude'
    # 如果你的欄位不同(例如 'lat', 'lng' 等)，請在這裡改對應
    seven_df = pd.DataFrame(seven_data)
    if {"latitude", "longitude"}.issubset(seven_df.columns):
        seven_df["latitude"] = seven_df["latitude"].astype(float)
        seven_df["longitude"] = seven_df["longitude"].astype(float)
        # 計算距離
        seven_df["distance_m"] = seven_df.apply(
            lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
            axis=1
        )
    else:
        print("⚠️  7-11 JSON 裡沒有 'latitude' 或 'longitude' 欄位，將無法做距離計算。")
        seven_df = pd.DataFrame()  # 代表無法顯示 7-11 店家

    # ========== 讀取 全家店家 JSON & 印出前 10 筆 ==========
    family_data = load_json(FAMILY_MART_STORES_FILE)
    print(f"全家店家 JSON 筆數: {len(family_data)}")
    print("全家店家 JSON 前 10 筆範例:")
    print(family_data[:10])

    # 轉成 DataFrame
    family_df = pd.DataFrame(family_data)
    # 假設全家 JSON 裡經緯度是 py_wgs84(緯度) / px_wgs84(經度)
    if {"py_wgs84", "px_wgs84"}.issubset(family_df.columns):
        family_df["latitude"] = family_df["py_wgs84"].astype(float)
        family_df["longitude"] = family_df["px_wgs84"].astype(float)
        family_df["distance_m"] = family_df.apply(
            lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
            axis=1
        )
    else:
        print("⚠️  全家 JSON 裡沒有 'py_wgs84' 或 'px_wgs84' 欄位，將無法做距離計算。")
        family_df = pd.DataFrame()

    # ========== 讀取 全家商品 JSON (若要顯示商品，可使用) ==========
    family_products = load_json(FAMILY_MART_PRODUCTS_FILE)
    print(f"全家商品 JSON 筆數: {len(family_products)}")
    print("全家商品 JSON 前 10 筆範例:")
    print(family_products[:10])

    # 這裡沒有示範「7-11 商品」的前 10 筆，因為上面已經印過 entire 7-11 JSON
    # (如果要也可以印)

    # ========== 篩選 3 公里範圍內所有店家 (7-11 + 全家) ==========
    result_rows = []

    # 7-11 部分
    if not seven_df.empty and "distance_m" in seven_df.columns:
        # 篩出 3km 內
        within_seven = seven_df[seven_df["distance_m"] <= MAX_DISTANCE].sort_values("distance_m")
        # 全部顯示，不限前 5
        for _, row in within_seven.iterrows():
            store_name = row.get("StoreName", "7-11 未提供店名")
            dist_str = f"{row['distance_m']:.1f} m"
            # 這裡如果有「即期食品」欄位，請自行取 row[...] 顯示
            # 或把 7-11 商品對應起來
            result_rows.append([
                f"7-11 {store_name}",
                dist_str,
                "7-11即期商品(示意)",
                "1"
            ])

    # 全家 部分
    if not family_df.empty and "distance_m" in family_df.columns:
        within_family = family_df[family_df["distance_m"] <= MAX_DISTANCE].sort_values("distance_m")
        for _, row in within_family.iterrows():
            store_name = row.get("Name", "全家 未提供店名")
            dist_str = f"{row['distance_m']:.1f} m"
            # 同理，若要顯示「即期食品」，請自行加判斷
            result_rows.append([
                f"全家 {store_name}",
                dist_str,
                "全家即期商品(示意)",
                "1"
            ])

    # 若結果為空，代表 3 公里內沒店家
    if not result_rows:
        return [["❌ 附近 3 公里內沒有便利商店", "", "", "", ""]]

    return result_rows

# ========== Gradio 介面 ==========
with gr.Blocks() as demo:
    gr.Markdown("## 便利商店門市與商品搜尋 (示範)")
    gr.Markdown("1. 按下「使用目前位置」或自行輸入緯度/經度\n2. 點選「搜尋」查詢 3 公里內所有店家\n3. 請於 Logs 查看 7-11 和全家 JSON 的前 10 筆結構")

    address = gr.Textbox(label="輸入地址(可留空)")
    lat = gr.Number(label="GPS 緯度", value=0, elem_id="lat")
    lon = gr.Number(label="GPS 經度", value=0, elem_id="lon")

    with gr.Row():
        gps_button = gr.Button("📍 使用目前位置", elem_id="gps-btn")
        search_button = gr.Button("🔍 搜尋")

    output_table = gr.Dataframe(
        headers=["門市", "距離 (m)", "商品/即期食品", "數量"],
        interactive=False
    )

    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

    gps_button.click(
        None,
        None,
        [lat, lon],
        js="""
        () => {
            return new Promise((resolve) => {
                if (!navigator.geolocation) {
                    alert("您的瀏覽器不支援地理位置功能");
                    resolve([0, 0]);
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve([position.coords.latitude, position.coords.longitude]);
                    },
                    (error) => {
                        alert("無法取得位置：" + error.message);
                        resolve([0, 0]);
                    }
                );
            });
        }
        """
    )

demo.launch(debug=True)
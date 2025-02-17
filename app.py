import gradio as gr
import requests
import json
import os
import pandas as pd
import re
from geopy.distance import geodesic

# 7-11 和全家的 JSON 檔案
seven_eleven_file = "seven_eleven_products.json"
family_mart_stores_file = "family_mart_stores.json"
family_mart_products_file = "family_mart_items.json"

# 限制搜尋範圍為 3 公里
MAX_DISTANCE = 3000  

# 讀取 JSON 檔案
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def find_nearest_store(address, lat, lon):
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")

    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)

    # ========== 先處理 7-11 資料 ==========
    seven_df = pd.DataFrame()
    try:
        seven_data = load_json(seven_eleven_file)
        if not seven_data:
            print("⚠️  7-11 資料是空的 (無法讀取或檔案沒有內容)")
        else:
            print("✅  成功讀取 7-11 資料，前五筆為：")
            # 直接列印前五筆 raw data（list 切片）
            print(seven_data[:5])
            
            # 假設 7-11 JSON 每筆資料都有這些欄位：
            # {
            #   "StoreName": "7-11 XXX店",
            #   "latitude": 25.123,
            #   "longitude": 121.456,
            #   ...
            # }
            seven_df = pd.DataFrame(seven_data)
            
            # 若確定這些欄位名稱存在，就做經緯度轉換
            if {"latitude", "longitude"}.issubset(seven_df.columns):
                seven_df["latitude"] = seven_df["latitude"].astype(float)
                seven_df["longitude"] = seven_df["longitude"].astype(float)
                seven_df["distance_m"] = seven_df.apply(
                    lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
                    axis=1
                )
            else:
                print("⚠️  7-11 資料裡沒有 'latitude' 或 'longitude' 欄位，無法計算距離。")
                seven_df = pd.DataFrame()  # 直接清空，代表無法使用
    except Exception as e:
        print(f"❌  讀取或處理 7-11 資料時發生錯誤: {e}")
        seven_df = pd.DataFrame()

    # ========== 再處理 Family 資料 ==========
    family_df = pd.DataFrame()
    try:
        family_data = load_json(family_mart_stores_file)
        if not family_data:
            print("⚠️  全家資料是空的 (無法讀取或檔案沒有內容)")
        else:
            print("✅  成功讀取 Family 資料，前五筆為：")
            print(family_data[:5])

            # 假設 Family JSON 裡的欄位是 py_wgs84 / px_wgs84 (緯度 / 經度)
            family_df = pd.DataFrame(family_data)
            if {"py_wgs84", "px_wgs84"}.issubset(family_df.columns):
                family_df["latitude"] = family_df["py_wgs84"].astype(float)
                family_df["longitude"] = family_df["px_wgs84"].astype(float)
                family_df["distance_m"] = family_df.apply(
                    lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
                    axis=1
                )
            else:
                print("⚠️  全家資料裡沒有 'py_wgs84' 或 'px_wgs84' 欄位，無法計算距離。")
                family_df = pd.DataFrame()
    except Exception as e:
        print(f"❌  讀取或處理 Family 資料時發生錯誤: {e}")
        family_df = pd.DataFrame()

    # ========== 篩選 3 公里內最近的店家 ==========
    # 7-11
    nearby_seven = pd.DataFrame()
    if not seven_df.empty and "distance_m" in seven_df.columns:
        nearby_seven = seven_df[seven_df["distance_m"] <= MAX_DISTANCE].sort_values(by="distance_m").head(5)

    # 全家
    nearby_family = pd.DataFrame()
    if not family_df.empty and "distance_m" in family_df.columns:
        nearby_family = family_df[family_df["distance_m"] <= MAX_DISTANCE].sort_values(by="distance_m").head(5)

    if nearby_seven.empty and nearby_family.empty:
        return [["❌ 附近 3 公里內沒有便利商店", "", "", "", ""]]

    # ========== 整理成表格輸出 ==========
    output = []

    # 7-11 結果
    if not nearby_seven.empty:
        for _, row in nearby_seven.iterrows():
            store_name = row.get("StoreName", "7-11 未提供店名")
            dist = f"{row['distance_m']:.2f} m"
            output.append([
                store_name,
                dist,
                "7-11 商品(示意)",
                "5"  # 這裡只是示範
            ])
    # 全家 結果
    if not nearby_family.empty:
        for _, row in nearby_family.iterrows():
            store_name = row.get("Name", "全家 未提供店名")
            dist = f"{row['distance_m']:.2f} m"
            output.append([
                store_name,
                dist,
                "全家 商品(示意)",
                "5"  # 這裡只是示範
            ])

    return output

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## 便利商店門市與商品搜尋")
    gr.Markdown("輸入 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)", value=0, elem_id="lat")
    lon = gr.Number(label="GPS 經度 (可選)", value=0, elem_id="lon")

    with gr.Row():
        gps_button = gr.Button("📍 使用目前位置", elem_id="gps-btn")
        search_button = gr.Button("🔍 搜尋")

    output_table = gr.Dataframe(
        headers=["門市", "距離 (m)", "食物", "數量"],
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
                    resolve([0, 0]); // 回傳 [0,0] 避免錯誤
                    return;
                }
                
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve([position.coords.latitude, position.coords.longitude]);
                    },
                    (error) => {
                        alert("無法獲取位置：" + error.message);
                        resolve([0, 0]); // GPS 失敗時回傳 [0,0]
                    }
                );
            });
        }
        """
    )

# 在 launch 時加上 debug=True 也可以幫助觀察更多 log 資訊
demo.launch(share=True, debug=True)
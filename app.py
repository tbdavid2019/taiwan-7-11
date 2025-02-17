import gradio as gr
import pandas as pd
import json
import os
import requests
from xml.etree import ElementTree
import re
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# 設定資料夾
DATA_DIR = "datasets"
SEVEN_ELEVEN_FILE = os.path.join(DATA_DIR, "seven_eleven_products.json")
FAMILY_MART_FILE = os.path.join(DATA_DIR, "family_mart_products.json")

# 確保 datasets 資料夾存在
os.makedirs(DATA_DIR, exist_ok=True)

# 設定地理編碼器
geolocator = Nominatim(user_agent="geoapiExercises", timeout=10)

def find_nearest_store(address, user_lat, user_lon):
    print(f"🔍 收到查詢請求: address={address}, lat={user_lat}, lon={user_lon}")

    if user_lat == 0 or user_lon == 0:
        print("❌ GPS 座標無效，請提供有效數值")
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", ""]]

    user_coords = (user_lat, user_lon)
    print(f"📍 使用 GPS 座標: {user_coords}")

    # 讀取 JSON 檔案
    if not os.path.exists(FAMILY_MART_FILE):
        print("⚠️ 全家 JSON 不存在")
        return [["❌ 便利商店數據不可用", "", "", ""]]

    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_mart_data = json.load(f)

    # 轉換為 DataFrame
    family_df = pd.DataFrame(family_mart_data)

    print(f"✅ 全家資料行數: {len(family_df)}")

    if family_df.empty:
        print("⚠️  便利商店資料為空")
        return [["❌ 便利商店數據為空", "", "", ""]]

    # 過濾無效座標
    family_df = family_df.dropna(subset=["latitude", "longitude"])
    family_df = family_df[(family_df["latitude"] != 0.0) & (family_df["longitude"] != 0.0)]

    # 計算距離
    try:
        family_df["distance"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
    except Exception as e:
        print(f"❌ 計算距離時發生錯誤: {e}")
        return [["❌ 計算距離失敗", "", "", ""]]

    # 取最近的 3 間門市
    nearest_family = family_df.nsmallest(3, "distance")

    output = []
    for _, row in nearest_family.iterrows():
        output.append([
            f"{row['store_type']}, {row['store_name']}",
            f"{row['distance']:.2f} 公尺",
            row.get("title", "未知"),
            row["quantity"]
        ])

    print("✅ 搜尋完成，返回結果")
    return output

# **Gradio UI**
with gr.Blocks() as interface:
    gr.Markdown("## 便利商店門市與商品搜尋")
    gr.Markdown("輸入 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)", value=0)
    lon = gr.Number(label="GPS 經度 (可選)", value=0)

    with gr.Row():
        use_gps_button = gr.Button("使用目前位置")
        search_button = gr.Button("搜尋")

    output_table = gr.Dataframe(headers=["門市", "距離", "食物", "數量"])

    # **使用目前位置**
    use_gps_button.click(None, [], [lat, lon], js="""
        () => {
            return new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    (position) => resolve([position.coords.latitude, position.coords.longitude]),
                    (error) => reject([0, 0])
                );
            });
        }
    """)

    # ✅ 修正：`inputs=["", lat, lon]` 改為 `inputs=[address, lat, lon]`
    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

interface.launch()
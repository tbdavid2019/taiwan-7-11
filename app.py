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

    # 檢查 JSON 文件是否存在
    if not os.path.exists(SEVEN_ELEVEN_FILE) or not os.path.exists(FAMILY_MART_FILE):
        print("⚠️ JSON 資料不存在，請重新下載")
        return [["❌ 便利商店數據不可用", "", "", ""]]

    # 讀取 JSON 檔案
    with open(SEVEN_ELEVEN_FILE, 'r', encoding='utf-8') as f:
        seven_eleven_data = json.load(f)
    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_mart_data = json.load(f)

    # 轉換為 DataFrame
    seven_df = pd.DataFrame(seven_eleven_data)
    family_df = pd.DataFrame(family_mart_data)

    print(f"✅ 7-11 資料行數: {len(seven_df)}, 全家資料行數: {len(family_df)}")

    # 確保 DataFrame 不是空的
    if seven_df.empty or family_df.empty:
        print("⚠️  便利商店資料為空")
        return [["❌ 便利商店數據為空", "", "", ""]]

    # 檢查是否有 "latitude" 和 "longitude" 欄位
    if "latitude" not in seven_df.columns or "longitude" not in seven_df.columns:
        print("⚠️  7-11 資料缺少座標欄位")
        return [["❌ 7-11 資料缺少座標", "", "", ""]]
    
    if "latitude" not in family_df.columns or "longitude" not in family_df.columns:
        print("⚠️  全家資料缺少座標欄位")
        return [["❌ 全家資料缺少座標", "", "", ""]]

    # 移除沒有座標的行
    seven_df = seven_df.dropna(subset=["latitude", "longitude"])
    family_df = family_df.dropna(subset=["latitude", "longitude"])

    # 計算距離
    try:
        seven_df["distance"] = seven_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
        family_df["distance"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
    except Exception as e:
        print(f"❌ 計算距離時發生錯誤: {e}")
        return [["❌ 計算距離失敗", "", "", ""]]

    # 取最近的 3 間門市
    nearest_seven = seven_df.nsmallest(3, "distance")
    nearest_family = family_df.nsmallest(3, "distance")

    output = []
    for _, row in nearest_seven.iterrows():
        output.append([
            f"{row['store_type']}, {row['store_name']}",
            f"{row['distance']:.2f} 公尺",
            row["name"],
            row["quantity"]
        ])
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
    gr.Markdown("輸入地址或 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)", value=0)
    lon = gr.Number(label="GPS 經度 (可選)", value=0)

    with gr.Row():
        use_gps_button = gr.Button("使用目前位置")
        search_button = gr.Button("搜尋")

    output_table = gr.Dataframe(headers=["門市", "距離", "食物", "數量"])

    # **使用目前位置 - 透過 JavaScript 取得 GPS**
    use_gps_button.click(
        None, [], [lat, lon], js="""
        () => {
            return new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        let latitude = position.coords.latitude;
                        let longitude = position.coords.longitude;
                        console.log("📍 取得 GPS 座標:", latitude, longitude);
                        resolve([latitude, longitude]); 
                    },
                    (error) => {
                        alert("無法取得您的 GPS 位置，請允許瀏覽器存取您的位置。");
                        reject([0, 0]);
                    }
                );
            });
        }
        """
    )

    # **當按下搜尋按鈕時，才會執行 `find_nearest_store`**
    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

interface.launch()
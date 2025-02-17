import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic

# ⏳ 下載 7-11 JSON

seven_eleven_url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
seven_eleven_file = "seven_eleven_products.json"


# 先檢查檔案是否存在，沒有的話下載
if not os.path.exists(seven_eleven_file):
    print("⚠️  7-11 JSON 檔案不存在，正在下載...")
    # 這裡是 7-11 資料的 API (如果有 API，請填入正確的 URL)
    api_url = "https://example.com/api/7-11-products"  # 這裡要替換為正確的 URL
    response = requests.get(api_url)

    if response.status_code == 200:
        with open(seven_eleven_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        print("✅  7-11 JSON 下載完成！")
    else:
        print(f"❌ 下載失敗，狀態碼: {response.status_code}")

# 讀取 JSON 檔案
try:
    with open(seven_eleven_file, "r", encoding="utf-8") as f:
        seven_eleven_data = json.load(f)
    print("📂  7-11 JSON 成功讀取！")
except Exception as e:
    print(f"❌  讀取 JSON 失敗: {e}")

# ⏳ 下載全家 JSON
family_mart_url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
family_mart_file = "family_mart_products.json"

if not os.path.exists(family_mart_file):
    response = requests.get(family_mart_url)
    if response.status_code == 200:
        with open(family_mart_file, "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)

# ✅ 讀取 JSON
with open(seven_eleven_file, "r", encoding="utf-8") as f:
    seven_eleven_data = json.load(f)

with open(family_mart_file, "r", encoding="utf-8") as f:
    family_mart_data = json.load(f)

# 轉換為 DataFrame
seven_df = pd.DataFrame(seven_eleven_data)
family_df = pd.DataFrame(family_mart_data)

# 📍 定位函數
def find_nearest_store(address, lat, lon):
    if not lat or not lon:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)

    # ✅ 計算 7-11 門市距離
    seven_df["distance_m"] = seven_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters
        if "latitude" in row and "longitude" in row else float("inf"),
        axis=1,
    )

    # ✅ 計算全家門市距離
    family_df["distance_m"] = family_df.apply(
        lambda row: geodesic(user_coords, (row["py_wgs84"], row["px_wgs84"])).meters
        if "py_wgs84" in row and "px_wgs84" in row else float("inf"),
        axis=1,
    )

    # 📌 限制 3km 內的商店
    nearby_seven = seven_df[seven_df["distance_m"] <= 3000].sort_values(by="distance_m").head(5)
    nearby_family = family_df[family_df["distance_m"] <= 3000].sort_values(by="distance_m").head(5)

    # 🔎 準備輸出
    output = []
    for _, row in nearby_seven.iterrows():
        output.append(["7-11 " + row["store_name"], f"{row['distance_m']:.2f} m", row["name"], row.get("quantity", 1)])

    for _, row in nearby_family.iterrows():
        output.append(["全家 " + row["Name"], f"{row['distance_m']:.2f} m", row["Name"], row.get("quantity", 1)])

    return output

# 📍 取得 GPS 位置（使用 JS）
def get_location():
    return "navigator.geolocation.getCurrentPosition(function(position) { gradioAPI.setValue('lat', position.coords.latitude); gradioAPI.setValue('lon', position.coords.longitude); });"

# 🚀 Gradio 介面
with gr.Blocks() as app:
    gr.Markdown("# 便利商店門市與商品搜尋")
    gr.Markdown("輸入地址或 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)")
    lon = gr.Number(label="GPS 經度 (可選)")

    with gr.Row():
        gps_button = gr.Button("📍 使用目前位置")
        search_button = gr.Button("🔍 搜尋")

    output_table = gr.Dataframe(
        headers=["門市", "距離 (m)", "食物", "數量"],
        interactive=False,
    )

    gps_button.click(fn=None, inputs=[], outputs=[], js=get_location)
    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

app.launch()
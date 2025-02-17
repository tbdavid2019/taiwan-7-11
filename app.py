import gradio as gr
import pandas as pd
import json
import os
import requests
import re
from geopy.distance import geodesic

# 📌 定義 7-11 和 全家 API 來源
SEVEN_ELEVEN_URL = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
FAMILY_MART_URL = "https://famihealth.family.com.tw/Calculator"

# 📌 爬取 7-11 最新資料
def fetch_seven_eleven_data():
    print("📥 正在下載 7-11 最新數據...")
    response = requests.get(SEVEN_ELEVEN_URL)
    if response.status_code == 200:
        try:
            data = response.json()
            with open("seven_eleven_products.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ 7-11 數據下載完成，共 {len(data)} 筆資料")
        except:
            print("❌ 解析 7-11 JSON 失敗")
    else:
        print("❌ 下載 7-11 數據失敗")

# 📌 爬取 全家 最新資料 (門市 + 產品)
def fetch_family_mart_data():
    print("📥 正在下載全家最新數據...")

    # 全家門市資料
    store_url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
    store_response = requests.post(store_url, json={"store": ""})
    if store_response.status_code == 200:
        store_data = store_response.json()
        with open("family_mart_stores.json", "w", encoding="utf-8") as f:
            json.dump(store_data, f, ensure_ascii=False, indent=4)
        print(f"✅ 全家門市數據下載完成，共 {len(store_data)} 筆資料")
    else:
        print("❌ 下載全家門市數據失敗")

    # 全家產品資料
    headers = {"User-Agent": "Mozilla/5.0"}
    product_response = requests.get(FAMILY_MART_URL, headers=headers)
    if product_response.status_code == 200:
        match = re.search(r'var categories = (\[.*?\]);', product_response.text, re.S)
        if match:
            categories_data = json.loads(match.group(1))
            results = []
            for category in categories_data:
                for product in category.get("products", []):
                    results.append({
                        "category": category.get("name"),
                        "title": product.get("name"),
                        "picture_url": product.get("imgurl"),
                        "Calories (kcal)": product.get("calo", 0),
                        "Fat (g)": product.get("fat", 0),
                    })
            with open("family_mart_products.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"✅ 全家產品數據下載完成，共 {len(results)} 筆資料")
        else:
            print("❌ 解析全家產品數據失敗")
    else:
        print("❌ 下載全家產品數據失敗")

# 📌 查找最近的便利商店
def find_nearest_store(address, lat, lon):
    if lat == 0 or lon == 0:
        return [["X 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    print(f"📍 使用 GPS 座標: ({lat}, {lon})")
    user_coords = (lat, lon)

    # 讀取門市 JSON 檔案
    try:
        with open("seven_eleven_products.json", "r", encoding="utf-8") as f:
            seven_data = json.load(f)
        with open("family_mart_stores.json", "r", encoding="utf-8") as f:
            family_data = json.load(f)
    except:
        return [["❌ JSON 資料不存在，請重新下載", "", "", "", ""]]

    seven_df = pd.DataFrame(seven_data)
    family_df = pd.DataFrame(family_data)

    # 處理經緯度
    seven_df["latitude"] = seven_df["latitude"].astype(float)
    seven_df["longitude"] = seven_df["longitude"].astype(float)
    family_df["latitude"] = family_df["py_wgs84"].astype(float)
    family_df["longitude"] = family_df["px_wgs84"].astype(float)

    # 計算距離
    seven_df["distance_m"] = seven_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
    family_df["distance_m"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)

    # 過濾 3km 內的商店
    nearby_seven = seven_df[seven_df["distance_m"] <= 3000].sort_values(by="distance_m").head(5)
    nearby_family = family_df[family_df["distance_m"] <= 3000].sort_values(by="distance_m").head(5)

    # 整合數據
    output = []
    for _, row in nearby_seven.iterrows():
        output.append(["7-11 " + row["store_name"], f"{row['distance_m']:.2f} 公尺", row["name"], row["quantity"]])

    for _, row in nearby_family.iterrows():
        output.append(["全家 " + row["Name"], f"{row['distance_m']:.2f} 公尺", row["store_name"], row["quantity"]])

    return output

# 📌 JavaScript 代碼獲取 GPS
get_location_js = """
navigator.geolocation.getCurrentPosition(
    (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        console.log("獲取GPS成功:", lat, lon);
        document.querySelector('input[aria-label="GPS 緯度 (可選)"]').value = lat;
        document.querySelector('input[aria-label="GPS 經度 (可選)"]').value = lon;
    },
    (error) => {
        console.error("GPS獲取失敗", error);
    }
);
"""

# 📌 建立 Gradio UI
address_input = gr.Textbox(label="輸入地址或留空以使用 GPS")
lat_input = gr.Number(label="GPS 緯度 (可選)", value=0)
lon_input = gr.Number(label="GPS 經度 (可選)", value=0)
gps_button = gr.Button("📍 使用目前位置")
search_button = gr.Button("🔍 搜尋")
output_table = gr.DataFrame(headers=["門市", "距離", "食物", "數量"])

# 📌 設置按鈕事件
gps_button.click(None, [], [], _js=get_location_js)
search_button.click(find_nearest_store, [address_input, lat_input, lon_input], output_table)

# 📌 啟動應用
app = gr.Interface(
    fn=find_nearest_store,
    inputs=[address_input, lat_input, lon_input],
    outputs=output_table,
    title="便利商店門市與商品搜尋",
    description="輸入地址或 GPS 座標來搜尋最近的便利商店與推薦商品"
)

fetch_seven_eleven_data()
fetch_family_mart_data()
app.launch()
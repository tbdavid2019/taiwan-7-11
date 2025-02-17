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

# 下載 7-11 JSON
def fetch_seven_eleven_data():
    base_url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    categories = ["1_Ricerolls", "16_sandwich", "2_Light", "3_Cuisine", "4_Snacks"]

    data = []
    for category in categories:
        response = requests.get(base_url, headers=headers)
        if response.status_code == 200:
            try:
                root = ElementTree.fromstring(response.content)
                for item in root.findall(".//Item"):
                    data.append({
                        "category": category,
                        "name": item.findtext("name", ""),
                        "kcal": item.findtext("kcal", ""),
                        "price": item.findtext("price", ""),
                        "image": f'https://www.7-11.com.tw/freshfoods/{category}/' + item.findtext("image", ""),
                        "latitude": 0.0,  # 沒有提供座標
                        "longitude": 0.0
                    })
            except ElementTree.ParseError:
                print(f"分類 {category} 無法解析")
    
    with open(SEVEN_ELEVEN_FILE, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# 下載全家 JSON
def fetch_family_mart_data():
    url = 'https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName'
    response = requests.post(url, json={"store": ""})

    if response.status_code == 200:
        data = response.json()
        for store in data:
            store["latitude"] = store.get("lat", 0.0)
            store["longitude"] = store.get("lng", 0.0)

        with open(FAMILY_MART_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# 設定地理編碼器
geolocator = Nominatim(user_agent="geoapiExercises", timeout=10)

def find_nearest_store(address, user_lat, user_lon):
    fetch_seven_eleven_data()
    fetch_family_mart_data()

    with open(SEVEN_ELEVEN_FILE, 'r', encoding='utf-8') as f:
        seven_eleven_data = json.load(f)
    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_mart_data = json.load(f)

    seven_df = pd.DataFrame(seven_eleven_data)
    family_df = pd.DataFrame(family_mart_data)

    if address:
        try:
            location = geolocator.geocode(address, timeout=10)
            if not location:
                return "地址無法解析"
            user_coords = (location.latitude, location.longitude)
        except Exception as e:
            return f"地理編碼錯誤: {e}"
    elif user_lat and user_lon:
        user_coords = (user_lat, user_lon)
    else:
        return "請輸入地址或提供 GPS 座標"

    seven_df["distance"] = seven_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
    family_df["distance"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)

    nearest_seven = seven_df.nsmallest(3, "distance")
    nearest_family = family_df.nsmallest(3, "distance")

    output = []
    for _, row in nearest_seven.iterrows():
        output.append({
            "門市": "7-11 " + row.get("store_name", "未知"),
            "距離": f"{row['distance']:.2f} 公尺",
            "食物": row["name"],
            "卡路里": row["kcal"],
            "價格": f"${row['price']}",
            "圖片": row["image"]
        })
    for _, row in nearest_family.iterrows():
        output.append({
            "門市": "全家 " + row.get("store_name", "未知"),
            "距離": f"{row['distance']:.2f} 公尺",
            "食物": row.get("title", "未知"),
            "卡路里": row.get("Calories", "未知"),
            "價格": f"${row.get('price', 'N/A')}",
            "圖片": row.get("picture_url", "")
        })

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

    output_table = gr.Dataframe(headers=["門市", "距離", "食物", "卡路里", "價格", "圖片"])

    # **使用目前位置 - 透過 JavaScript 取得 GPS**
    use_gps_button.click(
        None, [], [], js="""
        () => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    document.querySelector('input[aria-label="GPS 緯度 (可選)"]').value = position.coords.latitude;
                    document.querySelector('input[aria-label="GPS 經度 (可選)"]').value = position.coords.longitude;
                },
                (error) => {
                    alert("無法取得您的 GPS 位置，請允許瀏覽器存取您的位置。");
                }
            );
        }
        """
    )

    # **當按下搜尋按鈕時，才會執行 `find_nearest_store`**
    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

interface.launch()
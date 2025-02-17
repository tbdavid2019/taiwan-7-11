import gradio as gr
import pandas as pd
import json
import os
import requests
from xml.etree import ElementTree
import re
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 設定檔案路徑
DATA_DIR = "datasets"
SEVEN_ELEVEN_FILE = os.path.join(DATA_DIR, "seven_eleven_products.json")
FAMILY_MART_FILE = os.path.join(DATA_DIR, "family_mart_products.json")

# 確保 datasets 資料夾存在
os.makedirs(DATA_DIR, exist_ok=True)

# 下載 7-11 JSON
def fetch_seven_eleven_data():
    base_url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    categories = [
        "19_star", "1_Ricerolls", "16_sandwich", "2_Light", "3_Cuisine",
        "4_Snacks", "5_ForeignDishes", "6_Noodles", "7_Oden", "8_Bigbite",
        "9_Icecream", "10_Slurpee", "11_bread", "hot", "12_steam",
        "13_luwei", "15_health", "17_ohlala", "18_veg", "20_panini", "21_ice", "22_ice"
    ]
    
    data = []
    for index, category in enumerate(categories):
        response = requests.get(base_url, headers=headers, params={"": index})
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
                        "special_sale": item.findtext("special_sale", ""),
                        "new": item.findtext("new", ""),
                        "content": item.findtext("content", ""),
                        "latitude": 0.0,  # 假設沒座標
                        "longitude": 0.0
                    })
            except ElementTree.ParseError:
                print(f"分類 {category} 返回非 XML 格式資料。")
        else:
            print(f"分類 {category} 請求失敗，狀態碼: {response.status_code}")

    with open(SEVEN_ELEVEN_FILE, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# 下載全家 JSON
def fetch_family_mart_data():
    url = 'https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName'
    response = requests.post(url, json={"store": ""})

    if response.status_code == 200:
        data = response.json()
        for store in data:
            store["latitude"] = store.get("lat", 0.0)  # 假設 API 提供座標
            store["longitude"] = store.get("lng", 0.0)

        with open(FAMILY_MART_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# 設定地理編碼器，增加 timeout 避免請求過久
geolocator = Nominatim(user_agent="geoapiExercises", timeout=10)

def find_nearest_store(address, user_lat, user_lon):
    # 重新下載最新的 JSON
    fetch_seven_eleven_data()
    fetch_family_mart_data()

    # 讀取最新的 JSON
    with open(SEVEN_ELEVEN_FILE, 'r', encoding='utf-8') as f:
        seven_eleven_data = json.load(f)
    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_mart_data = json.load(f)

    # 轉換為 DataFrame
    seven_df = pd.DataFrame(seven_eleven_data)
    family_df = pd.DataFrame(family_mart_data)

    # 解析地址為 GPS 座標
    if address:
        try:
            location = geolocator.geocode(address, timeout=10)
            if not location:
                return "地址無法解析，請重新輸入"
            user_coords = (location.latitude, location.longitude)
        except Exception as e:
            return f"地理編碼錯誤: {e}"
    elif user_lat and user_lon:
        user_coords = (user_lat, user_lon)
    else:
        return "請輸入地址或提供 GPS 座標"

    # 計算距離
    seven_df["distance"] = seven_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)
    family_df["distance"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)

    # 找最近門市
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

# Gradio UI，新增搜尋按鈕
def display_results(address, lat, lon):
    return find_nearest_store(address, lat, lon)

interface = gr.Interface(
    fn=display_results,
    inputs=[
        gr.Textbox(label="輸入地址或留空以使用 GPS"),
        gr.Number(label="GPS 緯度 (可選)", value=0),
        gr.Number(label="GPS 經度 (可選)", value=0),
        gr.Button("搜尋")
    ],
    outputs=gr.Dataframe(headers=["門市", "距離", "食物", "卡路里", "價格", "圖片"]),
    live=False,  # 只有按「搜尋」才會執行
    title="便利商店門市與商品搜尋",
    description="輸入地址或 GPS 座標來搜尋最近的便利商店與推薦商品"
)

interface.launch()
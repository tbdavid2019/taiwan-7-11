import gradio as gr
import pandas as pd
import json
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# 載入爬蟲資料
seven_eleven_file = os.path.join('docs', 'assets', 'seven_eleven_products.json')
family_mart_file = os.path.join('docs', 'assets', 'family_mart_products.json')

with open(seven_eleven_file, 'r', encoding='utf-8') as f:
    seven_eleven_data = json.load(f)

with open(family_mart_file, 'r', encoding='utf-8') as f:
    family_mart_data = json.load(f)

# 將資料整合為 DataFrame
seven_df = pd.DataFrame(seven_eleven_data)
family_df = pd.DataFrame(family_mart_data)

# 定義地理編碼器
geolocator = Nominatim(user_agent="geoapiExercises")

def find_nearest_store(address, user_lat=None, user_lon=None):
    if address:
        # 使用地址轉換為 GPS 座標
        location = geolocator.geocode(address)
        if not location:
            return "地址無法解析，請重新輸入"
        user_coords = (location.latitude, location.longitude)
    elif user_lat and user_lon:
        # 使用提供的 GPS 座標
        user_coords = (user_lat, user_lon)
    else:
        return "請輸入地址或提供 GPS 座標"

    # 添加門市位置（假設 JSON 包含座標資料）
    seven_df['coords'] = list(zip(seven_df['latitude'], seven_df['longitude']))
    family_df['coords'] = list(zip(family_df['latitude'], family_df['longitude']))

    # 計算與每家門市的距離
    seven_df['distance'] = seven_df['coords'].apply(lambda x: geodesic(user_coords, x).meters)
    family_df['distance'] = family_df['coords'].apply(lambda x: geodesic(user_coords, x).meters)

    # 篩選最近的門市
    nearest_seven = seven_df.sort_values(by='distance').head(3)
    nearest_family = family_df.sort_values(by='distance').head(3)

    # 整理輸出資料
    output = []
    for _, row in nearest_seven.iterrows():
        output.append({
            "門市": "7-11 " + row['store_name'],
            "距離": f"{row['distance']:.2f} 公尺",
            "食物": row['name'],
            "卡路里": row['kcal'],
            "價格": f"${row['price']}",
            "圖片": row['image']
        })
    for _, row in nearest_family.iterrows():
        output.append({
            "門市": "全家 " + row['store_name'],
            "距離": f"{row['distance']:.2f} 公尺",
            "食物": row['title'],
            "卡路里": row['Calories'],
            "價格": f"${row['price']}" if 'price' in row else "N/A",
            "圖片": row['picture_url']
        })

    return output

# 定義 Gradio 介面
def display_results(address, lat, lon):
    return find_nearest_store(address, lat, lon)

interface = gr.Interface(
    fn=display_results,
    inputs=[
        gr.Textbox(label="輸入地址或留空以使用 GPS"),
        gr.Number(label="GPS 緯度 (可選)", value=None),
        gr.Number(label="GPS 經度 (可選)", value=None)
    ],
    outputs=gr.Dataframe(headers=["門市", "距離", "食物", "卡路里", "價格", "圖片"]),
    live=True,
    title="便利商店門市與商品搜尋",
    description="輸入地址或 GPS 座標來搜尋最近的便利商店與推薦商品"
)

interface.launch()
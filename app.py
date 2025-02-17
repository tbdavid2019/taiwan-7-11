import gradio as gr
import requests
import json
import os
import pandas as pd
import re
from geopy.distance import geodesic

# 📌 定義 JSON 文件路徑
SEVEN_ELEVEN_FILE = "seven_eleven_products.json"
FAMILY_MART_FILE = "family_mart_stores.json"
FAMILY_MART_PRODUCTS_FILE = "family_mart_products.json"

# 📥 **下載 7-11 門市數據**
def fetch_seven_eleven_data():
    print("📥 正在下載 7-11 最新數據...")
    base_url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(base_url, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            with open(SEVEN_ELEVEN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ 7-11 數據下載完成，共 {len(data)} 筆資料")
        except json.JSONDecodeError:
            print("❌ 7-11 數據解析失敗")
    else:
        print(f"❌ 7-11 API 請求失敗，狀態碼: {response.status_code}")

# 📥 **下載全家門市數據**
def fetch_family_mart_data():
    print("📥 正在下載全家最新數據...")
    url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.post(url, headers=headers, json={"store": ""})

    if response.status_code == 200:
        data = response.json()
        with open(FAMILY_MART_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 全家數據下載完成，共 {len(data)} 筆資料")
    else:
        print(f"❌ 全家 API 請求失敗，狀態碼: {response.status_code}")

# 📥 **下載全家商品數據**
def fetch_family_mart_products():
    print("📥 正在下載全家商品數據...")
    url = "https://famihealth.family.com.tw/Calculator"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match = re.search(r'var categories = (\[.*?\]);', response.text, re.S)
        if match:
            categories_data = json.loads(match.group(1))
            results = []
            for category in categories_data:
                for product in category.get("products", []):
                    results.append({
                        "category": category.get("name"),
                        "title": product.get("name"),
                        "picture_url": product.get("imgurl"),
                        "Protein (g)": product.get("protein", 0),
                        "Carb (g)": product.get("carb", 0),
                        "Calories (kcal)": product.get("calo", 0),
                        "Fat (g)": product.get("fat", 0),
                        "Description": product.get("description", ""),
                    })
            with open(FAMILY_MART_PRODUCTS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"✅ 全家商品數據下載完成，共 {len(results)} 筆資料")
    else:
        print(f"❌ 全家商品 API 請求失敗，狀態碼: {response.status_code}")

# 🔍 **查找最近門市**
def find_nearest_store(address, user_lat, user_lon):
    print(f"🔍 收到查詢請求: address={address}, lat={user_lat}, lon={user_lon}")

    if user_lat == 0 or user_lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (user_lat, user_lon)
    print(f"📍 使用 GPS 座標: {user_coords}")

    # **下載最新數據**
    fetch_seven_eleven_data()
    fetch_family_mart_data()
    fetch_family_mart_products()

    # **檢查 JSON**
    if not os.path.exists(SEVEN_ELEVEN_FILE) or not os.path.exists(FAMILY_MART_FILE) or not os.path.exists(FAMILY_MART_PRODUCTS_FILE):
        return [["❌ 便利商店數據下載失敗", "", "", "", ""]]

    # **讀取 JSON**
    with open(SEVEN_ELEVEN_FILE, 'r', encoding='utf-8') as f:
        seven_data = json.load(f)

    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_data = json.load(f)

    with open(FAMILY_MART_PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        products_data = json.load(f)

    # **轉換 DataFrame**
    seven_df = pd.DataFrame(seven_data)
    family_df = pd.DataFrame(family_data)
    products_df = pd.DataFrame(products_data)

    print(f"✅ 7-11: {len(seven_df)} 行, 全家: {len(family_df)} 行")

    # ✅ **修正全家的座標與門市名稱**
    family_df["latitude"] = family_df["py_wgs84"]
    family_df["longitude"] = family_df["px_wgs84"]
    family_df["store_name"] = family_df["Name"]

    # **計算距離**
    family_df["distance"] = family_df.apply(lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1)

    # **過濾 3km 內的門市**
    family_df = family_df[family_df["distance"] <= 3000]

    # **合併商品資訊**
    family_df = family_df.merge(products_df, how="left", left_on="store_name", right_on="category")

    # **取最近的 3 間門市**
    nearest_family = family_df.nsmallest(3, "distance")

    output = []
    for _, row in nearest_family.iterrows():
        output.append([
            f"{row['store_type']}, {row['store_name']}",
            f"{row['distance']:.2f} 公尺",
            f"{row['distance']:.0f} m",
            row.get("title", "未知"), 
            row["quantity"]
        ])

    return output

# **🌍 Gradio 介面**
with gr.Blocks() as demo:
    gr.Markdown("# 便利商店門市與商品搜尋")
    gr.Markdown("輸入 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)")
    lon = gr.Number(label="GPS 經度 (可選)")

    search_button = gr.Button("搜尋")
    output_table = gr.Dataframe(headers=["門市", "距離", "距離 (m)", "食物", "數量"])

    search_button.click(find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

demo.launch()
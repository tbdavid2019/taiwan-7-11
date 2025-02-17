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

# **下載 7-11 JSON**
def fetch_seven_eleven_data():
    print("📥 正在下載 7-11 最新數據...")
    url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            root = ElementTree.fromstring(response.content)
            data = []
            for item in root.findall(".//Item"):
                data.append({
                    "store_type": "7-11",
                    "store_name": "未知門市",
                    "name": item.findtext("name", ""),
                    "kcal": item.findtext("kcal", ""),
                    "price": item.findtext("price", ""),
                    "image": item.findtext("image", ""),
                    "quantity": 1
                })

            with open(SEVEN_ELEVEN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            print(f"✅ 7-11 數據下載完成，共 {len(data)} 筆資料")
            print("🔍 前 10 筆 7-11 JSON:", json.dumps(data[:10], ensure_ascii=False, indent=4))

        except ElementTree.ParseError:
            print("⚠️ 7-11 API 返回非 XML 格式數據")
    else:
        print(f"⚠️ 7-11 API 請求失敗，狀態碼: {response.status_code}")

# **下載 全家 JSON**
def fetch_family_mart_data():
    print("📥 正在下載全家最新數據...")
    url = 'https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName'
    response = requests.post(url, json={"store": ""})

    if response.status_code == 200:
        data = response.json()
        for store in data:
            store["store_type"] = "全家"
            store["store_name"] = store.get("name", "未知門市")
            store["quantity"] = 1
            store["latitude"] = store.get("lat", 0.0)
            store["longitude"] = store.get("lng", 0.0)

        with open(FAMILY_MART_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"✅ 全家數據下載完成，共 {len(data)} 筆資料")
        print("🔍 前 10 筆全家 JSON:", json.dumps(data[:10], ensure_ascii=False, indent=4))

# 設定地理編碼器
geolocator = Nominatim(user_agent="geoapiExercises", timeout=10)

def find_nearest_store(address, user_lat, user_lon):
    print(f"🔍 收到查詢請求: address={address}, lat={user_lat}, lon={user_lon}")

    if user_lat == 0 or user_lon == 0:
        print("❌ GPS 座標無效，請提供有效數值")
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", ""]]

    user_coords = (user_lat, user_lon)
    print(f"📍 使用 GPS 座標: {user_coords}")

    # **重新下載 7-11 & 全家 JSON**
    fetch_seven_eleven_data()
    fetch_family_mart_data()

    # **檢查 JSON 是否成功下載**
    if not os.path.exists(SEVEN_ELEVEN_FILE) or not os.path.exists(FAMILY_MART_FILE):
        print("⚠️ JSON 下載後仍然不存在，請檢查 API 是否有效")
        return [["❌ 便利商店數據下載失敗", "", "", ""]]

    # **讀取 JSON 檔案**
    with open(SEVEN_ELEVEN_FILE, 'r', encoding='utf-8') as f:
        seven_eleven_data = json.load(f)

    with open(FAMILY_MART_FILE, 'r', encoding='utf-8') as f:
        family_mart_data = json.load(f)

    # **轉換為 DataFrame**
    seven_df = pd.DataFrame(seven_eleven_data)
    family_df = pd.DataFrame(family_mart_data)

    print(f"✅ 7-11 資料行數: {len(seven_df)}, 全家資料行數: {len(family_df)}")

    if seven_df.empty and family_df.empty:
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

    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

interface.launch()
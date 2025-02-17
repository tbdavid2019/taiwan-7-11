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

# 下載 7-11 JSON
def download_seven_eleven_data():
    if not os.path.exists(seven_eleven_file):
        print("⚠️  7-11 JSON 不存在，開始下載...")
        url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"
        response = requests.get(url)
        if response.status_code == 200:
            with open(seven_eleven_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            print("✅  7-11 JSON 下載完成")
        else:
            print(f"❌ 下載 7-11 JSON 失敗，錯誤碼: {response.status_code}")

# 下載全家商店 JSON
def download_family_mart_stores():
    if not os.path.exists(family_mart_stores_file):
        print("⚠️  全家商店 JSON 不存在，開始下載...")
        url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
        response = requests.post(url, json={"store": ""})
        if response.status_code == 200:
            with open(family_mart_stores_file, "w", encoding="utf-8") as f:
                json.dump(response.json(), f, ensure_ascii=False, indent=4)
            print("✅  全家商店 JSON 下載完成")
        else:
            print(f"❌ 下載全家商店 JSON 失敗，錯誤碼: {response.status_code}")

# 下載全家商品 JSON
def download_family_mart_products():
    if not os.path.exists(family_mart_products_file):
        print("⚠️  全家商品 JSON 不存在，開始下載...")
        url = "https://famihealth.family.com.tw/Calculator"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            match = re.search(r'var categories = (\[.*?\]);', response.text, re.S)
            if match:
                categories_data = json.loads(match.group(1))
                results = [
                    {
                        "category": cat.get("name"),
                        "title": prod.get("name"),
                        "picture_url": prod.get("imgurl"),
                        "calories": prod.get("calo", 0)
                    }
                    for cat in categories_data for prod in cat.get("products", [])
                ]
                with open(family_mart_products_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                print("✅  全家商品 JSON 下載完成")

# 讀取 JSON 檔案
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 搜尋最近的店家
def find_nearest_store(address, lat, lon):
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")

    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)
    
    # 讀取商店 JSON
    seven_data = load_json(seven_eleven_file)
    family_data = load_json(family_mart_stores_file)
    family_mart_items = load_json(family_mart_products_file)

    # ----------------------------
    # 將 7-11 資料轉成 DataFrame (依照你實際的 JSON 結構)
    # ----------------------------
    # 假設 seven_data 每一筆包含:
    # {
    #   "StoreName": "7-11 XXX店",
    #   "latitude": 25.123,
    #   "longitude": 121.456,
    #   ...
    # }
    # 請依你實際欄位修改
    seven_df = pd.DataFrame(seven_data)
    if not {"latitude", "longitude"}.issubset(seven_df.columns):
        # 如果 7-11 資料中沒有 latitude/longitude，就先跳過
        return [["❌ 7-11 資料中找不到經緯度欄位", "", "", "", ""]]
    
    # ----------------------------
    # 將全家資料轉成 DataFrame
    # ----------------------------
    # 假設 family_data 裡的欄位是 py_wgs84 / px_wgs84
    # (py_wgs84 = 緯度, px_wgs84 = 經度)
    family_df = pd.DataFrame(family_data)
    if not {"py_wgs84", "px_wgs84"}.issubset(family_df.columns):
        return [["❌ 全家資料中找不到 py_wgs84 / px_wgs84 欄位", "", "", "", ""]]
    
    # 處理經緯度欄位
    seven_df["latitude"] = seven_df["latitude"].astype(float)
    seven_df["longitude"] = seven_df["longitude"].astype(float)
    family_df["latitude"] = family_df["py_wgs84"].astype(float)
    family_df["longitude"] = family_df["px_wgs84"].astype(float)

    # 計算距離
    seven_df["distance_m"] = seven_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
        axis=1
    )
    family_df["distance_m"] = family_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
        axis=1
    )

    # 過濾 3 公里範圍內的商店，並只取前 5 間
    nearby_seven = seven_df[seven_df["distance_m"] <= MAX_DISTANCE].sort_values(by="distance_m").head(5)
    nearby_family = family_df[family_df["distance_m"] <= MAX_DISTANCE].sort_values(by="distance_m").head(5)

    # 如果都沒有符合的店家
    if len(nearby_seven) == 0 and len(nearby_family) == 0:
        return [["❌ 附近 3 公里內沒有便利商店", "", "", "", ""]]

    # 整理成表格輸出 (DataFrame 只能回傳一個，所以可以把兩者合併)
    output = []

    # 7-11
    for _, row in nearby_seven.iterrows():
        store_name = row.get("StoreName", "7-11 未提供店名")
        dist = f"{row['distance_m']:.2f} m"
        # 這裡示範把「商品」先寫成 "7-11 商品" 或自行處理
        output.append([
            store_name,
            dist,
            "7-11 商品(示意)",
            ""
        ])
    
    # 全家
    for _, row in nearby_family.iterrows():
        store_name = row.get("Name", "全家 未提供店名")
        dist = f"{row['distance_m']:.2f} m"
        output.append([
            store_name,
            dist,
            "全家 商品(示意)",
            ""
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

    # 按下「使用目前位置」後，利用 JS 取得地理位置，並自動填入 lat / lon
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

demo.launch(share=True)
import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic

# 7-11 和全家的 JSON 檔案
seven_eleven_file = "seven_eleven_products.json"
family_mart_file = "family_mart_products.json"
family_mart_stores_file = "family_mart_stores.json"
family_mart_products_file = "family_mart_items.json"

# 設定 3 公里範圍
MAX_DISTANCE = 3000  # 限制 3 公里

# 下載 7-11 JSON
def download_seven_eleven_data():
    if not os.path.exists(seven_eleven_file):
        print("⚠️  7-11 JSON 檔案不存在，正在下載...")
        api_url = "https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx"  # 這裡要替換為正確的 URL
        response = requests.get(api_url)

        if response.status_code == 200:
            with open(seven_eleven_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            print("✅  7-11 JSON 下載完成！")
        else:
            print(f"❌ 下載失敗，狀態碼: {response.status_code}")

# 下載全家商店 JSON
def download_family_mart_stores():
    if not os.path.exists(family_mart_stores_file):
        print("⚠️  全家商店 JSON 不存在，正在下載...")
        url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
        response = requests.post(url, json={"store": ""})

        if response.status_code == 200:
            with open(family_mart_stores_file, "w", encoding="utf-8") as f:
                json.dump(response.json(), f, ensure_ascii=False, indent=4)
            print("✅  全家商店 JSON 下載完成！")
        else:
            print(f"❌ 下載失敗，狀態碼: {response.status_code}")

# 下載全家商品 JSON
def download_family_mart_products():
    if not os.path.exists(family_mart_products_file):
        print("⚠️  全家商品 JSON 不存在，正在下載...")
        fUrl = "https://famihealth.family.com.tw/Calculator"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        response = requests.get(fUrl, headers=headers)

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
                print("✅  全家商品 JSON 下載完成！")

# 讀取 JSON 檔案
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

# 搜尋最近的店家
def find_nearest_store(address, lat, lon):
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")

    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)
    
    # 讀取商店 JSON
    seven_eleven_data = load_json(seven_eleven_file)
    family_mart_data = load_json(family_mart_stores_file)

    # 轉換 DataFrame
    seven_df = pd.DataFrame(seven_eleven_data)
    family_df = pd.DataFrame(family_mart_data)

    # 過濾掉沒有座標的數據
    family_df = family_df[family_df["latitude"] > 0]

    # 計算距離
    family_df["distance"] = family_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters, axis=1
    )

    # 過濾 3 公里範圍內的店家
    family_df = family_df[family_df["distance"] <= MAX_DISTANCE]

    # 整理輸出格式
    output = []
    for _, row in family_df.iterrows():
        output.append([
            f"全家 {row['Name']}",
            f"{row['distance']:.2f} m",
            "商品數據",
            "數量"
        ])

    if len(output) == 0:
        return [["❌ 附近 3 公里內沒有便利商店", "", "", "", ""]]

    return output

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## 便利商店門市與商品搜尋")
    gr.Markdown("輸入 GPS 座標來搜尋最近的便利商店與推薦商品")

    address = gr.Textbox(label="輸入地址或留空以使用 GPS")
    lat = gr.Number(label="GPS 緯度 (可選)", value=0)
    lon = gr.Number(label="GPS 經度 (可選)", value=0)

    with gr.Row():
        gps_button = gr.Button("📍 使用目前位置")
        search_button = gr.Button("🔍 搜尋")

    output_table = gr.Dataframe(
        headers=["門市", "距離 (m)", "食物", "數量"],
        interactive=False
    )

    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

demo.launch()
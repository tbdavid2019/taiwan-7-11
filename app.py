import gradio as gr
import requests
import re
import json
import os
import pandas as pd
from xml.etree import ElementTree
from geopy.distance import geodesic

# =============== 檔案路徑設定 (你可依需要修改) ===============
DATA_DIR = "docs/assets"  # 或 "./data" 等
os.makedirs(DATA_DIR, exist_ok=True)

SEVEN_ELEVEN_PRODUCTS_FILE = os.path.join(DATA_DIR, "seven_eleven_products.json")
FAMILY_MART_STORES_FILE = os.path.join(DATA_DIR, "family_mart_stores.json")
FAMILY_MART_PRODUCTS_FILE = os.path.join(DATA_DIR, "family_mart_products.json")

# 3 公里範圍
MAX_DISTANCE = 3000

# -----------------------------------------------------------
# 1. 下載或更新 7-11 商品資料 (目前只示範商品，若要店家需另尋API)
# -----------------------------------------------------------
def fetch_seven_eleven_products(force_update=False):
    """
    從 https://www.7-11.com.tw/freshfoods/Read_Food_xml_hot.aspx
    以各種 category 抓取商品資料(XML)，轉成 JSON 存檔。
    force_update=True 時，強制重新抓取。
    """
    if os.path.exists(SEVEN_ELEVEN_PRODUCTS_FILE) and not force_update:
        print("7-11 商品 JSON 已存在，跳過下載 (如要強制更新請設 force_update=True)")
        return

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

    data_list = []

    # 按照分類依序爬取
    for index, cat in enumerate(categories):
        # 注意：實際參數可能需要你自行測試
        params = {"": index}
        try:
            resp = requests.get(base_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                try:
                    root = ElementTree.fromstring(resp.content)
                    # 解析 XML
                    for item in root.findall(".//Item"):
                        data_list.append({
                            "category": cat,
                            "name": item.findtext("name", ""),
                            "kcal": item.findtext("kcal", ""),
                            "price": item.findtext("price", ""),
                            "image": f'https://www.7-11.com.tw/freshfoods/{cat}/' + item.findtext("image", ""),
                            "special_sale": item.findtext("special_sale", ""),
                            "new": item.findtext("new", ""),
                            "content": item.findtext("content", ""),
                            # 如果你另外有店家經緯度資訊，請自行加上:
                            # "latitude": ...,
                            # "longitude": ...
                        })
                except ElementTree.ParseError:
                    print(f"分類 {cat} 返回非 XML 格式資料，略過。")
            else:
                print(f"分類 {cat} 請求失敗，HTTP 狀態碼: {resp.status_code}")
        except Exception as e:
            print(f"分類 {cat} 請求錯誤: {e}")

    # 儲存到 JSON
    with open(SEVEN_ELEVEN_PRODUCTS_FILE, "w", encoding="utf-8") as jf:
        json.dump(data_list, jf, ensure_ascii=False, indent=4)

    print(f"✅ 7-11 商品資料抓取完成，共 {len(data_list)} 筆，已存為 {SEVEN_ELEVEN_PRODUCTS_FILE}")

# -----------------------------------------------------------
# 2. 下載或更新 全家門市資料 (內含經緯度 py_wgs84, px_wgs84)
# -----------------------------------------------------------
def fetch_family_stores(force_update=False):
    """
    從 https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName
    下載所有全家門市資料(含經緯度 py_wgs84, px_wgs84)並存檔。
    force_update=True 時，強制重新抓取。
    """
    if os.path.exists(FAMILY_MART_STORES_FILE) and not force_update:
        print("全家門市 JSON 已存在，跳過下載 (如要強制更新請設 force_update=True)")
        return

    url = "https://family.map.com.tw/famiport/api/dropdownlist/Select_StoreName"
    post_data = {"store": ""}
    try:
        resp = requests.post(url, json=post_data, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            with open(FAMILY_MART_STORES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ 全家門市資料抓取完成，共 {len(data)} 筆，已存為 {FAMILY_MART_STORES_FILE}")
        else:
            print(f"❌ 全家門市 API 請求失敗，HTTP 狀態碼: {resp.status_code}")
    except Exception as e:
        print(f"❌ 全家門市 API 請求錯誤: {e}")

# -----------------------------------------------------------
# 3. 下載或更新 全家商品資料
# -----------------------------------------------------------
def fetch_family_products(force_update=False):
    """
    從 https://famihealth.family.com.tw/Calculator 解析網頁 JS 中的
    var categories = [...] 取得商品清單。
    force_update=True 時，強制重新抓取。
    """
    if os.path.exists(FAMILY_MART_PRODUCTS_FILE) and not force_update:
        print("全家商品 JSON 已存在，跳過下載 (如要強制更新請設 force_update=True)")
        return

    url = "https://famihealth.family.com.tw/Calculator"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            match = re.search(r'var categories = (\[.*?\]);', resp.text, re.S)
            if match:
                categories_data = json.loads(match.group(1))
                results = []
                for cat in categories_data:
                    cat_name = cat.get("name", "")
                    for product in cat.get("products", []):
                        results.append({
                            "category": cat_name,
                            "title": product.get("name"),
                            "picture_url": product.get("imgurl"),
                            "protein": product.get("protein", 0),
                            "carb": product.get("carb", 0),
                            "calories": product.get("calo", 0),
                            "fat": product.get("fat", 0),
                            "description": product.get("description", ""),
                        })
                with open(FAMILY_MART_PRODUCTS_FILE, "w", encoding="utf-8") as jf:
                    json.dump(results, jf, ensure_ascii=False, indent=4)
                print(f"✅ 全家商品資料抓取完成，共 {len(results)} 筆，已存為 {FAMILY_MART_PRODUCTS_FILE}")
            else:
                print("❌ 找不到 var categories = ... 之內容，無法解析全家商品。")
        else:
            print(f"❌ 全家商品頁面請求失敗，HTTP 狀態碼: {resp.status_code}")
    except Exception as e:
        print(f"❌ 全家商品頁面請求錯誤: {e}")

# -----------------------------------------------------------
# 工具：讀取 JSON 檔
# -----------------------------------------------------------
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# -----------------------------------------------------------
# 4. 主邏輯：依使用者座標，篩選店家並顯示(3 公里內所有店家)
# -----------------------------------------------------------
def find_nearest_store(address, lat, lon):
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")

    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    user_coords = (lat, lon)

    # ========== 讀取 7-11 JSON 並印出前 10 筆 (檢查欄位用) ==========
    seven_data = load_json(SEVEN_ELEVEN_PRODUCTS_FILE)
    print(f"7-11 JSON 總筆數: {len(seven_data)}")
    print("===== 7-11 JSON 前 10 筆 =====")
    print(seven_data[:10])

    # 將 7-11 資料轉成 DataFrame (假設內含 latitude, longitude)
    seven_df = pd.DataFrame(seven_data)
    if {"latitude", "longitude"}.issubset(seven_df.columns):
        seven_df["latitude"] = seven_df["latitude"].astype(float)
        seven_df["longitude"] = seven_df["longitude"].astype(float)
        # 計算距離
        seven_df["distance_m"] = seven_df.apply(
            lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
            axis=1
        )
    else:
        print("⚠️  7-11 JSON 裡沒有 'latitude' 或 'longitude' 欄位，無法計算距離。")
        seven_df = pd.DataFrame()  # 清空，代表無法顯示 7-11 門市

    # ========== 讀取 全家門市 JSON 並印出前 10 筆 (檢查欄位用) ==========
    family_stores = load_json(FAMILY_MART_STORES_FILE)
    print(f"全家 JSON 總筆數: {len(family_stores)}")
    print("===== 全家 JSON 前 10 筆 =====")
    print(family_stores[:10])

    # 轉成 DataFrame (內含 py_wgs84, px_wgs84)
    family_df = pd.DataFrame(family_stores)
    if {"py_wgs84", "px_wgs84"}.issubset(family_df.columns):
        family_df["latitude"] = family_df["py_wgs84"].astype(float)
        family_df["longitude"] = family_df["px_wgs84"].astype(float)
        family_df["distance_m"] = family_df.apply(
            lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).meters,
            axis=1
        )
    else:
        print("⚠️  全家 JSON 裡沒有 'py_wgs84' 或 'px_wgs84' 欄位，無法計算距離。")
        family_df = pd.DataFrame()

    # ========== 篩選 3 公里內的店家 (不只前 5 筆，全部顯示) ==========
    nearby_seven = pd.DataFrame()
    if not seven_df.empty and "distance_m" in seven_df.columns:
        nearby_seven = seven_df[seven_df["distance_m"] <= MAX_DISTANCE].sort_values("distance_m")

    nearby_family = pd.DataFrame()
    if not family_df.empty and "distance_m" in family_df.columns:
        nearby_family = family_df[family_df["distance_m"] <= MAX_DISTANCE].sort_values("distance_m")

    # 若都沒資料
    if nearby_seven.empty and nearby_family.empty:
        return [["❌ 附近 3 公里內沒有便利商店", "", "", "", ""]]

    # ========== 合併輸出 ==========
    output = []

    # 7-11 門市
    if not nearby_seven.empty:
        for _, row in nearby_seven.iterrows():
            store_name = row.get("StoreName", "7-11 未提供店名")
            dist_str = f"{row['distance_m']:.1f} m"
            # 假設要顯示「即期食品」，可自行加判斷或先示範顯示固定字串
            output.append([
                f"7-11 {store_name}",
                dist_str,
                "7-11即期食品(示意)",
                "1"
            ])

    # 全家 門市
    if not nearby_family.empty:
        for _, row in nearby_family.iterrows():
            store_name = row.get("Name", "全家 未提供店名")
            dist_str = f"{row['distance_m']:.1f} m"
            output.append([
                f"全家 {store_name}",
                dist_str,
                "全家即期食品(示意)",
                "1"
            ])

    return output

# -----------------------------------------------------------
# 5. 建立 Gradio 介面
# -----------------------------------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 便利商店門市與商品搜尋 (示範)")
    gr.Markdown("1. 按下「使用目前位置」或自行輸入緯度/經度\n2. 點選「搜尋」查詢 3 公里內的所有店家\n3. 請於 Logs 查看 7-11 和全家 JSON 的前 10 筆結構")

    address = gr.Textbox(label="輸入地址(可留空)")
    lat = gr.Number(label="GPS 緯度", value=0, elem_id="lat")
    lon = gr.Number(label="GPS 經度", value=0, elem_id="lon")

    with gr.Row():
        gps_button = gr.Button("📍 使用目前位置", elem_id="gps-btn")
        search_button = gr.Button("🔍 搜尋")

    output_table = gr.Dataframe(
        headers=["門市", "距離 (m)", "商品/即期食品", "數量"],
        interactive=False
    )

    search_button.click(fn=find_nearest_store, inputs=[address, lat, lon], outputs=output_table)

    gps_button.click(
        None,
        None,
        [lat, lon],
        js="""
        () => {
            return new Promise((resolve) => {
                if (!navigator.geolocation) {
                    alert("您的瀏覽器不支援地理位置功能");
                    resolve([0, 0]);
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve([position.coords.latitude, position.coords.longitude]);
                    },
                    (error) => {
                        alert("無法取得位置：" + error.message);
                        resolve([0, 0]);
                    }
                );
            });
        }
        """
    )

def main():
    """
    主程式入口，可在本地端執行 python 檔案時呼叫此函式，
    先下載/更新資料，再啟動 Gradio。
    """
    # 下載 / 更新 所有資料
    fetch_seven_eleven_products(force_update=False)
    fetch_family_stores(force_update=False)
    fetch_family_products(force_update=False)

    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)

if __name__ == "__main__":
    main()
import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic

# =============== 7-11 所需常數 ===============
# 請確認此處的 MID_V 是否有效，若過期請更新
MID_V = "W0_DiF4DlgU5OeQoRswrRcaaNHMWOL7K3ra3385ocZcv-bBOWySZvoUtH6j-7pjiccl0C5h30uRUNbJXsABCKMqiekSb7tdiBNdVq8Ro5jgk6sgvhZla5iV0H3-8dZfASc7AhEm85679LIK3hxN7Sam6D0LAnYK9Lb0DZhn7xeTeksB4IsBx4Msr_VI"  # 請填入有效的 mid_v
USER_AGENT_7_11 = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
API_7_11_BASE = "https://lovefood.openpoint.com.tw/LoveFood/api"

# =============== FamilyMart 所需常數 ===============
FAMILY_PROJECT_CODE = "202106302"  # 若有需要請自行調整
API_FAMILY = "https://stamp.family.com.tw/api/maps/MapProductInfo"

# 3 公里範圍
MAX_DISTANCE = 3000

# -----------------------------------------------------------
# 7-11: 取得 AccessToken
# -----------------------------------------------------------
def get_7_11_token():
    """
    POST /Auth/FrontendAuth/AccessToken?mid_v=$mid_v
    回傳 JWT token
    """
    url = f"{API_7_11_BASE}/Auth/FrontendAuth/AccessToken?mid_v={MID_V}"
    headers = {
        "user-agent": USER_AGENT_7_11
    }
    resp = requests.post(url, headers=headers, data="")
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 token 失敗: {js}")
    token = js["element"]
    return token

# -----------------------------------------------------------
# 7-11: 取得附近門市清單 (含剩餘即期品總數量)
# -----------------------------------------------------------
def get_7_11_nearby_stores(token, lat, lon):
    """
    POST /Search/FrontendStoreItemStock/GetNearbyStoreList?token=$token
    取得附近門市的「即期品」總數量
    """
    url = f"{API_7_11_BASE}/Search/FrontendStoreItemStock/GetNearbyStoreList?token={token}"
    headers = {
        "user-agent": USER_AGENT_7_11,
        "content-type": "application/json",
    }
    body = {
        "CurrentLocation": {
            "Latitude": lat,
            "Longitude": lon
        },
        "SearchLocation": {
            "Latitude": lat,
            "Longitude": lon
        }
    }
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 附近門市失敗: {js}")
    return js["element"].get("StoreStockItemList", [])

# -----------------------------------------------------------
# 7-11: 取得單一門市的即期品清單
# -----------------------------------------------------------
def get_7_11_store_detail(token, lat, lon, store_no):
    """
    POST /Search/FrontendStoreItemStock/GetStoreDetail?token=$token
    回傳該門市的即期品細項 (商品名稱 / 剩餘數量 等)
    """
    url = f"{API_7_11_BASE}/Search/FrontendStoreItemStock/GetStoreDetail?token={token}"
    headers = {
        "user-agent": USER_AGENT_7_11,
        "content-type": "application/json",
    }
    body = {
        "CurrentLocation": {
            "Latitude": lat,
            "Longitude": lon
        },
        "StoreNo": store_no
    }
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 門市({store_no})資料失敗: {js}")
    return js["element"].get("StoreStockItem", {})

# -----------------------------------------------------------
# FamilyMart: 取得附近門市即期品清單 (單次呼叫可拿到所有商品細項)
# -----------------------------------------------------------
def get_family_nearby_stores(lat, lon):
    """
    POST https://stamp.family.com.tw/api/maps/MapProductInfo
    查詢附近門市及即期品庫存，回傳資料中 code 應為 1 代表成功
    """
    headers = {
        "Content-Type": "application/json;charset=utf-8",
    }
    body = {
        "ProjectCode": FAMILY_PROJECT_CODE,
        "latitude": lat,
        "longitude": lon
    }
    resp = requests.post(API_FAMILY, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    # 修改判斷：根據回傳範例，成功時 code 為 1
    if js.get("code") != 1:
        raise RuntimeError(f"取得全家門市資料失敗: {js}")
    return js["data"]

# -----------------------------------------------------------
# Gradio 查詢邏輯
# -----------------------------------------------------------
def find_nearest_store(address, lat, lon):
    """
    1. 使用者輸入經緯度
    2. 查詢 7-11 與 FamilyMart 的即期品清單
    3. 合併結果後顯示
    """
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}")
    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]]

    result_rows = []

    # ------------------ 7-11 ------------------
    try:
        token_711 = get_7_11_token()
        nearby_stores_711 = get_7_11_nearby_stores(token_711, lat, lon)
        for store in nearby_stores_711:
            dist_m = store.get("Distance", 999999)
            if dist_m <= MAX_DISTANCE:
                store_no = store.get("StoreNo")
                store_name = store.get("StoreName", "7-11 未提供店名")
                remaining_qty = store.get("RemainingQty", 0)
                if remaining_qty > 0:
                    detail = get_7_11_store_detail(token_711, lat, lon, store_no)
                    for cat in detail.get("CategoryStockItems", []):
                        cat_name = cat.get("Name", "")
                        for item in cat.get("ItemList", []):
                            item_name = item.get("ItemName", "")
                            item_qty = item.get("RemainingQty", 0)
                            row = [
                                f"7-11 {store_name}",
                                f"{dist_m:.1f} m",
                                f"{cat_name} - {item_name}",
                                str(item_qty)
                            ]
                            result_rows.append(row)
                else:
                    row = [
                        f"7-11 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0"
                    ]
                    result_rows.append(row)
    except Exception as e:
        print(f"❌ 取得 7-11 即期品時發生錯誤: {e}")

    # ------------------ FamilyMart ------------------
    try:
        nearby_stores_family = get_family_nearby_stores(lat, lon)
        for store in nearby_stores_family:
            dist_m = store.get("distance", 999999)
            if dist_m <= MAX_DISTANCE:
                store_name = store.get("name", "全家 未提供店名")
                info_list = store.get("info", [])
                has_item = False
                for big_cat in info_list:
                    big_cat_name = big_cat.get("name", "")
                    for subcat in big_cat.get("categories", []):
                        subcat_name = subcat.get("name", "")
                        for product in subcat.get("products", []):
                            product_name = product.get("name", "")
                            qty = product.get("qty", 0)
                            if qty > 0:
                                has_item = True
                                row = [
                                    f"全家 {store_name}",
                                    f"{dist_m:.1f} m",
                                    f"{big_cat_name} - {subcat_name} - {product_name}",
                                    str(qty)
                                ]
                                result_rows.append(row)
                if not has_item:
                    row = [
                        f"全家 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0"
                    ]
                    result_rows.append(row)
    except Exception as e:
        print(f"❌ 取得全家 即期品時發生錯誤: {e}")

    if not result_rows:
        return [["❌ 附近 3 公里內沒有即期食品", "", "", "", ""]]

    return result_rows

# -----------------------------------------------------------
# Gradio 介面
# -----------------------------------------------------------
with gr.Blocks() as demo:
    gr.Markdown("## 便利商店「即期食品」搜尋示範")
    gr.Markdown("""
    1. 按下「使用目前位置」或自行輸入緯度/經度  
    2. 點選「搜尋」查詢 3 公里內 7-11 / 全家的即期品  
    3. 若要執行，需要有效的 mid_v (7-11 愛食記憶官網)  
    4. 在 Logs 查看詳細錯誤或除錯資訊
    """)
    address = gr.Textbox(label="輸入地址(可留空)")
    lat = gr.Number(label="GPS 緯度", value=0, elem_id="lat")
    lon = gr.Number(label="GPS 經度", value=0, elem_id="lon")

    with gr.Row():
        gps_button = gr.Button("📍 ❶ 使用目前位置-先按這個 並等待3秒 ", elem_id="gps-btn")
        search_button = gr.Button("🔍 ❷ 搜尋 ")

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
    主程式入口，在本地端執行:
      python your_script.py
    """
    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)

if __name__ == "__main__":
    main()
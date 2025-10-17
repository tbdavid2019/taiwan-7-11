import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic

# =============== 7-11 所需常數 ===============
# 請確認此處的 MID_V 是否有效，若過期請更新
MID_V = "W0_DiF4DlgU5OeQoRswrRcaaNHMWOL7K3ra3385ocZcv-bBOWySZvoUtH6j-7pjiccl0C5h30uRUNbJXsABCKMqiekSb7tdiBNdVq8Ro5jgk6sgvhZla5iV0H3-8dZfASc7AhEm85679LIK3hxN7Sam6D0LAnYK9Lb0DZhn7xeTeksB4IsBx4Msr_VI"
USER_AGENT_7_11 = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
API_7_11_BASE = "https://lovefood.openpoint.com.tw/LoveFood/api"

# =============== FamilyMart 所需常數 ===============
FAMILY_PROJECT_CODE = "202106302"  # 若有需要請自行調整
API_FAMILY = "https://stamp.family.com.tw/api/maps/MapProductInfo"


def get_7_11_token():
    url = f"{API_7_11_BASE}/Auth/FrontendAuth/AccessToken?mid_v={MID_V}"
    headers = {"user-agent": USER_AGENT_7_11}
    resp = requests.post(url, headers=headers, data="")
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 token 失敗: {js}")
    return js["element"]

def get_7_11_nearby_stores(token, lat, lon):
    url = f"{API_7_11_BASE}/Search/FrontendStoreItemStock/GetNearbyStoreList?token={token}"
    headers = {
        "user-agent": USER_AGENT_7_11,
        "content-type": "application/json",
    }
    body = {
        "CurrentLocation": {"Latitude": lat, "Longitude": lon},
        "SearchLocation": {"Latitude": lat, "Longitude": lon}
    }
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 附近門市失敗: {js}")
    return js["element"].get("StoreStockItemList", [])

def get_7_11_store_detail(token, lat, lon, store_no):
    url = f"{API_7_11_BASE}/Search/FrontendStoreItemStock/GetStoreDetail?token={token}"
    headers = {
        "user-agent": USER_AGENT_7_11,
        "content-type": "application/json",
    }
    body = {
        "CurrentLocation": {"Latitude": lat, "Longitude": lon},
        "StoreNo": store_no
    }
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    if not js.get("isSuccess"):
        raise RuntimeError(f"取得 7-11 門市({store_no})資料失敗: {js}")
    return js["element"].get("StoreStockItem", {})

def get_family_nearby_stores(lat, lon):
    headers = {"Content-Type": "application/json;charset=utf-8"}
    body = {
        "ProjectCode": FAMILY_PROJECT_CODE,
        "latitude": lat,
        "longitude": lon
    }
    resp = requests.post(API_FAMILY, headers=headers, json=body)
    resp.raise_for_status()
    js = resp.json()
    if js.get("code") != 1:
        raise RuntimeError(f"取得全家門市資料失敗: {js}")
    return js["data"]

def find_nearest_store(address, lat, lon, distance_km):
    """
    distance_km: 從下拉選單取得的「公里」(字串)，例如 '3' or '5' ...
    """
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}, distance_km={distance_km}")

    # 若有填地址但 lat/lon 為 0，嘗試用 Google Geocoding API
    if address and address.strip() != "" and (lat == 0 or lon == 0):
        try:
            import requests
            import os
            googlekey = os.environ.get("googlekey")
            if not googlekey:
                raise RuntimeError("未設定 googlekey，請於 Huggingface Space Secrets 設定。")
            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": address,
                "key": googlekey
            }
            resp = requests.get(geocode_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                lat = float(location["lat"])
                lon = float(location["lng"])
                print(f"地址轉換成功: {address} => lat={lat}, lon={lon}")
            else:
                print(f"❌ Google Geocoding 失敗: {data}")
                return [["❌ 地址轉換失敗，請輸入正確地址", "", "", "", ""]], 0, 0
        except Exception as e:
            print(f"❌ Google Geocoding 失敗: {e}")
            return [["❌ 地址轉換失敗，請輸入正確地址", "", "", "", ""]], 0, 0

    if lat == 0 or lon == 0:
        return [["❌ 請輸入地址或提供 GPS 座標", "", "", "", ""]], lat, lon

    # 將 km 轉成公尺
    max_distance = float(distance_km) * 1000

    result_rows = []

    # ------------------ 7-11 ------------------
    try:
        token_711 = get_7_11_token()
        nearby_stores_711 = get_7_11_nearby_stores(token_711, lat, lon)
        for store in nearby_stores_711:
            dist_m = store.get("Distance", 999999)
            if dist_m <= max_distance:
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
                                str(item_qty),
                                dist_m  # 用來排序
                            ]
                            result_rows.append(row)
                else:
                    row = [
                        f"7-11 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0",
                        dist_m
                    ]
                    result_rows.append(row)
    except Exception as e:
        print(f"❌ 取得 7-11 即期品時發生錯誤: {e}")

    # ------------------ FamilyMart ------------------
    try:
        nearby_stores_family = get_family_nearby_stores(lat, lon)
        for store in nearby_stores_family:
            dist_m = store.get("distance", 999999)
            if dist_m <= max_distance:
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
                                    str(qty),
                                    dist_m
                                ]
                                result_rows.append(row)
                if not has_item:
                    row = [
                        f"全家 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0",
                        dist_m
                    ]
                    result_rows.append(row)
    except Exception as e:
        print(f"❌ 取得全家 即期品時發生錯誤: {e}")

    if not result_rows:
        return [["❌ 附近沒有即期食品 (在所選公里範圍內)", "", "", "", ""]], lat, lon

    # 排序：依照最後一欄 (float 距離) 做由小到大排序
    result_rows.sort(key=lambda x: x[4])
    # 移除最後一欄 (不顯示給前端)
    for row in result_rows:
        row.pop()

    return result_rows, lat, lon

# ========== Gradio 介面 ==========

import gradio as gr

def main():
    with gr.Blocks(
        title="便利商店即期食品查詢",
        favicon_path="assets/favicon.svg",
    ) as demo:
        gr.Markdown("## 台灣7-11 和 family全家便利商店「即期食品」 乞丐時光搜尋")
        gr.Markdown("""
        1. 按下「📍🔍 自動定位並搜尋」可自動取得目前位置並直接查詢附近即期品
        2. 也可手動輸入地址、緯度、經度與搜尋範圍後再按此按鈕
        3. 意見反應 telegram @a7a8a9abc
        """)

        address = gr.Textbox(label="地址(可留空)", placeholder="可留空白,通常不用填")
        lat = gr.Number(label="GPS 緯度", value=0, elem_id="lat")
        lon = gr.Number(label="GPS 經度", value=0, elem_id="lon")

        # 下拉選單，提供可選距離 (公里)
        distance_dropdown = gr.Dropdown(
            label="搜尋範圍 (公里)",
            choices=["3", "5", "7", "13", "21"],
            value="3",        # 預設 3 公里
            interactive=True
        )

        with gr.Row():
            auto_gps_search_button = gr.Button("📍🔍 自動定位並搜尋", elem_id="auto-gps-search-btn")

        output_table = gr.Dataframe(
            headers=["門市", "距離 (m)", "商品/即期食品", "數量"],
            interactive=False
        )

        # 只保留自動定位並搜尋按鈕

        # (已移除 gps_button)

        # 新增自動定位並搜尋按鈕
        # auto_gps_search_button.click(
        #     fn=find_nearest_store,
        #     inputs=[address, lat, lon, distance_dropdown],
        #     outputs=output_table,
        #     js="""
        #     (address, lat, lon, distance) => {
        #         return new Promise((resolve) => {
        #             if (!navigator.geolocation) {
        #                 alert("您的瀏覽器不支援地理位置功能");
        #                 resolve([address, 0, 0, distance]);
        #                 return;
        #             }
        #             navigator.geolocation.getCurrentPosition(
        #                 (position) => {
        #                     resolve([address, position.coords.latitude, position.coords.longitude, distance]);
        #                 },
        #                 (error) => {
        #                     alert("無法取得位置：" + error.message);
        #                     resolve([address, 0, 0, distance]);
        #                 }
        #             );
        #         });
        #     }
        #     """
        # )

        # 修正版：自動定位並搜尋，查詢同時回填 lat/lon 欄位，address 有填時不抓 GPS
        auto_gps_search_button.click(
            fn=find_nearest_store,
            inputs=[address, lat, lon, distance_dropdown],
            outputs=[output_table, lat, lon],
            js="""
            (address, lat, lon, distance) => {
                function isZero(val) {
                    return !val || Number(val) === 0;
                }
                if (address && address.trim() !== "") {
                    // 有填地址，直接查詢，不抓 GPS
                    return [address, Number(lat), Number(lon), distance, Number(lat), Number(lon)];
                }
                if (!isZero(lat) && !isZero(lon)) {
                    // 沒填地址但有座標，直接查詢
                    return [address, Number(lat), Number(lon), distance, Number(lat), Number(lon)];
                }
                // 沒填地址且沒座標，抓 GPS
                return new Promise((resolve) => {
                    if (!navigator.geolocation) {
                        alert("您的瀏覽器不支援地理位置功能");
                        resolve([address, 0, 0, distance, 0, 0]);
                        return;
                    }
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const newLat = position.coords.latitude;
                            const newLon = position.coords.longitude;
                            resolve([address, newLat, newLon, distance, newLat, newLon]);
                        },
                        (error) => {
                            alert("無法取得位置：" + error.message);
                            resolve([address, 0, 0, distance, 0, 0]);
                        }
                    );
                });
            }
            """
        )

        demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)

if __name__ == "__main__":
    main()

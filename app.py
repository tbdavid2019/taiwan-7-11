import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic
from dotenv import load_dotenv
import uuid

load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
GOOGLE_GEOCODING_API_KEY = os.environ.get("googlekey") or GOOGLE_MAPS_API_KEY

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


def _get_first(mapping, *keys):
    for key in keys:
        if not isinstance(mapping, dict):
            continue
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _generate_map_html(center_lat, center_lon, markers):
    """生成互動式 Google Maps HTML（優先方案）"""
    if not markers:
        print("⚠️ 警告：沒有門市標記資料")
        return None

    print(f"🗺️ [方案1: HTML] 準備生成互動地圖：中心點 ({center_lat}, {center_lon})，門市數量：{len(markers)}")

    center_lat = _to_float(center_lat)
    center_lon = _to_float(center_lon)

    if center_lat is None or center_lon is None:
        for marker in markers:
            lat_candidate = _to_float(marker.get("lat"))
            lon_candidate = _to_float(marker.get("lng"))
            if lat_candidate is not None and lon_candidate is not None:
                center_lat = lat_candidate
                center_lon = lon_candidate
                break

    if center_lat is None or center_lon is None:
        print("❌ 錯誤：無法確定地圖中心點座標")
        return None
    
    # 使用 iframe 方式嵌入 Google Maps（不需要 API key）
    maps_url = f"https://www.google.com/maps/search/?api=1&query={center_lat},{center_lon}&zoom=14"
    
    html = f"""
<div style="width: 100%; max-width: 900px; margin: 0 auto;">
    <div style="width: 100%; height: 450px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 16px;">
        <iframe 
            width="100%" 
            height="100%" 
            frameborder="0" 
            style="border:0"
            referrerpolicy="no-referrer-when-downgrade"
            src="{maps_url}"
            allowfullscreen>
        </iframe>
    </div>
    <div style="text-align: center; color: #666; font-size: 14px;">
        <p style="margin: 8px 0;">
            📍 找到 <strong>{len(markers)}</strong> 個門市 | 
            <a href="{maps_url}" target="_blank" style="color: #1a73e8; text-decoration: none; font-weight: 500;">
                🔗 在新分頁開啟完整地圖
            </a>
        </p>
    </div>
</div>
"""
    
    print(f"✅ [方案1: HTML] iframe 地圖生成成功，顯示 {len(markers)} 個門市")
    return html


def _generate_map_static(center_lat, center_lon, markers):
    """生成 Google Maps Static API 圖片 HTML（備用方案）"""
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ [方案2: 靜態圖] 警告：未設定 GOOGLE_MAPS_API_KEY，無法生成靜態地圖")
        return None
    
    if not markers:
        return None

    print(f"🗺️ [方案2: 靜態圖] 準備生成靜態地圖：中心點 ({center_lat}, {center_lon})，門市數量：{len(markers)}")

    center_lat = _to_float(center_lat)
    center_lon = _to_float(center_lon)

    if center_lat is None or center_lon is None:
        for marker in markers:
            lat_candidate = _to_float(marker.get("lat"))
            lon_candidate = _to_float(marker.get("lng"))
            if lat_candidate is not None and lon_candidate is not None:
                center_lat = lat_candidate
                center_lon = lon_candidate
                break

    if center_lat is None or center_lon is None:
        return None
    
    # 建立標記字串
    marker_params = []
    
    # 首先加入用戶位置標記（綠色，圖標樣式）
    user_marker = f"color:green|label:📍|{center_lat},{center_lon}"
    marker_params.append(user_marker)
    
    # 然後加入門市標記
    for marker in markers[:10]:
        lat = _to_float(marker.get("lat"))
        lng = _to_float(marker.get("lng"))
        map_num = marker.get("map_number", "")
        if lat is not None and lng is not None:
            color = "red" if "7-11" in marker.get("title", "") else "blue"
            # 使用 map_number 作為標籤
            label = str(map_num) if map_num else ""
            marker_params.append(f"color:{color}|label:{label}|{lat},{lng}")
    
    markers_str = "&".join([f"markers={m}" for m in marker_params])
    
    zoom = 14 if len(markers) > 1 else 15
    map_url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={center_lat},{center_lon}"
        f"&zoom={zoom}"
        f"&size=800x400"
        f"&maptype=roadmap"
        f"&{markers_str}"
        f"&key={GOOGLE_MAPS_API_KEY}"
    )
    
    # 包裝成 HTML img 標籤，並加上門市編號對照表
    maps_link = f"https://www.google.com/maps/search/?api=1&query={center_lat},{center_lon}"
    
    # 生成門市編號對照表
    store_legend = []
    
    # 先加入用戶位置說明
    store_legend.append(
        f'<div style="margin: 4px 0; text-align: left; font-weight: 500; color: #2e7d32;">'
        f'🟢 您的位置 ({center_lat:.4f}, {center_lon:.4f})'
        f'</div>'
    )
    
    # 然後加入門市列表
    for marker in markers[:10]:
        map_num = marker.get("map_number", "")
        title = marker.get("title", "門市")
        dist = marker.get("distance_m", 0)
        color = "🔴" if "7-11" in title else "🔵"
        store_legend.append(
            f'<div style="margin: 4px 0; text-align: left;">'
            f'{color} <strong>{map_num}</strong>. {title} ({dist:.0f}m)'
            f'</div>'
        )
    
    legend_html = "".join(store_legend)
    
    html = f"""
<div style="width: 100%; max-width: 900px; margin: 0 auto;">
    <div style="width: 100%; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 16px;">
        <img src="{map_url}" alt="門市地圖" style="width: 100%; height: auto; display: block;" />
    </div>
    <div style="text-align: center; color: #666; font-size: 14px; margin-bottom: 16px;">
        <p style="margin: 8px 0;">
            📍 找到 <strong>{len(markers)}</strong> 個門市 | 
            <a href="{maps_link}" target="_blank" style="color: #1a73e8; text-decoration: none; font-weight: 500;">
                🔗 在新分頁開啟完整地圖
            </a>
        </p>
    </div>
    <div style="background: #f8f9fa; border-radius: 8px; padding: 12px; font-size: 13px;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #333;">📋 地圖標記對照：</div>
        {legend_html}
    </div>
</div>
"""
    
    print(f"✅ [方案2: 靜態圖] 地圖 HTML 生成完成，包含 {len(marker_params)} 個標記")
    return html


def _generate_map_markdown(center_lat, center_lon, markers):
    """生成包含 Google Maps 連結的 Markdown（最終備用方案）"""
    if not markers:
        print("⚠️ 警告：沒有門市標記資料")
        return None

    print(f"🗺️ [方案3: Markdown] 準備生成文字連結：中心點 ({center_lat}, {center_lon})，門市數量：{len(markers)}")

    center_lat = _to_float(center_lat)
    center_lon = _to_float(center_lon)

    if center_lat is None or center_lon is None:
        for marker in markers:
            lat_candidate = _to_float(marker.get("lat"))
            lon_candidate = _to_float(marker.get("lng"))
            if lat_candidate is not None and lon_candidate is not None:
                center_lat = lat_candidate
                center_lon = lon_candidate
                break

    if center_lat is None or center_lon is None:
        print("❌ 錯誤：無法確定地圖中心點座標")
        return None
    
    # 生成門市列表文字
    store_list = []
    for idx, marker in enumerate(markers[:10], 1):
        title = marker.get("title", "門市")
        lat = _to_float(marker.get("lat"))
        lng = _to_float(marker.get("lng"))
        dist = marker.get("distance_m")
        
        if lat and lng:
            # 生成 Google Maps 連結
            maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            dist_text = f" ({dist:.0f}m)" if dist else ""
            store_list.append(f"{idx}. [{title}]({maps_link}){dist_text}")
    
    # 生成顯示所有門市的地圖連結
    all_markers_url = f"https://www.google.com/maps/search/?api=1&query={center_lat},{center_lon}"
    
    markdown_text = f"""
### 📍 找到 {len(markers)} 個門市

[🗺️ 在 Google Maps 查看完整地圖]({all_markers_url})

#### 門市列表（點擊查看位置）：
{chr(10).join(store_list[:10])}
"""
    
    print(f"✅ [方案3: Markdown] 地圖連結生成完成，包含 {len(store_list)} 個門市")
    return markdown_text


def find_nearest_store(address, lat, lon, distance_km):
    """
    distance_km: 從下拉選單取得的「公里」(字串)，例如 '3' or '5' ...
    """
    print(f"🔍 收到查詢請求: address={address}, lat={lat}, lon={lon}, distance_km={distance_km}")

    hidden_map = gr.update(value="", visible=False)

    def build_message_row(message):
        return [[message, "", "", "", ""]]

    # 若有填地址但 lat/lon 為 0，嘗試用 Google Geocoding API
    if address and address.strip() != "" and (lat == 0 or lon == 0):
        try:
            import requests
            googlekey = GOOGLE_GEOCODING_API_KEY
            if not googlekey:
                raise RuntimeError("未設定 GOOGLE_MAPS_API_KEY，請於 .env 或環境變數中設定。")
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
                return build_message_row("❌ 地址轉換失敗，請輸入正確地址"), 0, 0, hidden_map
        except Exception as e:
            print(f"❌ Google Geocoding 失敗: {e}")
            return build_message_row("❌ 地址轉換失敗，請輸入正確地址"), 0, 0, hidden_map

    if lat == 0 or lon == 0:
        return build_message_row("❌ 請輸入地址或提供 GPS 座標"), lat, lon, hidden_map

    # 將 km 轉成公尺
    max_distance = float(distance_km) * 1000

    result_rows = []
    map_store_info = {}

    def update_marker(brand, identifier, store_name, distance_m, *, lat_value=None, lon_value=None, address_text=None, items=None):
        key = f"{brand}-{identifier or store_name}"
        entry = map_store_info.setdefault(
            key,
            {
                "brand": brand,
                "title": f"{brand} {store_name}" if store_name else brand,
                "lat": None,
                "lng": None,
                "distance_m": None,
                "address": None,
                "items": [],
            },
        )

        lat_float = _to_float(lat_value)
        lon_float = _to_float(lon_value)
        dist_float = _to_float(distance_m)

        if lat_float is not None:
            entry["lat"] = lat_float
        if lon_float is not None:
            entry["lng"] = lon_float
        if dist_float is not None:
            if entry["distance_m"] is None or dist_float < entry["distance_m"]:
                entry["distance_m"] = dist_float
        if address_text:
            entry["address"] = address_text
        if items:
            for item in items:
                if item and item not in entry["items"]:
                    entry["items"].append(item)

        return entry

    # ------------------ 7-11 ------------------
    try:
        token_711 = get_7_11_token()
        nearby_stores_711 = get_7_11_nearby_stores(token_711, lat, lon)
        
        # Debug: 檢查第一個門市的完整資料結構
        if nearby_stores_711 and len(nearby_stores_711) > 0:
            import json
            print(f"🔍 7-11 API 第一個門市的完整資料：")
            print(json.dumps(nearby_stores_711[0], ensure_ascii=False, indent=2))
        
        for store in nearby_stores_711:
            dist_m = _to_float(_get_first(store, "Distance", "distance"))
            if dist_m is None:
                dist_m = float("inf")
            if dist_m <= max_distance:
                store_no = store.get("StoreNo")
                store_name = store.get("StoreName", "7-11 未提供店名")
                remaining_qty = store.get("RemainingQty", 0)

                store_lat = _get_first(store, "StoreLatitude", "Latitude", "Lat", "storeLatitude", "LatitudeWgs84")
                store_lon = _get_first(store, "StoreLongitude", "Longitude", "Lng", "storeLongitude", "LongitudeWgs84")
                store_addr = _get_first(store, "StoreAddress", "Address")

                detail_data = None
                detail_loaded = False

                def ensure_detail():
                    nonlocal detail_data, detail_loaded
                    if detail_loaded:
                        return detail_data
                    detail_loaded = True
                    try:
                        detail_data = get_7_11_store_detail(token_711, lat, lon, store_no)
                    except Exception as detail_err:
                        print(f"⚠️ 取得 7-11 門市({store_no})詳細失敗: {detail_err}")
                        detail_data = {}
                    return detail_data

                if store_lat is None or store_lon is None or not store_addr:
                    detail_candidate = ensure_detail()
                    if isinstance(detail_candidate, dict):
                        store_lat = store_lat or _get_first(detail_candidate, "StoreLat", "Latitude", "Lat")
                        store_lon = store_lon or _get_first(detail_candidate, "StoreLng", "Longitude", "Lng")
                        store_addr = store_addr or _get_first(detail_candidate, "StoreAddress", "Address")

                # Debug: 檢查座標是否取得
                if store_lat is None or store_lon is None:
                    print(f"⚠️ 7-11 {store_name} ({store_no}) 缺少座標: lat={store_lat}, lon={store_lon}")
                else:
                    print(f"✅ 7-11 {store_name} ({store_no}) 座標: ({store_lat}, {store_lon})")

                marker_entry = update_marker(
                    "7-11",
                    store_no,
                    store_name,
                    dist_m,
                    lat_value=store_lat,
                    lon_value=store_lon,
                    address_text=store_addr,
                )

                if remaining_qty > 0:
                    detail = ensure_detail()
                    if isinstance(detail, dict):
                        categories = detail.get("CategoryStockItems", [])
                    else:
                        categories = []
                    for cat in categories:
                        cat_name = cat.get("Name", "")
                        for item in cat.get("ItemList", []):
                            item_name = item.get("ItemName", "")
                            item_qty = item.get("RemainingQty", 0)
                            row = [
                                f"7-11 {store_name}",
                                f"{dist_m:.1f} m",
                                f"{cat_name} - {item_name}",
                                str(item_qty),
                                dist_m,
                            ]
                            result_rows.append(row)

                            item_desc = f"{cat_name} - {item_name}".strip(" -")
                            if item_qty not in (None, "", 0):
                                item_desc = f"{item_desc} x{item_qty}"
                            update_marker(
                                "7-11",
                                store_no,
                                store_name,
                                dist_m,
                                items=[item_desc],
                            )
                else:
                    # 即使沒有即期品，也要加入地圖標記
                    row = [
                        f"7-11 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0",
                        dist_m,
                    ]
                    result_rows.append(row)
                    # 確保沒有即期品的 7-11 也顯示在地圖上
                    update_marker(
                        "7-11",
                        store_no,
                        store_name,
                        dist_m,
                        items=["即期品 0 項"],
                    )
    except Exception as e:
        print(f"❌ 取得 7-11 即期品時發生錯誤: {e}")

    # ------------------ FamilyMart ------------------
    try:
        nearby_stores_family = get_family_nearby_stores(lat, lon)
        for store in nearby_stores_family:
            dist_m = _to_float(_get_first(store, "distance", "Distance"))
            if dist_m is None:
                dist_m = float("inf")
            if dist_m <= max_distance:
                store_name = store.get("name", "全家 未提供店名")
                store_id = _get_first(store, "storeid", "storeId", "StoreId", "id", "store_no")
                store_lat = _get_first(store, "latitude", "Latitude", "lat")
                store_lon = _get_first(store, "longitude", "Longitude", "lng")
                store_addr = _get_first(store, "address", "addr", "Address")

                update_marker(
                    "全家",
                    store_id,
                    store_name,
                    dist_m,
                    lat_value=store_lat,
                    lon_value=store_lon,
                    address_text=store_addr,
                )

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
                                    dist_m,
                                ]
                                result_rows.append(row)

                                item_desc = f"{big_cat_name} - {subcat_name} - {product_name}".strip(" -")
                                if qty not in (None, "", 0):
                                    item_desc = f"{item_desc} x{qty}"
                                update_marker(
                                    "全家",
                                    store_id,
                                    store_name,
                                    dist_m,
                                    items=[item_desc],
                                )
                if not has_item:
                    row = [
                        f"全家 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0",
                        dist_m,
                    ]
                    result_rows.append(row)
    except Exception as e:
        print(f"❌ 取得全家 即期品時發生錯誤: {e}")

    if not result_rows:
        return build_message_row("❌ 附近沒有即期食品 (在所選公里範圍內)"), lat, lon, hidden_map

    # 排序：依照最後一欄 (float 距離) 做由小到大排序
    result_rows.sort(key=lambda x: x[4])
    # 移除最後一欄 (不顯示給前端)
    for row in result_rows:
        row.pop()

    markers = []
    for entry in map_store_info.values():
        title = entry.get("title")
        lat = entry.get("lat")
        lng = entry.get("lng")
        
        if lat is None or lng is None:
            print(f"⚠️ 跳過無座標的門市: {title} (lat={lat}, lng={lng})")
            continue
        
        markers.append(
            {
                "title": title,
                "lat": lat,
                "lng": lng,
                "distance_m": entry.get("distance_m"),
                "address": entry.get("address"),
                "items": entry.get("items", []),
            }
        )
    
    print(f"📍 總共加入 {len(markers)} 個門市到地圖標記")

    markers.sort(key=lambda item: item.get("distance_m") if item.get("distance_m") is not None else float("inf"))

    # 為 markers 加上編號（從 1 開始）
    for idx, marker in enumerate(markers, 1):
        marker["map_number"] = idx

    # 在 result_rows 前面加上對應的地圖編號
    # 建立 store_key 到 map_number 的映射
    store_to_number = {}
    for marker in markers:
        # 從 title 中提取 store_key（brand + store_no）
        title = marker.get("title", "")
        store_to_number[title] = marker.get("map_number", "")
    
    # 為每個 result_row 加上地圖編號
    for row in result_rows:
        store_name = row[0]  # 例如 "7-11 龍門" 或 "全家 宜農"
        
        # 在 map_store_info 中找到對應的 store_key
        matched_number = ""
        for store_key, entry in map_store_info.items():
            if entry.get("title") == store_name:
                matched_number = store_to_number.get(store_name, "")
                break
        
        # 在最前面插入地圖編號
        row.insert(0, str(matched_number) if matched_number else "-")

    # 主要方案：使用靜態圖片（需要 API key）
    try:
        if GOOGLE_MAPS_API_KEY:
            map_display = _generate_map_static(lat, lon, markers)
            if map_display:
                print("✅ 使用靜態地圖顯示")
                map_component = gr.update(value=map_display, visible=True)
                return result_rows, lat, lon, map_component
        else:
            print("⚠️ 未設定 GOOGLE_MAPS_API_KEY")
    except Exception as e:
        print(f"⚠️ 靜態地圖生成失敗: {e}")
    
    # 備用方案：使用 Markdown 連結（無需 API key）
    try:
        map_markdown = _generate_map_markdown(lat, lon, markers)
        if map_markdown:
            print("✅ 使用 Markdown 文字連結（備用方案）")
            map_component = gr.update(value=map_markdown, visible=True)
            return result_rows, lat, lon, map_component
    except Exception as e:
        print(f"⚠️ Markdown 方案失敗: {e}")
    
    # 所有方案都失敗，隱藏地圖但不影響主要功能
    print("ℹ️ 地圖功能暫時無法使用，但門市搜尋功能正常")
    return result_rows, lat, lon, hidden_map

# ========== Gradio 介面 ==========

import gradio as gr

def main():
    with gr.Blocks() as demo:
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

        # 使用 HTML 組件支援 iframe，同時可以顯示靜態圖片或 Markdown
        map_display = gr.HTML(label="門市地圖", visible=False, elem_id="store-map-container")

        output_table = gr.Dataframe(
            headers=["地圖編號", "門市", "距離 (m)", "商品/即期食品", "數量"],
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
            outputs=[output_table, lat, lon, map_display],
            js="""
            (address, lat, lon, distance) => {
                function isZero(val) {
                    return !val || Number(val) === 0;
                }

                if (address && address.trim() !== "") {
                    // 有填地址，直接查詢，不抓 GPS
                    return [address, Number(lat), Number(lon), distance];
                }
                if (!isZero(lat) && !isZero(lon)) {
                    // 沒填地址但有座標，直接查詢
                    return [address, Number(lat), Number(lon), distance];
                }
                // 沒填地址且沒座標，抓 GPS
                return new Promise((resolve) => {
                    if (!navigator.geolocation) {
                        alert("您的瀏覽器不支援地理位置功能");
                        resolve([address, 0, 0, distance]);
                        return;
                    }
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const newLat = position.coords.latitude;
                            const newLon = position.coords.longitude;
                            resolve([address, newLat, newLon, distance]);
                        },
                        (error) => {
                            alert("無法取得位置：" + error.message);
                            resolve([address, 0, 0, distance]);
                        }
                    );
                });
            }
            """
        )

        demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)

if __name__ == "__main__":
    main()
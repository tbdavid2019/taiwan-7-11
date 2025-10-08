import gradio as gr
import requests
import json
import os
import pandas as pd
from geopy.distance import geodesic
from dotenv import load_dotenv
import uuid
from string import Template

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
        if not GOOGLE_MAPS_API_KEY or not markers:
                return None

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

        container_id = f"store-map-{uuid.uuid4().hex}"
        markers_json = json.dumps(markers, ensure_ascii=False)
        center_json = json.dumps({"lat": center_lat, "lng": center_lon})

        template = Template(
                """
<div id="$container_id" style="width: 100%; min-height: 420px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"></div>
<script>
(() => {
    const containerId = "$container_id";
    const center = $center_json;
    const markers = $markers_json;

    const ensureScript = () => {
        if (!window.__googleMapsLoader) {
            window.__googleMapsLoader = new Promise((resolve) => {
                const script = document.createElement('script');
                script.src = "https://maps.googleapis.com/maps/api/js?key=$api_key";
                script.async = true;
                script.defer = true;
                script.onload = resolve;
                document.head.appendChild(script);
            });
        }
        return window.__googleMapsLoader;
    };

    const escapeHtml = (str) => {
        return String(str ?? "").replace(/[&<>"']/g, (ch) => {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
            return map[ch] ?? ch;
        });
    };

    const initMap = () => {
        const el = document.getElementById(containerId);
        if (!el || !window.google || !window.google.maps) return;
        const map = new google.maps.Map(el, {
            zoom: markers.length > 1 ? 13 : 15,
            center,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true
        });

        markers.forEach((marker) => {
            if (!marker) return;
            const lat = Number(marker.lat);
            const lng = Number(marker.lng);
            if (!isFinite(lat) || !isFinite(lng)) return;

            const gmMarker = new google.maps.Marker({
                position: { lat, lng },
                map,
                title: marker.title || ""
            });

            const infoLines = [];
            if (marker.address) infoLines.push(escapeHtml(marker.address));
            if (marker.distance_m !== undefined && marker.distance_m !== null) {
                const distanceValue = Number(marker.distance_m);
                if (isFinite(distanceValue)) {
                    infoLines.push(`距離：約 ${distanceValue.toFixed(0)} 公尺`);
                }
            }
            if (Array.isArray(marker.items) && marker.items.length) {
                const itemsText = marker.items.map((item) => escapeHtml(item)).join("、");
                infoLines.push(`即期品：${itemsText}`);
            }

            if (infoLines.length) {
                const infoWindow = new google.maps.InfoWindow({
                    content: `<div style="font-size: 14px; line-height: 1.5;">${infoLines.join("<br>")}</div>`
                });
                gmMarker.addListener("click", () => infoWindow.open({ anchor: gmMarker, map, shouldFocus: false }));
            }
        });
    };

    ensureScript().then(() => {
        if (document.getElementById(containerId)) {
            initMap();
        }
    });
})();
</script>
"""
        )

        return template.substitute(
                container_id=container_id,
                center_json=center_json,
                markers_json=markers_json,
                api_key=GOOGLE_MAPS_API_KEY,
        )

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
                    row = [
                        f"7-11 {store_name}",
                        f"{dist_m:.1f} m",
                        "即期品 0 項",
                        "0",
                        dist_m,
                    ]
                    result_rows.append(row)
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
        if entry.get("lat") is None or entry.get("lng") is None:
            continue
        markers.append(
            {
                "title": entry.get("title"),
                "lat": entry.get("lat"),
                "lng": entry.get("lng"),
                "distance_m": entry.get("distance_m"),
                "address": entry.get("address"),
                "items": entry.get("items", []),
            }
        )

    markers.sort(key=lambda item: item.get("distance_m") if item.get("distance_m") is not None else float("inf"))

    map_html = _generate_map_html(lat, lon, markers)
    map_component = gr.update(value=map_html, visible=True) if map_html else hidden_map

    return result_rows, lat, lon, map_component

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

        map_html = gr.HTML(value="", visible=False, elem_id="store-map-container")

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
            outputs=[output_table, lat, lon, map_html],
            js="""
            (address, lat, lon, distance) => {
                function isZero(val) {
                    return !val || Number(val) === 0;
                }

                const nullTable = null;
                const nullMap = null;

                if (address && address.trim() !== "") {
                    // 有填地址，直接查詢，不抓 GPS
                    const currentLat = Number(lat);
                    const currentLon = Number(lon);
                    return [address, currentLat, currentLon, distance, nullTable, currentLat, currentLon, nullMap];
                }
                if (!isZero(lat) && !isZero(lon)) {
                    // 沒填地址但有座標，直接查詢
                    const currentLat = Number(lat);
                    const currentLon = Number(lon);
                    return [address, currentLat, currentLon, distance, nullTable, currentLat, currentLon, nullMap];
                }
                // 沒填地址且沒座標，抓 GPS
                return new Promise((resolve) => {
                    if (!navigator.geolocation) {
                        alert("您的瀏覽器不支援地理位置功能");
                        resolve([address, 0, 0, distance, nullTable, 0, 0, nullMap]);
                        return;
                    }
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const newLat = position.coords.latitude;
                            const newLon = position.coords.longitude;
                            resolve([address, newLat, newLon, distance, nullTable, newLat, newLon, nullMap]);
                        },
                        (error) => {
                            alert("無法取得位置：" + error.message);
                            resolve([address, 0, 0, distance, nullTable, 0, 0, nullMap]);
                        }
                    );
                });
            }
            """
        )

        demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)

if __name__ == "__main__":
    main()
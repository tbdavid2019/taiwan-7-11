import requests
import os
import html
from typing import Optional
import huggingface_hub

# Monkeypatch HfFolder to support older Gradio versions with newer huggingface_hub
if not hasattr(huggingface_hub, "HfFolder"):
    class HfFolder:
        @classmethod
        def get_token(cls):
            return huggingface_hub.get_token()
    huggingface_hub.HfFolder = HfFolder

import gradio as gr

# =============== 7-11 所需常數 ===============
# 請確認此處的 MID_V 是否有效，若過期請更新
MID_V = "W0_DiF4DlgU5OeQoRswrRcaaNHMWOL7K3ra3385ocZcv-bBOWySZvoUtH6j-7pjiccl0C5h30uRUNbJXsABCKMqiekSb7tdiBNdVq8Ro5jgk6sgvhZla5iV0H3-8dZfASc7AhEm85679LIK3hxN7Sam6D0LAnYK9Lb0DZhn7xeTeksB4IsBx4Msr_VI"
USER_AGENT_7_11 = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
API_7_11_BASE = "https://lovefood.openpoint.com.tw/LoveFood/api"

# =============== FamilyMart 所需常數 ===============
FAMILY_PROJECT_CODE = "202106302"  # 若有需要請自行調整
API_FAMILY = "https://stamp.family.com.tw/api/maps/MapProductInfo"

TAG_ICONS = {
    "麵": "🍜",
    "湯": "🥣",
    "飯": "🍚",
    "飯糰": "🍙",
}


def categorize_tags(text: str):
    if not text:
        return []
    tags = []
    if "飯糰" in text:
        tags.append("飯糰")
    if "麵" in text:
        tags.append("麵")
    if "湯" in text:
        tags.append("湯")
    if "飯" in text and "飯糰" not in text:
        tags.append("飯")
    return tags


def build_store_key(store_type: str, store_id: str):
    return f"{store_type}:{store_id}"


def build_favorite_choices(results, selected):
    stores = {}
    for r in results:
        key = r["store_key"]
        store_name = r.get("store_name") or ""
        label = f"{r['store_type']} {store_name}"
        dist = r.get("distance_m", 0)
        if key not in stores or dist < stores[key]["distance_m"]:
            stores[key] = {"label": label, "distance_m": dist}

    choices = [
        (v["label"], key)
        for key, v in sorted(stores.items(), key=lambda item: item[1]["distance_m"])
    ]
    selected_set = set(selected or [])
    selected_values = [key for key in (selected or []) if key in stores]
    if selected_set:
        selected_values = [key for key in (selected or []) if key in stores]
    return gr.update(choices=choices, value=selected_values)


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

def apply_filters(
    results,
    distance_km,
    store_filter,
    only_under_1km,
    only_in_stock,
    tag_include,
    tag_exclude,
    only_favorites,
    favorites,
):
    if not results:
        return "", _render_error("❌ 尚未搜尋，請先按下「自動定位並搜尋」")

    filtered = results
    if distance_km:
        max_distance = float(distance_km) * 1000
        filtered = [r for r in filtered if r["distance_m"] <= max_distance]

    if store_filter == "只看 7-11":
        filtered = [r for r in filtered if r["store_type"] == "7-11"]
    elif store_filter == "只看 全家":
        filtered = [r for r in filtered if r["store_type"] == "全家"]

    if only_under_1km:
        filtered = [r for r in filtered if r["distance_m"] <= 1000]
    if only_in_stock:
        filtered = [r for r in filtered if r["qty"] > 0]

    favorites_set = set(favorites or [])
    if only_favorites:
        filtered = [r for r in filtered if r.get("store_key") in favorites_set]

    include_set = set(tag_include or [])
    if include_set:
        filtered = [
            r for r in filtered if include_set.intersection(set(r.get("tags", [])))
        ]

    exclude_set = set(tag_exclude or [])
    if exclude_set:
        filtered = [
            r for r in filtered if not exclude_set.intersection(set(r.get("tags", [])))
        ]

    filtered.sort(key=lambda x: x["distance_m"])

    if not filtered:
        return "", _render_error("❌ 沒有符合篩選條件的結果")

    store_keys = {(r["store_type"], r["store_id"]) for r in filtered}
    total_qty = sum(r["qty"] for r in filtered if r["qty"] > 0)
    min_distance = min(r["distance_m"] for r in filtered) if filtered else None
    summary_html = _render_summary(len(store_keys), total_qty, min_distance, filtered)
    table_html = _render_table(filtered)

    return summary_html, table_html

def build_store_label(store_type, store_name):
    safe_name = html.escape(store_name)
    badge_class = "badge-711" if store_type == "7-11" else "badge-family"
    badge_text = "7-11" if store_type == "7-11" else "全家"
    return f"<span class='badge {badge_class}'>{badge_text}</span> {safe_name}"

def fetch_nearby_stores_data(lat, lon):
    results = []
    # ------------------ 7-11 ------------------
    try:
        token_711 = get_7_11_token()
        nearby_stores_711 = get_7_11_nearby_stores(token_711, lat, lon)
        for store in nearby_stores_711:
            dist_m = store.get("Distance", 999999)
            store_no = store.get("StoreNo")
            store_name = store.get("StoreName", "7-11 未提供店名")
            store_key = build_store_key("7-11", store_no)
            remaining_qty = store.get("RemainingQty", 0)
            if remaining_qty > 0:
                detail = get_7_11_store_detail(token_711, lat, lon, store_no)
                for cat in detail.get("CategoryStockItems", []):
                    cat_name = cat.get("Name", "")
                    for item in cat.get("ItemList", []):
                        item_name = item.get("ItemName", "")
                        item_qty = item.get("RemainingQty", 0)
                        tags = categorize_tags(f"{cat_name} {item_name}")
                        results.append({
                            "store_type": "7-11",
                            "store_id": store_no,
                            "store_key": store_key,
                            "store_name": store_name,
                            "store_label": build_store_label("7-11", store_name),
                            "distance_m": dist_m,
                            "item_label": f"{cat_name} - {item_name}",
                            "qty": item_qty,
                            "tags": tags,
                        })
            else:
                results.append({
                    "store_type": "7-11",
                    "store_id": store_no,
                    "store_key": store_key,
                    "store_name": store_name,
                    "store_label": build_store_label("7-11", store_name),
                    "distance_m": dist_m,
                    "item_label": "即期品 0 項",
                    "qty": 0,
                    "tags": [],
                })
    except Exception as e:
        print(f"❌ 取得 7-11 即期品時發生錯誤: {e}")

    # ------------------ FamilyMart ------------------
    try:
        nearby_stores_family = get_family_nearby_stores(lat, lon)
        for store in nearby_stores_family:
            dist_m = store.get("distance", 999999)
            store_name = store.get("name", "全家 未提供店名")
            info_list = store.get("info", [])
            store_id = (
                store.get("id")
                or store.get("storeid")
                or store.get("posCode")
                or store_name
            )
            store_key = build_store_key("全家", store_id)
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
                            tags = categorize_tags(
                                f"{big_cat_name} {subcat_name} {product_name}"
                            )
                            results.append({
                                "store_type": "全家",
                                "store_id": store_id,
                                "store_key": store_key,
                                "store_name": store_name,
                                "store_label": build_store_label("全家", store_name),
                                "distance_m": dist_m,
                                "item_label": f"{big_cat_name} - {subcat_name} - {product_name}",
                                "qty": qty,
                                "tags": tags,
                            })
            if not has_item:
                results.append({
                    "store_type": "全家",
                    "store_id": store_id,
                    "store_key": store_key,
                    "store_name": store_name,
                    "store_label": build_store_label("全家", store_name),
                    "distance_m": dist_m,
                    "item_label": "即期品 0 項",
                    "qty": 0,
                    "tags": [],
                })
    except Exception as e:
        print(f"❌ 取得全家 即期品時發生錯誤: {e}")

    return results

def find_nearest_store(
    address,
    lat,
    lon,
    distance_km,
    store_filter,
    only_under_1km,
    only_in_stock,
    tag_include,
    tag_exclude,
    only_favorites,
    favorites,
    input_mode,
):
    """
    distance_km: 選擇的公里數
    store_filter: '全部' / '只看 7-11' / '只看 全家'
    only_under_1km: bool，是否只顯示 1km 以內
    only_in_stock: bool，是否只顯示有庫存 > 0
    input_mode: '用地址' / '用 GPS'
    """
    print(
        f"🔍 收到查詢請求: mode={input_mode}, address={address}, lat={lat}, lon={lon}, "
        f"distance_km={distance_km}, filter={store_filter}, <1km={only_under_1km}, "
        f"onlyStock={only_in_stock}, tags_in={tag_include}, tags_out={tag_exclude}, onlyFav={only_favorites}"
    )

    # 若有填地址且 lat/lon 為 0，嘗試用 Google Geocoding API
    if address and address.strip() != "" and (lat == 0 or lon == 0):
        try:
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
                return "", _render_error("❌ 地址轉換失敗，請輸入正確地址"), lat, lon, [], gr.update()
        except Exception as e:
            print(f"❌ Google Geocoding 失敗: {e}")
            return "", _render_error("❌ 地址轉換失敗，請輸入正確地址"), lat, lon, [], gr.update()

    if lat == 0 or lon == 0:
        return "", _render_error("❌ 請輸入地址或提供 GPS 座標"), lat, lon, [], gr.update()

    results = fetch_nearby_stores_data(lat, lon)

    if not results:
        return "", _render_error("❌ 附近沒有即期食品 (在所選公里範圍內)"), lat, lon, [], gr.update()

    summary_html, table_html = apply_filters(
        results,
        distance_km,
        store_filter,
        only_under_1km,
        only_in_stock,
        tag_include,
        tag_exclude,
        only_favorites,
        favorites,
    )
    favorites_update = build_favorite_choices(results, favorites)

    return summary_html, table_html, lat, lon, results, favorites_update

def _render_error(msg: str):
    safe_msg = html.escape(msg)
    return f"<div class='callout callout-error'>{safe_msg}</div>"

def _render_summary(store_count: int, total_qty: int, min_distance: Optional[float], rows):
    nearest = f"{min_distance:.1f} m" if min_distance is not None else "—"
    tag_counts = {k: 0 for k in TAG_ICONS.keys()}
    for r in rows:
        for tag in r.get("tags", []):
            if tag in tag_counts:
                tag_counts[tag] += 1
    tags_html = "".join(
        f"<span class='tag-chip tag-{k}'>{TAG_ICONS.get(k, '')} {k} {v}</span>"
        for k, v in tag_counts.items()
        if v > 0
    )
    return f"""
    <div class='summary-bar'>
        <div><span class='summary-label'>門市</span><span class='summary-value'>{store_count}</span></div>
        <div><span class='summary-label'>可售商品數</span><span class='summary-value'>{total_qty}</span></div>
        <div><span class='summary-label'>最近距離</span><span class='summary-value'>{nearest}</span></div>
        <div><span class='summary-label'>品項分類</span><span class='summary-value tags'>{tags_html or '—'}</span></div>
    </div>
    """

def _render_table(rows):
    body_html = []
    for r in rows:
        qty_class = "qty-zero" if r["qty"] <= 0 else ""
        tags = r.get("tags", [])
        tag_class = ""
        if "麵" in tags:
            tag_class = "cat-noodle"
        elif "湯" in tags:
            tag_class = "cat-soup"
        elif "飯糰" in tags:
            tag_class = "cat-riceball"
        elif "飯" in tags:
            tag_class = "cat-rice"

        tag_html = "".join(
            f"<span class='tag-pill tag-{tag}'>{TAG_ICONS.get(tag, '')} {tag}</span>"
            for tag in tags
        )
        item_cell = f"{tag_html}{html.escape(r['item_label'])}"
        body_html.append(
            f"""
            <tr class='{qty_class} {tag_class}'>
                <td>{r["store_label"]}</td>
                <td>{r["distance_m"]:.1f} m</td>
                <td>{item_cell}</td>
                <td class='qty-cell'>{r["qty"]}</td>
            </tr>
            """
        )
    return f"""
    <div class='table-wrap'>
        <table class='results-table'>
            <thead>
                <tr>
                    <th>門市</th>
                    <th>距離 (m)</th>
                    <th>商品 / 即期食品</th>
                    <th>數量</th>
                </tr>
            </thead>
            <tbody>
                {''.join(body_html)}
            </tbody>
        </table>
    </div>
    """

# ========== Gradio 介面 ==========

def main():
    with gr.Blocks(
        title="便利商店即期食品查詢",
    ) as demo:
        gr.HTML(
            """
            <style>
            :root {
                --primary: #ff6b6b;
                --primary-weak: #ffe0e0;
            }
            #primary-search-btn button,
            #primary-search-btn button:where(*) {
                background: linear-gradient(135deg, #ff9ca0, #ff6b6b) !important;
                color: #fff !important;
                font-weight: 800 !important;
                padding: 16px 24px !important;
                font-size: 17px !important;
                border: none !important;
                border-radius: 14px !important;
                letter-spacing: 0.2px;
                box-shadow: 0 12px 28px -10px rgba(0,0,0,0.35) !important;
                transition: transform 0.12s ease, box-shadow 0.2s ease, filter 0.2s ease;
            }
            #primary-search-btn button:hover { filter: brightness(1.05); box-shadow: 0 14px 30px -10px rgba(0,0,0,0.38) !important; }
            #primary-search-btn button:active { transform: translateY(1px) scale(0.992); }
            .summary-bar {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                padding: 12px 14px;
                border: 1px solid #e5e5e5;
                border-radius: 10px;
                background: #fafafa;
            }
            .summary-label { display: block; color: #666; font-size: 12px; letter-spacing: 0.5px; }
            .summary-value { font-size: 18px; font-weight: 700; color: #111; }
            .table-wrap { max-height: 520px; overflow: auto; border: 1px solid #eee; border-radius: 10px; }
            .results-table { width: 100%; border-collapse: collapse; }
            .results-table thead th { position: sticky; top: 0; background: #f5f5f5; z-index: 1; padding: 8px 10px; text-align: left; }
            .results-table td { padding: 8px 10px; border-top: 1px solid #f1f1f1; }
            .results-table tbody tr:nth-child(even) { background: #fcfcfc; }
            .badge { display: inline-block; padding: 2px 6px; border-radius: 999px; font-size: 12px; color: #111; margin-right: 6px; }
            .badge-711 { background: #ffd9b0; }
            .badge-family { background: #d2f5e3; }
            .qty-zero { color: #888; }
            .qty-cell { text-align: right; font-variant-numeric: tabular-nums; }
            .callout { padding: 12px 14px; border-radius: 10px; border: 1px solid #f0b8b8; background: #fff3f3; color: #a12b2b; }
            .tag-chip { display: inline-block; padding: 2px 8px; border-radius: 999px; margin-right: 6px; font-size: 12px; }
            .tag-麵 { background: #ffe2e8; color: #b0233e; }
            .tag-湯 { background: #e8f1ff; color: #2b4ba1; }
            .tag-飯 { background: #fff1d6; color: #b46500; }
            .tag-飯糰 { background: #e8ffe8; color: #2b7a3d; }
            .cat-noodle td { background: #fff5f7; }
            .cat-soup td { background: #f4f8ff; }
            .cat-rice td { background: #fff9f0; }
            .cat-riceball td { background: #f4fff4; }
            .tag-pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 6px; border-radius: 8px; font-size: 12px; margin-right: 6px; }
            .tag-pill.tag-麵 { background: #ffe2e8; color: #b0233e; }
            .tag-pill.tag-湯 { background: #e8f1ff; color: #2b4ba1; }
            .tag-pill.tag-飯 { background: #fff1d6; color: #b46500; }
            .tag-pill.tag-飯糰 { background: #e8ffe8; color: #2b7a3d; }
            </style>
            """
        )
        gr.Markdown("## 台灣7-11 和 family全家便利商店「即期食品」 i珍食 友善食光 搜尋")
        gr.Markdown("""
        1. 按下「📍🔍 自動定位並搜尋」可自動取得目前位置並直接查詢附近即期品
        2. 也可手動輸入地址、緯度、經度與搜尋範圍後再按此按鈕
        3. 意見反應 https://david888.com 
        """)

        with gr.Row():
            auto_gps_search_button = gr.Button("📍🔍 自動定位並搜尋", elem_id="primary-search-btn")

        gr.Markdown("**輸入模式**：允許直接用 GPS（最快）或手動輸入地址 / 座標。")
        input_mode = gr.Radio(
            label="輸入方式",
            choices=["用 GPS", "用地址"],
            value="用 GPS",
            interactive=True,
        )

        with gr.Row():
            with gr.Column(visible=False) as address_group:
                address = gr.Textbox(
                    label="地址 (可留空)",
                    placeholder="建議直接用 GPS，不填也可查詢",
                )
            with gr.Column(visible=True) as gps_group:
                lat = gr.Number(label="GPS 緯度", value=0, elem_id="lat")
                lon = gr.Number(label="GPS 經度", value=0, elem_id="lon")

        with gr.Row():
            distance_slider = gr.Slider(
                label="搜尋範圍 (公里)",
                minimum=1,
                maximum=21,
                step=1,
                value=3,
                interactive=True,
                scale=2
            )
            store_filter = gr.Radio(
                label="門市品牌",
                choices=["全部", "只看 7-11", "只看 全家"],
                value="全部",
                interactive=True,
                scale=1
            )

        with gr.Row():
            only_under_1km = gr.Checkbox(label="只看 1 公里內", value=False)
            only_favorites = gr.Checkbox(label="只看愛店", value=False)
            only_in_stock = gr.Checkbox(label="只顯示有庫存", value=True)

        favorites_group = gr.CheckboxGroup(
            label="愛店清單",
            choices=[],
            value=[],
            interactive=True,
        )

        with gr.Row():
            tag_include = gr.CheckboxGroup(
                label="品項標籤（包含）",
                choices=list(TAG_ICONS.keys()),
                value=[],
                interactive=True,
            )
            tag_exclude = gr.CheckboxGroup(
                label="品項標籤（排除）",
                choices=list(TAG_ICONS.keys()),
                value=[],
                interactive=True,
            )

        summary_html = gr.HTML("")
        results_html = gr.HTML("")
        results_state = gr.State([])
        favorites_state = gr.State([])

        def on_mode_change(mode):
            return (
                gr.update(visible=mode == "用地址"),
                gr.update(visible=mode == "用 GPS"),
            )

        def on_favorites_change(
            favorites,
            results,
            distance_km,
            store_filter,
            only_under_1km,
            only_in_stock,
            tag_include,
            tag_exclude,
            only_favorites,
        ):
            summary_html, table_html = apply_filters(
                results,
                distance_km,
                store_filter,
                only_under_1km,
                only_in_stock,
                tag_include,
                tag_exclude,
                only_favorites,
                favorites,
            )
            return favorites, summary_html, table_html

        input_mode.change(
            fn=on_mode_change,
            inputs=input_mode,
            outputs=[address_group, gps_group],
        )

        demo.load(
            fn=lambda: ("", 0, 0, 3, "全部", False, True, "用 GPS", [], [], False, []),
            outputs=[
                address,
                lat,
                lon,
                distance_slider,
                store_filter,
                only_under_1km,
                only_in_stock,
                input_mode,
                tag_include,
                tag_exclude,
                only_favorites,
                favorites_state,
            ],
            js="""
            () => {
                const getNum = (key, fallback) => {
                    const raw = localStorage.getItem(key);
                    const n = raw === null ? fallback : Number(raw);
                    return isNaN(n) ? fallback : n;
                };
                const getList = (key) => {
                    try {
                        return JSON.parse(localStorage.getItem(key) || '[]');
                    } catch (e) {
                        return [];
                    }
                };
                return [
                    localStorage.getItem('addr') || '',
                    getNum('lat', 0),
                    getNum('lon', 0),
                    getNum('radius', 3),
                    localStorage.getItem('store_filter') || '全部',
                    localStorage.getItem('lt1k') === 'true',
                    localStorage.getItem('onlyStock') !== 'false',
                    localStorage.getItem('mode') || '用 GPS',
                    getList('tags_include'),
                    getList('tags_exclude'),
                    localStorage.getItem('onlyFavorites') === 'true',
                    getList('favorites'),
                ];
            }
            """,
        )

        demo.load(
            fn=on_mode_change,
            inputs=input_mode,
            outputs=[address_group, gps_group],
        )

        auto_gps_search_button.click(
            fn=find_nearest_store,
            inputs=[
                address,
                lat,
                lon,
                distance_slider,
                store_filter,
                only_under_1km,
                only_in_stock,
                tag_include,
                tag_exclude,
                only_favorites,
                favorites_state,
                input_mode,
            ],
            outputs=[summary_html, results_html, lat, lon, results_state, favorites_group],
            js="""
            (address, lat, lon, distance, storeFilter, under1k, onlyStock, tagInclude, tagExclude, onlyFavorites, favorites, mode) => {
                const distanceVal = Number(distance) || 0;
                const savePrefs = (addr, la, lo, dist) => {
                    localStorage.setItem('mode', mode);
                    localStorage.setItem('addr', addr || '');
                    localStorage.setItem('lat', la || 0);
                    localStorage.setItem('lon', lo || 0);
                    localStorage.setItem('radius', dist || 3);
                    localStorage.setItem('store_filter', storeFilter || '全部');
                    localStorage.setItem('lt1k', under1k ? 'true' : 'false');
                    localStorage.setItem('onlyStock', onlyStock ? 'true' : 'false');
                    localStorage.setItem('tags_include', JSON.stringify(tagInclude || []));
                    localStorage.setItem('tags_exclude', JSON.stringify(tagExclude || []));
                    localStorage.setItem('onlyFavorites', onlyFavorites ? 'true' : 'false');
                    localStorage.setItem('favorites', JSON.stringify(favorites || []));
                };
                const finalize = (newLat, newLon) => {
                    savePrefs(address, newLat, newLon, distanceVal);
                    return [
                        address,
                        newLat,
                        newLon,
                        distanceVal,
                        storeFilter,
                        under1k,
                        onlyStock,
                        tagInclude,
                        tagExclude,
                        onlyFavorites,
                        favorites,
                        mode,
                    ];
                };
                if (mode === "用地址" && address && address.trim() !== "") {
                    // 地址模式：交給後端 geocode，不沿用舊座標
                    return finalize(0, 0);
                }
                // GPS 模式：優先取即時座標，失敗才用現有欄位值
                return new Promise((resolve) => {
                    const fallback = () => finalize(Number(lat) || 0, Number(lon) || 0);
                    if (!navigator.geolocation) {
                        alert("您的瀏覽器不支援地理位置功能");
                        resolve(fallback());
                        return;
                    }
                    navigator.geolocation.getCurrentPosition(
                        (pos) => resolve(finalize(pos.coords.latitude, pos.coords.longitude)),
                        (error) => {
                            alert("無法取得位置：" + error.message);
                            resolve(fallback());
                        }
                    );
                });
            }
            """
        )

        # 篩選器變動時只套用快取結果（不重新查詢）
        for ctrl in (
            store_filter,
            only_under_1km,
            only_in_stock,
            distance_slider,
            tag_include,
            tag_exclude,
            only_favorites,
        ):
            ctrl.change(
                fn=apply_filters,
                inputs=[
                    results_state,
                    distance_slider,
                    store_filter,
                    only_under_1km,
                    only_in_stock,
                    tag_include,
                    tag_exclude,
                    only_favorites,
                    favorites_state,
                ],
                outputs=[summary_html, results_html],
            )

        favorites_group.change(
            fn=on_favorites_change,
            inputs=[
                favorites_group,
                results_state,
                distance_slider,
                store_filter,
                only_under_1km,
                only_in_stock,
                tag_include,
                tag_exclude,
                only_favorites,
            ],
            outputs=[favorites_state, summary_html, results_html],
            js="""
            (favorites, results, distance, storeFilter, under1k, onlyStock, tagInclude, tagExclude, onlyFavorites) => {
                localStorage.setItem('favorites', JSON.stringify(favorites || []));
                return [favorites, results, distance, storeFilter, under1k, onlyStock, tagInclude, tagExclude, onlyFavorites];
            }
            """,
        )

        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            debug=True,
            favicon_path="assets/favicon.svg",
        )

if __name__ == "__main__":
    main()

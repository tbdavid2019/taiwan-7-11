import requests
import json

# MID_V = "W0_DiF4DlgU5OeQoRswrRcaaNHMWOL7K3ra3385ocZcv-bBOWySZvoUtH6j-7pjiccl0C5h30uRUNbJXsABCKMqiekSb7tdiBNdVq8Ro5jgk6sgvhZla5iV0H3-8dZfASc7AhEm85679LIK3hxN7Sam6D0LAnYK9Lb0DZhn7xeTeksB4IsBx4Msr_VI"
MID_V = "W0_DiF4DlgU5OeQoRswrRcaaNHMWOL7K3ra3385ocZcv-bBOWySZvoUtH6j-7pjiccl0C5h30uRUNbJXsABCKMqiekSb7tdiBNdVq8Ro5jgk6sgvhZla5iV0H3-8dZfASc7AhEm85679LIK3hxN7Sam6D0LAnYK9Lb0DZhn7xeTeksB4IsBx4Msr_VI"
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
API_BASE = "https://lovefood.openpoint.com.tw/LoveFood/api"

print("=== 測試 7-11 Token API ===")
url = f"{API_BASE}/Auth/FrontendAuth/AccessToken?mid_v={MID_V}"
headers = {"user-agent": USER_AGENT}
resp = requests.post(url, headers=headers, data="", timeout=10)
print(f"Status Code: {resp.status_code}")
print(f"Response Text (前 500 字元): {resp.text[:500]}")

if resp.status_code == 200 and resp.text:
    try:
        js = resp.json()
        print(f"\nJSON 解析成功:")
        print(f"isSuccess: {js.get('isSuccess')}")
        if js.get('isSuccess'):
            token = js.get('element')
            print(f"Token (前 50 字元): {token[:50] if token else 'None'}...")
            
            print("\n=== 測試取得附近門市 ===")
            nearby_url = f"{API_BASE}/Search/FrontendStoreItemStock/GetNearbyStoreList?token={token}"
            payload = {
                "CurrentLocation": {"Latitude": 25.0330, "Longitude": 121.5654},
                "SearchLocation": {"Latitude": 25.0330, "Longitude": 121.5654}
            }
            resp2 = requests.post(
                nearby_url, 
                headers={"user-agent": USER_AGENT, "content-type": "application/json"}, 
                json=payload, 
                timeout=10
            )
            print(f"Status Code: {resp2.status_code}")
            
            if resp2.status_code == 200:
                js2 = resp2.json()
                print(f"isSuccess: {js2.get('isSuccess')}")
                element = js2.get('element', {})
                print(f"\n=== element 的類型和內容 ===")
                print(f"Type: {type(element)}")
                print(json.dumps(element, indent=2, ensure_ascii=False)[:2000])
                
                # 測試取得門市詳細資料
                store_list = element.get('StoreStockItemList', [])
                if store_list:
                    first_store = store_list[0]
                    store_no = first_store.get('StoreNo')
                    print(f"\n=== 測試取得門市詳細資料 (StoreNo: {store_no}) ===")
                    
                    detail_url = f"{API_BASE}/Search/FrontendStoreItemStock/GetStoreDetail?token={token}"
                    detail_payload = {
                        "CurrentLocation": {"Latitude": 25.0330, "Longitude": 121.5654},
                        "StoreNo": store_no
                    }
                    resp3 = requests.post(
                        detail_url,
                        headers={"user-agent": USER_AGENT, "content-type": "application/json"},
                        json=detail_payload,
                        timeout=10
                    )
                    print(f"Status Code: {resp3.status_code}")
                    if resp3.status_code == 200:
                        js3 = resp3.json()
                        print(f"isSuccess: {js3.get('isSuccess')}")
                        detail_data = js3.get('element', {})
                        print("\n=== 門市詳細資料 ===")
                        print(json.dumps(detail_data, indent=2, ensure_ascii=False))
        else:
            print(f"API 回應失敗: {js}")
    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
else:
    print("API 請求失敗或回應為空")

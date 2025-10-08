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
                "Latitude": 25.0330,
                "Longitude": 121.5654,
                "Distance": 3
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
                stores = js2.get('element', [])
                print(f"門市數量: {len(stores)}")
                
                if stores:
                    print("\n=== 第一個門市的完整資料 ===")
                    print(json.dumps(stores[0], indent=2, ensure_ascii=False))
        else:
            print(f"API 回應失敗: {js}")
    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
else:
    print("API 請求失敗或回應為空")

---
title: Taiwan 7 11
emoji: 🌖
colorFrom: indigo
colorTo: pink
sdk: gradio
sdk_version: 5.16.0
app_file: app.py
pinned: false
short_description: 便利商店的打折品
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference


---

# 便利商店即期食品查詢 (7-11 / FamilyMart)

本專案透過非官方 API，查詢台灣 7-11 與全家便利商店「即期食品」的資訊。

> **注意：**  
> 1. 需要有效的 `MID_V` 值才能查詢 7-11 資料。`MID_V` 可能會隨官方更新而失效，需自行抓包或取得授權。  
> 2. 全家 API 可能會變動或停止。  
> 3. 本專案僅供研究教學之用，請勿用於商業或非法目的。

## 功能
- 以 GPS 座標或地址（自動轉換為經緯度，支援 Google Geocoding API）搜尋附近的 7-11 / 全家門市。
- 可自訂搜尋範圍（3 / 5 / 7 / 13 / 21 公里）。
- 顯示每間門市的即期食品清單與剩餘數量。

## 使用方式
1. 安裝 Python 3.8+ 及套件：
   ```bash
   pip install gradio requests pandas geopy
   ```

2.	執行：

	```
	python app.py
	```

3.	瀏覽器打開 http://127.0.0.1:7860，即可看到查詢介面。


注意事項
- 此為個人練習與技術示範，非官方專案。
- 若出現「憑證過期」或「Token 失敗」等訊息，表示 MID_V 失效，需要更新。
- 地址查詢需設定 Google Geocoding API 金鑰於環境變數 `googlekey`（Huggingface Space Secrets）。

- For address search, set your Google Geocoding API key in the environment variable `googlekey` (Huggingface Space Secrets).

---
Convenience Store Expiring-Food Query (7-11 / FamilyMart)

This project uses unofficial APIs to query expiring-food items in Taiwan’s 7-11 and FamilyMart convenience stores.

Note:
		1.	A valid MID_V is required to access 7-11’s data. MID_V may expire as the official app updates. You must capture or obtain it by yourself.
	2.	FamilyMart’s API might change or be discontinued without notice.
	3.	This project is for educational and research purposes only. Please do not use it for commercial or illegal purposes.

Features
	•	Search nearby 7-11 / FamilyMart stores by GPS coordinates or address (auto geocoding via Google API).
	•	Customizable search radius (3 / 5 / 7 / 13 / 21 km).
	•	Display each store’s expiring-food items and remaining quantity.

Usage
1.	Install Python 3.8+ and dependencies:
```
pip install gradio requests pandas
```

2.	Run:
```
python app.py
```

3.	Open http://127.0.0.1:7860 in your browser to see the interface.


---


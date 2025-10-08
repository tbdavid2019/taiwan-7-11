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

本專案透過非官方 API，查詢台灣 7-11 與全家便利商店「即期食品」的資訊，並在 Google Maps 上呈現搜尋結果。

> **注意：**  
> 1. 需要有效的 `MID_V` 值才能查詢 7-11 資料。`MID_V` 可能會隨官方更新而失效，需自行抓包或取得授權。  
> 2. 全家 API 可能會變動或停止。  
> 3. 本專案僅供研究教學之用，請勿用於商業或非法目的。

## 功能

- 以 GPS 座標或地址（自動轉換為經緯度，支援 Google Geocoding API）搜尋附近的 7-11 / 全家門市。
- 可自訂搜尋範圍（3 / 5 / 7 / 13 / 21 公里）。
- 顯示每間門市的即期食品清單與剩餘數量。
- 搜尋完成後，於按鈕下方顯示 Google Maps 標記，呈現已取得的門市位置（需提供 API key）。

## 使用方式

1. 安裝 Python 3.8+ 及套件：

   ```bash
   pip install -r requirements.txt
   ```

2. 建立環境變數：

   - 複製專案根目錄的 `.env` 檔案，填入 `GOOGLE_MAPS_API_KEY=<你的金鑰>`。
   - 相同的金鑰會用於 Google Maps 展示與地址地理編碼。

3. 執行：

   ```bash
   python app.py
   ```

4. 瀏覽器打開 [http://127.0.0.1:7860](http://127.0.0.1:7860)，即可看到查詢介面。

## 注意事項

- 此為個人練習與技術示範，非官方專案。
- 若出現「憑證過期」或「Token 失敗」等訊息，表示 MID_V 失效，需要更新。
- 地址查詢與地圖展示均需設定 Google Maps API 金鑰於 `.env`（欄位 `GOOGLE_MAPS_API_KEY`）或部署環境變數中。

---

## Convenience Store Expiring-Food Query (7-11 / FamilyMart)

This project uses unofficial APIs to query expiring-food items in Taiwan’s 7-11 and FamilyMart convenience stores.

### Note

- A valid MID_V is required to access 7-11’s data. MID_V may expire as the official app updates. You must capture or obtain it by yourself.
- FamilyMart’s API might change or be discontinued without notice.
- This project is for educational and research purposes only. Please do not use it for commercial or illegal purposes.

### Features

- Search nearby 7-11 / FamilyMart stores by GPS coordinates or address (auto geocoding via Google API).
- Customizable search radius (3 / 5 / 7 / 13 / 21 km).
- Display each store’s expiring-food items and remaining quantity.
- Show store markers on Google Maps after each search (requires API key).

### Usage

1. Install Python 3.8+ and dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:

   - Copy the `.env` file in the project root and set `GOOGLE_MAPS_API_KEY=<your_key>`.
   - The same key powers both Google Maps rendering and address geocoding.

3. Run:

   ```bash
   python app.py
   ```

4. Open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser to access the interface.

---


# Hugging Face Space 設定指南

## 設定 Google Maps API Key

在 Hugging Face Space 上部署時，需要透過 Space Settings 設定環境變數：

### 步驟

1. 前往你的 Space 頁面（例如：`https://huggingface.co/spaces/tbdavid2019/taiwan-7-11`）

2. 點擊頁面上方的 **Settings** 標籤

3. 找到 **Repository secrets** 或 **Variables and secrets** 區段

4. 點擊 **New secret** 按鈕

5. 填入以下資訊：
   - **Name**: `GOOGLE_MAPS_API_KEY`
   - **Value**: 你的 Google Maps API Key（例如：`AIzaSyBSuobLp_r96bWpAB4gf48n4pC9BseITpo`）

6. 點擊 **Add secret** 儲存

7. 重新啟動 Space（可能需要點擊 Factory reboot 或等待自動重啟）

### 檢查是否成功

部署後，檢查 Space 的 Logs（點擊右上角的 **Logs** 按鈕）：

- 如果看到 `⚠️ 警告：未設定 GOOGLE_MAPS_API_KEY，地圖無法顯示`，表示環境變數尚未生效
- 如果看到 `✅ 使用 Google Maps API Key: AIzaSyBSu...`，表示已正確載入

### 瀏覽器 Console 檢查

1. 在 Space 頁面按 F12 打開瀏覽器開發者工具
2. 切換到 **Console** 標籤
3. 點擊「📍🔍 自動定位並搜尋」按鈕
4. 檢查 console 訊息：
   - `✅ Google Maps API 載入成功` - API 正常
   - `❌ Google Maps API 載入失敗` - API Key 可能無效或有限制
   - `✅ 地圖繪製完成！已放置 X 個標記` - 成功顯示地圖

### 常見問題

#### 1. 地圖顯示空白灰色區域

**原因**：Google Maps API Key 未設定或無效

**解決方法**：
- 確認已在 Space Settings 新增 `GOOGLE_MAPS_API_KEY` secret
- 確認 API Key 已啟用 Maps JavaScript API
- 檢查 API Key 是否有網域限制（Hugging Face Space 使用 `*.hf.space` 網域）

#### 2. API Key 網域限制設定

在 Google Cloud Console 的 API Key 設定中：

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 選擇專案 → API 和服務 → 憑證
3. 找到你的 API Key 並點擊編輯
4. 在「應用程式限制」中選擇「HTTP 參照網址」
5. 新增以下網址：
   ```
   *.hf.space/*
   *.huggingface.co/*
   ```
6. 在「API 限制」中選擇「限制金鑰」並勾選：
   - Maps JavaScript API
   - Geocoding API

#### 3. 門市沒有座標資料

如果 console 顯示 `⚠️ 標記 X 座標無效`，表示某些門市的 API 回應中缺少經緯度資料。這是正常現象，程式會自動跳過無效標記。

## 本地測試

本地開發時，直接編輯 `.env` 檔案：

```bash
GOOGLE_MAPS_API_KEY=你的API金鑰
```

然後執行：

```bash
python app.py
```

---

**提示**：如果修改後仍無法顯示，可能需要清除瀏覽器快取或使用無痕模式重新載入頁面。

from fastapi import FastAPI, HTTPException, Query # 導入 FastAPI 核心類，用於創建 Web API 應用。
                                                  # 導入 HTTPException，用於在 API 請求處理中拋出 HTTP 錯誤。
                                                  # 導入 Query，用於在路由函數中定義查詢參數。
from fastapi.staticfiles import StaticFiles # 導入 StaticFiles，用於在 FastAPI 應用中服務靜態文件（如 HTML、CSS、JavaScript）。
from pydantic import BaseModel # 導入 Pydantic 的 BaseModel，用於定義數據模型，實現請求體驗證和回應序列化。
import os # 導入 os 模組，用於與作業系統進行交互，例如讀取環境變數和處理文件路徑。
import requests # 導入 requests 庫，這是一個流行的 Python 庫，用於發送 HTTP 請求（例如到 Apify 或 Google Places API）。
import time # 導入 time 模組，提供時間相關的功能，例如 `time.sleep()` 用於暫停程式執行。
import json # 導入 json 模組，用於處理 JSON 格式的數據。
from dotenv import load_dotenv # 導入 load_dotenv，用於從 `.env` 檔案載入環境變數。

# --- 1. 初始化與設定 ---
load_dotenv() # 調用 load_dotenv()，自動查找並載入專案根目錄下的 `.env` 檔案，將其中的變數載入到 os.environ 中。
              # 這使得應用程式可以安全地讀取 API 金鑰、資料庫連接字串等敏感資訊。

app = FastAPI( # 創建一個 FastAPI 應用程式實例。
    title="Project MineSweeper - 美食地標防雷系統 API", # 設定在自動生成的 API 文件（如 Swagger UI）中顯示的應用標題。
    description="輸入一個地點名稱，獲取其量化的踩雷分數與分析報告。", # 設定 API 文件的簡短描述。
    version="2.0.0" # 設定 API 的版本號。此處版本升級，代表已加入 AI 功能。
)

# --- 2. 匯入與初始化核心模組 ---
# 將 import 放在這裡，確保在 app 建立後再引入。這有助於避免潛在的循環依賴問題，並確保模組在應用程式環境初始化後才被載入。
from app.services import FeatureEngineer # 從 `app/services.py` 導入 `FeatureEngineer` 類，用於特徵工程。
from app.models import LandmineScorer # 從 `app/models.py` 導入 `LandmineScorer` 類，用於計算踩雷分數。
from app.database import places_collection, reviews_collection # 從 `app/database.py` 導入 `places_collection` 和 `reviews_collection`，它們是 MongoDB (Cosmos DB) 的集合實例。

engineer = FeatureEngineer() # 初始化 `FeatureEngineer` 類的一個實例。
scorer = LandmineScorer() # 初始化 `LandmineScorer` 類的一個實例。

# --- 3. 讀取環境變數 ---
APIFY_API_TOKEN = os.getenv("THIRD_PARTY_API_KEY") # 從環境變數中獲取 Apify API 的金鑰。
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") # 從環境變數中獲取 Google Places API 的金鑰。
BASE_API_URL = "https://api.apify.com/v2" # 定義 Apify API 的基礎 URL。

# --- 4. 輔助函式：Apify 數據抓取 ---
def _run_apify_actor_and_get_data(place_id: str) -> dict | None:
    """
    (內部輔助函式) 根據 Google Place ID 執行 Apify Actor 抓取數據並直接回傳結果。
    這個函數會啟動一個 Apify 任務，輪詢其狀態，並在任務成功後下載數據。
    Args:
        place_id (str): Google 地點的唯一識別符。
    Returns:
        dict | None: 抓取到的地點數據字典（包含評論），如果 Apify 任務失敗則為 None。
    Raises:
        ValueError: 如果 APIFY_API_TOKEN 未設定。
        RuntimeError: 如果 Apify 任務未能成功完成。
        requests.exceptions.RequestException: 如果與 Apify API 的 HTTP 請求失敗。
    """
    actor_id = "compass~crawler-google-places" # 定義要使用的 Apify Actor ID，這是 Google Places 爬蟲的 ID。
    if not APIFY_API_TOKEN: # 檢查 Apify API 金鑰是否已設置。
        raise ValueError("APIFY_API_TOKEN 未設定，請檢查環境變數。") # 如果金鑰未設置，則拋出 ValueError。

    Maps_url = f"https://www.google.com/maps/search/?api=1&query=a&query_place_id={place_id}" # 構建 Google Maps 的 URL 格式，Apify Actor 需要這個格式來識別地點。

    actor_input = { # 定義傳遞給 Apify Actor 的輸入參數。
        "startUrls": [{"url": Maps_url}], # 指定 Actor 開始爬取的 URL 列表。
        "maxReviews": 50, # 設定 Actor 抓取的最大評論數量。此處為了測試和節省額度，設為較低值。
        "language": "zh-TW" # 指定抓取評論的語言為繁體中文。
    }
    
    print(f"INFO: 啟動 Apify Actor 抓取 Place ID '{place_id}' 的數據...") # 打印日誌訊息，指示 Apify 任務即將啟動。
    run_response = requests.post(f"{BASE_API_URL}/acts/{actor_id}/runs?token={APIFY_API_TOKEN}", json=actor_input) # 向 Apify API 發送 POST 請求以啟動 Actor 任務。
    run_response.raise_for_status() # 檢查 HTTP 回應狀態碼。如果請求失敗（4xx 或 5xx），則拋出異常。
    run_data = run_response.json()['data'] # 解析回應的 JSON 數據，提取任務運行相關資訊。
    run_id, dataset_id = run_data['id'], run_data['defaultDatasetId'] # 提取運行 ID 和任務生成數據集的 ID。
    print(f"INFO: 任務已啟動，Run ID: {run_id}") # 打印任務的運行 ID。

    while True: # 進入循環，定期輪詢 Apify 任務的狀態。
        status_response = requests.get(f"{BASE_API_URL}/acts/{actor_id}/runs/{run_id}?token={APIFY_API_TOKEN}") # 發送 GET 請求查詢任務狀態。
        status_response.raise_for_status() # 檢查狀態查詢請求的回應是否成功。
        status = status_response.json()['data']['status'] # 從回應中提取任務的當前狀態字串。
        print(f"INFO: 當前任務狀態: {status}") # 打印當前任務狀態。
        if status in ["SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"]: # 如果任務狀態是最終狀態（成功、失敗、超時、中止），則跳出循環。
            break
        time.sleep(15) # 暫停 15 秒，避免頻繁請求 Apify API。

    if status == "SUCCEEDED": # 如果任務成功完成。
        print("INFO: 任務成功！下載數據...") # 打印成功訊息。
        dataset_response = requests.get(f"{BASE_API_URL}/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}") # 從 Apify 數據集下載抓取到的數據。
        dataset_response.raise_for_status() # 檢查數據下載請求的回應是否成功。
        return dataset_response.json() # 回傳 JSON 格式的數據。
    else: # 如果任務未能成功完成。
        raise RuntimeError(f"Apify 任務未能成功完成，最終狀態為: {status}") # 拋出運行時錯誤，指示任務失敗原因。

# --- 5. API 路由定義 ---
# Pydantic 模型：定義 /search 端點回應的單個地點候選對象結構。
class PlaceCandidate(BaseModel):
    name: str # 地點的名稱。
    address: str # 地點的格式化地址。
    place_id: str # 地點的 Google Place ID。

# Pydantic 模型：定義 /analyze 端點請求的輸入結構。
class AnalyzeRequest(BaseModel):
    place_id: str # 請求體中必須包含的地點 ID。

# Pydantic 模型：定義 /analyze 端點回應的輸出結構。
class AnalyzeResponse(BaseModel):
    place_name: str # 分析地點的名稱。
    landmine_score: float # 計算出的踩雷分數。
    risk_level: str # 根據踩雷分數判斷的風險等級（例如 "低度風險", "中度風險", "高度風險"）。
    summary: str # 踩雷分析的動態摘要。
    key_negative_keywords: list[str] # 從評論中摘錄的關鍵負面片語列表。
    positive_points: list[str] # 從評論中摘錄的正面提及片語列表。
    details: dict # 包含更多詳細數據（如歷史平均分、近期平均分、評論總數、趨勢分數）的字典。

# /search 端點：用於模糊搜尋地點並回傳候選列表。
@app.get("/search", response_model=list[PlaceCandidate]) # 定義一個 GET 請求的 API 端點，路徑為 "/search"。
                                                            # `response_model` 指定了這個端點將回傳 `PlaceCandidate` 對象的列表。
async def search_places(query: str = Query(..., min_length=2, description="模糊搜尋關鍵字")):
    """
    模糊搜尋 Google Places API 以獲取地點候選列表。
    `query`: 用戶輸入的搜尋關鍵字，必須至少有 2 個字元。
    """
    if not GOOGLE_PLACES_API_KEY: # 檢查 Google Places API 金鑰是否已設置。
        raise HTTPException(status_code=503, detail="Google Places API 金鑰未設定。") # 如果未設置，則拋出 503 服務不可用錯誤。

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json" # Google Places API 的 `findplacefromtext` 端點 URL。
    params = { # 定義發送給 Google Places API 的查詢參數。
        "input": query, # 搜尋的輸入文字。
        "inputtype": "textquery", # 輸入類型為文字查詢。
        "fields": "place_id,formatted_address,name", # 請求回傳的數據欄位。
        "key": GOOGLE_PLACES_API_KEY, # Google Places API 金鑰。
        "language": "zh-TW" # 指定搜尋結果的語言為繁體中文。
    }
    response = requests.get(url, params=params) # 發送 GET 請求到 Google Places API。
    response.raise_for_status() # 檢查 HTTP 回應狀態碼。如果請求失敗，則拋出異常。
    data = response.json() # 解析回應的 JSON 數據。
    
    # 遍歷回應數據中的 'candidates' 列表，為每個候選地點創建一個 `PlaceCandidate` 對象。
    # `res.get("name")` 安全地獲取字段值，避免鍵錯誤。
    return [
        PlaceCandidate(name=res.get("name"), address=res.get("formatted_address"), place_id=res.get("place_id"))
        for res in data.get("candidates", []) # 從 `data` 字典中獲取 'candidates' 列表，如果不存在則默認為空列表。
    ]

# /analyze 端點：用於分析指定地點的踩雷分數。
@app.post("/analyze", response_model=AnalyzeResponse) # 定義一個 POST 請求的 API 端點，路徑為 "/analyze"。
                                                         # 接收 `AnalyzeRequest` 作為請求體，回傳 `AnalyzeResponse`。
async def analyze_place(request: AnalyzeRequest):
    """
    根據提供的地點 ID 分析其踩雷分數和報告。
    會優先從資料庫快取中查找，若無則啟動 Apify 抓取數據。
    `request`: 包含 `place_id` 的請求體。
    """
    place_id = request.place_id # 從請求體中獲取 `place_id`。
    print(f"INFO: 收到新的分析請求: Place ID = {place_id}") # 打印日誌訊息，指示收到新的分析請求。
    
    if places_collection is None or reviews_collection is None: # 檢查資料庫集合是否已成功初始化（即資料庫連線是否成功）。
        raise HTTPException(status_code=503, detail="資料庫服務不可用。") # 如果資料庫服務不可用，則拋出 503 錯誤。

    place_data = places_collection.find_one({"_id": place_id}) # 嘗試從 `places_collection` 中查找是否有該 `place_id` 的快取數據。
    
    if place_data: # 如果在資料庫中找到快取數據。
        print(f"INFO: 在 Cosmos DB 中找到快取: {place_id}") # 打印日誌訊息，指示找到快取。
        reviews_list = list(reviews_collection.find({"place_id": place_id})) # 從 `reviews_collection` 中查找與該 `place_id` 相關的所有評論。
        place_info = place_data # 使用從資料庫獲取的地點數據作為 `place_info`。
        place_info["reviews"] = reviews_list # 將查找到的評論列表添加到 `place_info` 字典中。
    else: # 如果資料庫中沒有快取數據。
        print(f"INFO: Cosmos DB 中無快取，正在啟動 Apify 即時數據抓取...") # 打印日誌訊息，指示將啟動即時數據抓取。
        try:
            apify_data = _run_apify_actor_and_get_data(place_id) # 調用內部輔助函數 `_run_apify_actor_and_get_data` 啟動 Apify 任務抓取數據。
            if not apify_data: raise ValueError("Apify 未回傳任何數據。") # 如果 Apify 未回傳任何數據，則拋出錯誤。
            place_info = apify_data[0] # Apify 回傳的通常是一個列表，取第一個元素作為主要的地點資訊。
            reviews_list = place_info.get("reviews", []) # 從 Apify 獲取的地點資訊中提取評論列表。

            # 將抓取到的地點資訊存入資料庫以供快取。
            place_to_insert = place_info.copy() # 複製 `place_info` 以避免修改原始數據。
            place_to_insert.pop("reviews", None) # 移除 'reviews' 字段，因為評論將被單獨儲存。
            place_to_insert["_id"] = place_id # 將 `_id` 設置為 `place_id`，這是 MongoDB 的主鍵。
            places_collection.insert_one(place_to_insert) # 將地點資訊插入到 `places_collection` 中。

            if reviews_list: # 如果有評論數據。
                for review in reviews_list: # 遍歷每一條評論。
                    review["place_id"] = place_id # 為每條評論添加 `place_id` 字段，以便關聯。
                reviews_collection.insert_many(reviews_list) # 將評論列表批量插入到 `reviews_collection` 中。
            print("INFO: 新資料已成功存入 Azure Cosmos DB。") # 打印日誌訊息，指示新資料已成功存入資料庫。
        except Exception as e: # 捕獲在 Apify 數據抓取或資料庫寫入過程中可能發生的任何異常。
            raise HTTPException(status_code=500, detail=f"Apify 數據抓取或資料庫寫入失敗: {e}") # 拋出 500 內部伺服器錯誤。

    # 調用 FeatureEngineer 的 run 方法，執行特徵工程。
    # 它會回傳三個值：處理後的 DataFrame、趨勢資訊字典、關鍵片語字典。
    processed_df, trend_info, key_phrases = engineer.run(place_info)
    if processed_df is None: # 如果 `FeatureEngineer.run` 回傳 None (表示處理失敗，例如缺少必要數據)。
        raise HTTPException(status_code=500, detail="特徵工程執行失敗。") # 拋出 500 內部伺服器錯誤。

    # 調用 LandmineScorer 的 calculate_score 方法，計算最終踩雷分數和摘要。
    # 它會回傳兩個值：最終分數和摘要文字。
    score, summary = scorer.calculate_score(processed_df, trend_info)
    
    risk_level = "低度風險" # 預設風險等級為「低度風險」。
    if score > 70: risk_level = "高度風險" # 如果分數大於 70，則設定為「高度風險」。
    elif score > 40: risk_level = "中度風險" # 如果分數大於 40，則設定為「中度風險」。
    
    place_name = place_info.get("title", place_id) # 從 `place_info` 中獲取地點的標題名稱，如果沒有則使用 `place_id`。
    print(f"INFO: 分析完成。地點: {place_name}, 踩雷分數: {score:.2f}") # 打印日誌訊息，顯示分析結果。
    
    # 構建 `AnalyzeResponse` 對象並回傳。
    return AnalyzeResponse(
        place_name=place_name, # 地點名稱。
        landmine_score=round(score, 2), # 踩雷分數，四捨五入到小數點後兩位。
        risk_level=risk_level, # 風險等級。
        summary=summary, # 動態摘要。
        key_negative_keywords=key_phrases.get("key_negative_keywords", []), # 關鍵負面片語列表，如果沒有則為空列表。
        positive_points=key_phrases.get("positive_points", []), # 正面提及片語列表，如果沒有則為空列表。
        details=trend_info # 詳細數據（趨勢資訊）。
    )

# --- 6. 掛載前端靜態檔案 (放在最後，最穩定的方式) ---
# 構建靜態檔案目錄的絕對路徑。`os.path.dirname(__file__)` 獲取當前檔案的目錄，`'..'` 向上退一層（到專案根目錄），然後進入 'static' 資料夾。
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
# 將根路徑 "/" 掛載到靜態檔案服務。
# 當有請求發往應用程式根路徑且無法匹配其他 API 路由時，FastAPI 會從 `static_dir` 指定的目錄中查找對應的靜態檔案。
# `html=True` 表示如果請求的是目錄，會自動嘗試查找並提供 `index.html`。
# `name="static"` 是給這個靜態檔案掛載點一個名稱，在 FastAPI 內部用於路由管理。
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
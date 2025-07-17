import os # 導入 os 模組，用於與作業系統進行交互，例如讀取環境變數和處理文件路徑。
import requests # 導入 requests 庫，這是一個流行的 Python 庫，用於發送 HTTP 請求（例如 GET, POST 等）。
import time # 導入 time 模組，提供時間相關的功能，例如 `time.sleep()` 用於暫停程式執行。
import json # 導入 json 模組，用於處理 JSON (JavaScript Object Notation) 格式的數據，包括編碼和解碼。
from dotenv import load_dotenv # 從 dotenv 庫導入 load_dotenv 函數。這個函數用於從 `.env` 檔案中載入環境變數到程式的執行環境中。

# --- 1. 初始化與環境設定 ---
# 載入 .env 檔案中定義的環境變數
load_dotenv() # 調用 load_dotenv() 會自動查找並讀取當前或父目錄下的 `.env` 檔案，
              # 將其中定義的鍵值對載入為環境變數。這樣可以安全地管理敏感資訊，而不將它們硬編碼到程式碼中。

# 從環境變數中安全地讀取您的 Apify API Token
# 我們在 Day 1 已約定將第三方金鑰存在這個變數名中
APIFY_API_TOKEN = os.getenv("THIRD_PARTY_API_KEY") # 使用 os.getenv() 函數從環境變數中獲取名為 "THIRD_PARTY_API_KEY" 的值。
                                                  # 如果該環境變數不存在，則返回 None。

# Apify 官方 Google Maps Scraper Actor 的唯一識別符
# 這能確保我們總是使用正確的工具
ACTOR_ID = "compass~crawler-google-places" # 定義 Apify 平台上 Google Maps Sc抓取器 Actor 的固定 ID。
                                          # 這是 Apify 服務中特定自動化任務的唯一標識。

# Apify API 的基礎 URL
BASE_API_URL = "https://api.apify.com/v2" # 定義 Apify API 的基礎 URL。所有 Apify API 請求都將以此 URL 為前綴。


def run_and_get_reviews(search_term: str, output_path: str, max_reviews: int = 50):
    """
    執行 Apify Actor 抓取指定地點的 Google Maps 評論，並在完成後下載結果。

    Args:
        search_term (str): 要在 Google Maps 上搜尋的關鍵字，例如 "基隆廟口夜市"。
                           這是 Actor 任務的輸入，用於指定要抓取評論的地點。
        output_path (str): 下載的 JSON 數據要儲存的本地路徑。
                           指定抓取到的評論數據在本地文件系統中的保存位置。
        max_reviews (int): 希望抓取的最大評論數量。默認為 50 條。
                           這個參數限制了 Actor 嘗試抓取的評論條數，有助於控制成本和執行時間。
    """

    if not APIFY_API_TOKEN: # 檢查 APIFY_API_TOKEN 是否為空或 None。
        print("錯誤：找不到 API Token。請檢查您的 .env 檔案是否已正確設定 THIRD_PARTY_API_KEY。") # 如果 Token 不存在，則打印錯誤訊息。
        return # 終止函數的執行，因為沒有 API Token 無法進行後續操作。

    # --- 2. 準備並啟動 Actor 任務 ---
    # 這是要傳遞給 Apify Actor 的輸入參數，告訴它要搜尋什麼、抓多少筆
    actor_input = { # 定義一個字典，作為啟動 Apify Actor 任務的輸入配置。
        "searchStringsArray": [search_term], # Actor 將根據此列表中的搜尋字串在 Google Maps 上進行搜尋。
        "maxReviews": max_reviews, # 傳遞最大評論數量參數。
        "language": "zh-TW" # 指定抓取評論的語言為繁體中文，確保獲取相關語言的評論。
    }

    print(f"INFO: 準備啟動 Apify Actor 來抓取 '{search_term}' 的數據...") # 打印提示訊息，告知使用者任務即將開始。

    try:
        # 透過 HTTP POST 請求啟動 Actor 任務
        run_response = requests.post( # 使用 requests.post 發送 POST 請求。
            f"{BASE_API_URL}/acts/{ACTOR_ID}/runs?token={APIFY_API_TOKEN}", # 請求的 URL，包含 Apify API 基礎 URL、Actor ID 和 API Token。
            json=actor_input # 將 `actor_input` 字典作為 JSON 格式的請求體發送。requests 庫會自動處理 JSON 編碼。
        )
        run_response.raise_for_status() # 檢查 HTTP 回應的狀態碼。如果狀態碼是 4xx (客戶端錯誤) 或 5xx (伺服器錯誤)，則會拋出 `requests.exceptions.HTTPError`。
        run_data = run_response.json() # 將 HTTP 回應的 JSON 內容解析為 Python 字典。
        
        # 從回應中獲取這次任務的 ID 和預設數據集的 ID
        run_id = run_data['data']['id'] # 從回應數據中提取本次 Actor 任務的唯一運行 ID。
        dataset_id = run_data['data']['defaultDatasetId'] # 從回應數據中提取與本次任務相關聯的預設數據集 ID。
        print(f"INFO: 任務已成功啟動，Run ID: {run_id}") # 打印成功啟動任務的訊息和運行 ID。

    except requests.exceptions.RequestException as e: # 捕獲任何 `requests` 庫可能拋出的異常（包括連接錯誤、超時、HTTP 錯誤等）。
        print(f"錯誤：啟動 Apify Actor 失敗。錯誤訊息: {e}") # 打印啟動失敗的錯誤訊息。
        return # 失敗則返回，不繼續執行後續步驟。

    # --- 3. 輪詢任務狀態，直到完成 ---
    while True: # 進入一個無限循環，用於定期查詢 Actor 任務的狀態，直到任務完成。
        try:
            print(f"INFO: 正在查詢任務 {run_id} 的狀態...") # 打印提示訊息，告知正在查詢任務狀態。
            status_response = requests.get(f"{BASE_API_URL}/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_TOKEN}") # 發送 GET 請求查詢特定運行 ID 的任務狀態。
            status_response.raise_for_status() # 檢查狀態查詢請求的回應是否成功。
            status_data = status_response.json() # 解析狀態查詢的回應 JSON。
            status = status_data['data']['status'] # 從回應數據中提取任務的當前狀態字串（例如 "RUNNING", "SUCCEEDED"）。
            
            print(f"INFO: 當前任務狀態: {status}") # 打印當前任務的狀態。

            # 當任務狀態為最終狀態 (成功、失敗、中止) 時，跳出迴圈
            if status in ["SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"]: # 檢查當前狀態是否為任務的最終狀態。
                break # 如果是最終狀態，則跳出 while 循環。
            
            # 等待 15 秒後再進行下一次查詢，避免過於頻繁地請求 API
            time.sleep(15) # 暫停程式執行 15 秒，以避免頻繁請求 Apify API 導致達到速率限制或增加不必要的負載。

        except requests.exceptions.RequestException as e: # 捕獲查詢任務狀態時可能發生的請求異常。
            print(f"錯誤：查詢任務狀態失敗。錯誤訊息: {e}") # 打印錯誤訊息。
            return # 失敗則返回。

    # --- 4. 根據最終狀態下載結果 ---
    if status == "SUCCEEDED": # 如果任務的最終狀態是 "SUCCEEDED" (成功完成)
        print("INFO: 任務成功完成！正在下載數據集...") # 打印成功訊息。
        try:
            # 從數據集端點獲取所有項目
            dataset_response = requests.get(f"{BASE_API_URL}/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}") # 發送 GET 請求從 Apify 數據集下載所有項目。
            dataset_response.raise_for_status() # 檢查數據集下載請求的回應是否成功。
            reviews_data = dataset_response.json() # 解析下載到的 JSON 數據，這將是評論數據的列表。
            
            # 確保輸出目錄存在。如果目錄不存在，則創建它。`exist_ok=True` 表示如果目錄已經存在，則不會拋出錯誤。
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 將獲取的數據以美觀的格式寫入本地 JSON 檔案
            with open(output_path, 'w', encoding='utf-8') as f: # 以寫入模式 ('w') 打開指定的輸出文件，使用 UTF-8 編碼。
                json.dump(reviews_data, f, ensure_ascii=False, indent=2) # 將 `reviews_data` 寫入文件，格式為 JSON。
                                                                          # `ensure_ascii=False` 允許直接寫入非 ASCII 字元（如中文）。
                                                                          # `indent=2` 使 JSON 輸出格式化，易於閱讀，每層縮排 2 個空格。
                
            print(f"SUCCESS: 數據已成功下載並儲存至 {output_path}") # 打印成功下載和保存數據的訊息。

        except requests.exceptions.RequestException as e: # 捕獲下載數據集時可能發生的請求異常。
            print(f"錯誤：下載數據集失敗。錯誤訊息: {e}") # 打印錯誤訊息。
    else: # 如果任務最終狀態不是 "SUCCEEDED"
        print(f"ERROR: 任務未能成功完成，最終狀態為: {status}。無法下載數據。") # 打印任務失敗的錯誤訊息和最終狀態。


if __name__ == "__main__":
    # 這是 Python 腳本的標準執行入口點。
    # 只有當這個腳本被直接運行時（而不是作為模組被導入時），`if` 語句塊中的程式碼才會執行。
    
    # 腳本的執行入口
    # 我們可以輕易地更改 search_query 來獲取不同餐廳的數據
    search_query = "基隆廟口夜市" # 定義要用於 Apify Actor 搜尋的關鍵字。
    # 構建輸出檔案的路徑和名稱。將 `search_query` 中的空格替換為底線，以創建一個有效的文件名。
    output_file_path = f"data/apify_{search_query.replace(' ', '_')}_output.json"
    
    # 執行主函式
    run_and_get_reviews(search_query, output_file_path) # 調用 `run_and_get_reviews` 函數來開始數據抓取過程。
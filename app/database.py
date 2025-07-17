import os # 導入 os 模組，用於與作業系統進行交互，例如讀取環境變數。
from pymongo import MongoClient # 從 pymongo 庫導入 MongoClient 類。pymongo 是 Python 中用於 MongoDB 資料庫的驅動程式。這裡使用它來連接 Azure Cosmos DB 的 MongoDB API 介面。
from dotenv import load_dotenv # 從 dotenv 庫導入 load_dotenv 函數。這個函數用於從 `.env` 檔案中載入環境變數到程式的執行環境中。

# 載入環境變數
load_dotenv() # 調用 load_dotenv() 會自動查找並讀取當前或父目錄下的 `.env` 檔案，
              # 將其中定義的鍵值對載入為環境變數。這樣可以安全地管理敏感資訊，而不將它們硬編碼到程式碼中。

# 從環境變數讀取您的 Cosmos DB 連線字串和您自訂的資料庫名稱
COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING") # 使用 os.getenv() 函數從環境變數中獲取名為 "COSMOS_CONNECTION_STRING" 的值。
                                                                 # 這是連接 Azure Cosmos DB 所需的完整連接字串。
DB_NAME = os.getenv("DB_NAME", "minesweeper_db") # 使用 os.getenv() 函數獲取名為 "DB_NAME" 的環境變數值。
                                                 # 如果該環境變數不存在，則使用預設值 "minesweeper_db"。
                                                 # 這是您在 Cosmos DB 中用於存儲資料的資料庫名稱。

# 建立一個全域的資料庫連線客戶端變數，初始設為 None
client = None
# 建立一個全域的資料庫實例變數，初始設為 None
db = None

try:
    if not COSMOS_CONNECTION_STRING: # 檢查 `COSMOS_CONNECTION_STRING` 是否為空或 None。
        raise ValueError("COSMOS_CONNECTION_STRING 環境變數未設定。") # 如果連接字串未設定，則拋出 `ValueError`。
    
    client = MongoClient(COSMOS_CONNECTION_STRING) # 使用獲取到的連接字串創建 `MongoClient` 實例，這會建立與 Azure Cosmos DB 的實際網路連接。
    db = client[DB_NAME] # 透過 `client` 物件選擇或創建指定的資料庫。如果資料庫在 Cosmos DB 中不存在，它會自動被創建（在第一次寫入數據時）。
    
    # 建立我們要使用的集合 (Collections)，類似於傳統資料庫的資料表
    places_collection = db["places"] # 獲取或創建名為 "places" 的集合。這個集合通常用於存儲地點的詳細資訊。
    reviews_collection = db["reviews"] # 獲取或創建名為 "reviews" 的集合。這個集合通常用於存儲來自 Apify 抓取的評論數據。
    
    # 測試連線，發送一個 'ping' 命令到管理資料庫，如果連線失敗會拋出異常
    client.admin.command('ping') # 發送一個輕量級命令到資料庫以驗證連接是否活躍。如果連接不成功，這裡會拋出異常。
    print(f"INFO: 成功連接到 Azure Cosmos DB，資料庫: '{DB_NAME}'。") # 如果 `ping` 命令成功，則打印一條成功連接的資訊日誌。

except Exception as e: # 捕獲在嘗試資料庫連接或操作過程中可能發生的任何異常（例如網路問題、連接字串錯誤、身份驗證失敗等）。
    print(f"CRITICAL: 資料庫連線失敗！錯誤: {e}") # 打印一個關鍵錯誤訊息，指示資料庫連接失敗的原因。
    # 在無法連線時，將 collection 設為 None，讓後續程式能判斷資料庫是否可用
    places_collection = None # 將 `places_collection` 設為 None，表示資料庫服務不可用。
    reviews_collection = None # 將 `reviews_collection` 設為 None，表示資料庫服務不可用。
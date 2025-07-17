import os # 導入 os 模組，用於與作業系統進行交互，例如讀取環境變數。
from azure.core.credentials import AzureKeyCredential # 從 Azure SDK 的 `azure.core.credentials` 導入 `AzureKeyCredential` 類。這個類用於使用 API 金鑰進行 Azure 服務的身份驗證。
from azure.ai.textanalytics import TextAnalyticsClient # 從 Azure SDK 的 `azure.ai.textanalytics` 導入 `TextAnalyticsClient` 類。這個類是與 Azure AI Language 服務進行交互的核心客戶端。
from dotenv import load_dotenv # 從 `dotenv` 庫導入 `load_dotenv` 函數，用於從 `.env` 檔案載入環境變數。

load_dotenv() # 調用此函數，會自動讀取專案根目錄下的 `.env` 檔案，並將其中的鍵值對載入到程式的環境變數中。

# 從環境變數讀取 Azure 憑證
AZURE_KEY = os.getenv("AZURE_LANGUAGE_KEY") # 從環境變數中獲取名為 "AZURE_LANGUAGE_KEY" 的值，這是 Azure AI Language 服務的訂閱金鑰。
AZURE_ENDPOINT = os.getenv("AZURE_LANGUAGE_ENDPOINT") # 從環境變數中獲取名為 "AZURE_LANGUAGE_ENDPOINT" 的值，這是 Azure AI Language 服務的端點 URL。

# 初始化文字分析客戶端
text_analytics_client = None # 預設文字分析客戶端變數為 None。
if AZURE_KEY and AZURE_ENDPOINT: # 檢查是否成功獲取了 Azure 金鑰和端點。
    credential = AzureKeyCredential(AZURE_KEY) # 使用獲取到的 Azure 金鑰創建一個 `AzureKeyCredential` 對象，用於身份驗證。
    text_analytics_client = TextAnalyticsClient(endpoint=AZURE_ENDPOINT, credential=credential) # 使用端點 URL 和憑證初始化 `TextAnalyticsClient` 客戶端實例。
    print("INFO: Azure AI Language 服務已成功初始化。") # 如果成功初始化，打印一條資訊日誌。
else: # 如果 Azure 金鑰或端點有任何一個缺失。
    print("WARNING: 未找到 Azure AI Language 的憑證，情感分析功能將被禁用。") # 打印警告訊息，告知情感分析功能將不可用。


def get_sentiment_score(text: str) -> float:
    """
    使用 Azure AI Language 服務，分析一段文字並回傳情感分數。
    分數範圍：正向為 (0, 1]，中性為 0，負向為 [-1, 0)。
    Args:
        text (str): 要進行情感分析的文本字符串。
    Returns:
        float: 情感分數。
    """
    if not text_analytics_client: # 檢查 `text_analytics_client` 是否已成功初始化。如果為 None，表示服務未配置。
        return 0.0 # 如果服務未初始化，則直接回傳 0.0，表示中性分數，不執行實際的 API 呼叫。

    try:
        # Azure API 的情感分析方法需要傳入一個文件列表，即使只有一個文本也必須放入列表中。
        documents = [text] # 將輸入的單個文本放入列表中。
        # 調用 `text_analytics_client` 的 `analyze_sentiment` 方法來執行情感分析。
        # `language="zh-Hant"` 指定了分析的語言為繁體中文。
        # `[0]` 表示從回傳結果列表中取出第一個（也是唯一一個）文檔的分析結果。
        response = text_analytics_client.analyze_sentiment(documents=documents, language="zh-Hant")[0]

        # 如果分析出錯（例如文本格式問題，或服務內部錯誤），則回傳中性。
        if response.is_error: # 檢查回應對象的 `is_error` 屬性，判斷分析是否出錯。
            return 0.0 # 如果出錯，回傳中性分數 0.0。

        # 將 Azure 回傳的 正/中/負面 情感判斷及其信心分數，轉換為我們自定義的 -1 到 1 區間。
        # Azure 的情感結果在 `response.sentiment` 中（"positive", "neutral", "negative"），
        # 信心分數在 `response.confidence_scores` 中（包含 positive, neutral, negative 的分數，範圍 0-1）。
        if response.sentiment == "positive": # 如果 Azure 判斷的情感是 "positive"。
            return response.confidence_scores.positive # 回傳其正向信心分數（範圍 0 到 1）。
        elif response.sentiment == "negative": # 如果 Azure 判斷的情感是 "negative"。
            return -response.confidence_scores.negative # 回傳其負向信心分數，並取負值，使其在 -1 到 0 之間。
        else: # 如果 Azure 判斷的情感是 "neutral"（中性）。
            return 0.0 # 回傳中性分數 0.0。

    except Exception as e: # 捕獲在呼叫 Azure API 過程中可能發生的任何異常（例如網路連接問題、API 限流、憑證無效等）。
        print(f"ERROR: 呼叫 Azure 情感分析 API 失敗: {e}") # 打印錯誤訊息，包含具體的異常內容。
        return 0.0 # 發生錯誤時，回傳中性分數 0.0，避免程式崩潰。
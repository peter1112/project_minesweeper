import pandas as pd # 導入 pandas 庫，用於數據處理和表格操作，特別是 DataFrame 
import json # 導入 json 模組，用於處理 JSON (JavaScript Object Notation) 格式的數據，包括編碼和解碼 
import os # 導入 os 模組，用於與作業系統進行交互，例如讀取環境變數和處理文件路徑 
import re # 導入 re 模組，用於處理正規表達式，例如在文本中查找模式或拆分字符串 
import jieba # 導入 jieba 庫，這是一個流行的中文斷詞工具，用於將中文文本切分成詞語 

# 匯入我們新的情感分析模組
from app.sentiment import get_sentiment_score # 從 `app.sentiment` 模組導入 `get_sentiment_score` 函數，用於執行情感分析 

# 建立相對於本檔案位置的絕對路徑，確保在任何環境下都能正確讀取檔案
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # 獲取當前腳本文件（services.py）的絕對路徑 
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # 獲取專案的根目錄路徑，通常是當前腳本文件所在目錄的父目錄 

class FeatureEngineer:
    """
    一個負責處理原始評論數據並從中提取特徵的類別。(AI 增強版) 
    - 使用 Jieba 進行精準斷詞。 
    - 呼叫外部 AI 服務進行情感分析。 
    - 摘錄評論中的關鍵片語。 
    """
    def __init__(self, keywords_path=os.path.join(PROJECT_ROOT, "data", "keywords.json")):
        """
        初始化 FeatureEngineer。 
        在實例化時，會自動載入三層級的負面關鍵字詞庫及正面詞庫。 
        Args:
            keywords_path (str): 關鍵字 JSON 檔案的絕對或相對路徑。預設路徑為專案根目錄下的 data/keywords.json 
        """
        try:
            # 開啟並載入 keywords.json 檔案，以 UTF-8 編碼讀取 
            with open(keywords_path, 'r', encoding='utf-8') as f:
                self.keywords = json.load(f) # 將 JSON 數據載入到 `self.keywords` 字典中 
            # 將關鍵字列表轉換為 Set 結構，以大幅提升查找速度，因為 Set 查找是 O(1) 的平均時間複雜度 
            self.high_risk_set = set(self.keywords.get('high_risk', [])) # 獲取高風險關鍵字集合 
            self.medium_risk_set = set(self.keywords.get('medium_risk', [])) # 獲取中風險關鍵字集合 
            self.low_risk_set = set(self.keywords.get('low_risk', [])) # 獲取低風險關鍵字集合 
            self.positive_set = set(self.keywords.get('positive_points', [])) # 獲取正面關鍵字集合 
            # 組合所有負面關鍵字（高、中、低風險）為一個總體集合，方便在摘錄時使用。`union` 操作會自動去重 
            self.all_negative_set = self.high_risk_set.union(self.medium_risk_set).union(self.low_risk_set) 
            print(f"INFO: FeatureEngineer 已準備就緒，關鍵字詞庫已從 {keywords_path} 成功載入。") # 成功載入時印出資訊 
        except FileNotFoundError:
            # 如果找不到關鍵字檔案，打印錯誤訊息，並將所有關鍵字集合初始化為空 Set，確保程式不會因為缺失文件而崩潰 
            print(f"錯誤：找不到關鍵字檔案於 {keywords_path}。請確認檔案位置。") 
            self.high_risk_set, self.medium_risk_set, self.low_risk_set, self.positive_set, self.all_negative_set = [set() for _ in range(5)] 

    def _calculate_f1_depth(self, df: pd.DataFrame) -> pd.DataFrame:
        """ 私有方法：計算 F1 - 負評深度。 
            這個方法會為 DataFrame 添加兩個新的布林值欄位。 
        """
        # 根據 'rating' (星級) 欄位判斷評論是否為負面（星級 <= 2），並創建一個新的布林值欄位 'is_negative' 
        df['is_negative'] = df['rating'] <= 2 
        # 根據 'text' (評論文本) 的長度判斷是否為長評論（長度 > 100），並創建一個新的布林值欄位 'is_long_review' 
        df['is_long_review'] = df['text'].str.len() > 100 
        return df # 回傳添加了新欄位的 DataFrame 

    def _calculate_f2_keywords_jieba(self, text: str) -> dict:
        """ 私有方法：使用 Jieba 斷詞來精準計算文本中不同風險等級關鍵字的數量。 
        """
        # 使用 jieba.cut 進行斷詞，`cut_all=False` 表示使用精確模式，這更適合關鍵字匹配 
        seg_list = jieba.cut(text, cut_all=False) 
        # 將斷詞結果轉換為集合 (Set)，以便快速查找關鍵字並自動處理重複詞語 
        word_set = set(seg_list) 
        
        return {
            # 計算文本中高風險關鍵字的數量。通過集合交集操作 `intersection()` 找出共同的詞語，然後計算數量 
            'high_risk_keyword_count': len(self.high_risk_set.intersection(word_set)), 
            # 計算文本中中風險關鍵字的數量 
            'medium_risk_keyword_count': len(self.medium_risk_set.intersection(word_set)), 
            # 計算文本中低風險關鍵字的數量 
            'low_risk_keyword_count': len(self.low_risk_set.intersection(word_set)) 
        }

    def _extract_key_phrases(self, text: str) -> dict:
        """ 私有方法：從評論文本中摘錄代表性的正面和負面關鍵片語。 
        """
        positive_phrases = [] # 初始化一個空列表，用於儲存摘錄到的正面片語 
        negative_phrases = [] # 初始化一個空列表，用於儲存摘錄到的負面片語 
        
        # 使用正規表達式將評論文本拆分為獨立的句子。分句符包括逗號、句號、問號、感嘆號和換行符 
        sentences = re.split(r'[，。！？,!?\n]', text) 
        
        for sentence in sentences: # 遍歷拆分後的所有句子 
            sentence = sentence.strip() # 移除句子兩端的空白字元 
            if not sentence: continue # 如果句子處理後為空，則跳過當前循環 
            
            # 先檢查負面關鍵字，優先摘錄負面信息 (最多 3 句) 
            found_negative = False # 初始化一個布林變數，標記是否在當前句子中找到負面關鍵字 
            if len(negative_phrases) < 3: # 如果負面片語的數量還未達到上限（最多 3 句） 
                for keyword in self.all_negative_set: # 遍歷所有負面關鍵字集合中的詞語 
                    if keyword in sentence: # 如果當前關鍵字存在於句子中 
                        negative_phrases.append(sentence) # 將整個句子添加到負面片語列表 
                        found_negative = True # 標記已找到負面詞 
                        break # 找到一個負面詞後就跳出內部循環，避免重複添加或過度搜索 
            
            # 只有在「沒有」找到負面詞的情況下，才檢查正面關鍵字 (最多 2 句) 
            if not found_negative and len(positive_phrases) < 2: # 如果未找到負面詞且正面片語數量還未達到上限（最多 2 句） 
                for keyword in self.positive_set: # 遍歷所有正面關鍵字集合中的詞語 
                    if keyword in sentence: # 如果當前關鍵字存在於句子中 
                        positive_phrases.append(sentence) # 將整個句子添加到正面片語列表 
                        break # 找到一個正面詞後就跳出內部循環 
        
        return {"positive": positive_phrases, "negative": negative_phrases} # 回傳包含正面和負面片語列表的字典 
        # 注意：原代碼這裡有一個重複的 `return` 語句，實際執行時只有第一個會被觸發，第二個是多餘的。

    def _calculate_f3_trend(self, df: pd.DataFrame, place_info: dict) -> dict:
        """ 私有方法：計算 F3 - 近期趨勢惡化分數。 
            評估地點近期評論評分與歷史平均評分的趨勢。 
        """
        from datetime import datetime, timedelta, timezone # 導入日期時間相關模組，用於時間計算 

        # 獲取地點的歷史平均評分。如果 `place_info` 中有 `totalScore` 字段則用其值，否則計算 DataFrame 中 'rating' 欄位的平均值 
        historical_avg_rating = place_info.get('totalScore', df['rating'].mean()) 
        # 計算 90 天前的時間點。`datetime.now(timezone.utc)` 獲取當前 UTC 時間，`timedelta(days=90)` 定義 90 天的間隔 
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90) 
        # 過濾出近 90 天內的評論數據 
        recent_reviews = df[df['datetime'] >= ninety_days_ago] 
        
        if len(recent_reviews) > 5: # 如果近 90 天的評論數量大於 5 筆（認為有足夠數據計算趨勢） 
            recent_avg_rating = recent_reviews['rating'].mean() # 計算近期評論的平均評分 
            trend_score = historical_avg_rating - recent_avg_rating # 計算趨勢分數 (歷史平均 - 近期平均)。正數表示近期評分下降（趨勢惡化） 
        else: # 如果近期評論數量不足 5 筆 
            recent_avg_rating = None # 將近期平均評分設為 None 
            trend_score = 0 # 趨勢分數設為 0，表示不計算顯著趨勢 

        return {
            "historical_avg": round(historical_avg_rating, 2), # 四捨五入到小數點後兩位 
            "recent_avg": round(recent_avg_rating, 2) if recent_avg_rating is not None else "N/A", # 如果有近期平均則四捨五入，否則為 "N/A" 
            "trend_score": round(trend_score, 3) # 四捨五入到小數點後三位 
        }

    def run(self, place_info: dict) -> tuple[pd.DataFrame | None, dict | None, dict | None]:
        """
        公開方法：執行完整的特徵工程 Pipeline。 
        接收地點資訊 (包含評論列表)，處理後回傳處理後的 DataFrame、趨勢數據和關鍵片語。 
        Args:
            place_info (dict): 包含地點及其評論的字典數據，通常來自 Apify 抓取結果或資料庫快取。 
        Returns:
            tuple[pd.DataFrame | None, dict | None, dict | None]: 
                - 處理後的評論 DataFrame (pd.DataFrame)。 
                - 趨勢資訊字典 (dict)。 
                - 關鍵片語字典 (dict)。 
                如果處理過程中遇到關鍵錯誤（如缺少必要欄位），則可能回傳 None。 
        """
        print("INFO: 開始進行進階特徵工程...") 
        
        reviews_list = place_info.get('reviews', []) # 從 `place_info` 字典中安全地獲取 'reviews' 列表，如果不存在則默認為空列表 
        if not reviews_list: # 如果評論列表為空 
            return pd.DataFrame(), {}, {} # 回傳空的 DataFrame 和空字典，表示沒有數據可供分析 

        df = pd.DataFrame(reviews_list) # 將評論列表轉換為 Pandas DataFrame，便於數據操作 
        # 定義原始數據欄位名稱與我們內部使用名稱的映射關係 
        required_cols = {'stars': 'rating', 'text': 'text', 'publishedAtDate': 'datetime_str'} 
        
        # 檢查 DataFrame 是否包含所有必要的原始欄位 
        if not all(col in df.columns for col in required_cols.keys()): 
            # 如果缺少任何一個必要欄位，則回傳 None，表示處理失敗 
            return None, None, None 
            
        # 選取必要欄位，並移除包含空值的行 (`dropna()`) 
        df = df[list(required_cols.keys())].dropna() 
        # 重新命名選定的欄位為我們內部使用的名稱，`inplace=True` 表示直接在原 DataFrame 上修改 
        df.rename(columns=required_cols, inplace=True) 
        # 過濾掉評論文本為空或只包含空白字元的行。`.str.strip()` 移除文本兩端空白，然後檢查是否為空字串 
        df = df[df['text'].str.strip() != ''].copy() # `.copy()` 避免 Pandas 的 SettingWithCopyWarning 
        if df.empty: # 如果數據清洗後 DataFrame 變為空 
            return pd.DataFrame(), {}, {} # 回傳空的 DataFrame 和空字典 
        # 將 'datetime_str' 欄位（原始的日期時間字串）轉換為 Pandas 的 datetime 對象，便於後續日期時間計算 
        df['datetime'] = pd.to_datetime(df['datetime_str']) 
        print("INFO: 數據清洗完成。") 

        # --- AI 特徵計算 ---
        # 調用私有方法 `_calculate_f1_depth`，為 DataFrame 添加 'is_negative' 和 'is_long_review' 欄位 
        df = self._calculate_f1_depth(df) 

        print("INFO: 正在進行 Jieba 斷詞與關鍵字分析...") 
        # 對 DataFrame 的 'text' 欄位應用 `_calculate_f2_keywords_jieba` 方法。
        # `.apply(pd.Series)` 會將每個調用返回的字典（包含三種關鍵字計數）展開成 DataFrame 的新欄位 
        keyword_counts = df['text'].apply(self._calculate_f2_keywords_jieba).apply(pd.Series) 
        # 將新生成的關鍵字計數欄位與原 DataFrame 合併，`axis=1` 表示按列合併 
        df = pd.concat([df, keyword_counts], axis=1) 
        print("INFO: 關鍵字分析完成。") 

        print("INFO: 正在進行 Azure AI 情感分析...") 
        # 對 DataFrame 的 'text' 欄位應用 `get_sentiment_score` 函數，獲取每條評論的情感分數，並儲存到 'sentiment_score' 欄位 
        df['sentiment_score'] = df['text'].apply(get_sentiment_score) 
        print("INFO: 情感分析完成。") 
        
        print("INFO: 正在摘錄代表性評論片語...") 
        # 對 DataFrame 的 'text' 欄位應用 `_extract_key_phrases` 方法，從每條評論中摘錄正面和負面片語 
        phrases_df = df['text'].apply(self._extract_key_phrases).apply(pd.Series) 
        # 將所有評論中摘錄的正面片語列表扁平化為一個單一列表 
        all_positive = [item for sublist in phrases_df['positive'] for item in sublist] 
        # 將所有評論中摘錄的負面片語列表扁平化為一個單一列表 
        all_negative = [item for sublist in phrases_df['negative'] for item in sublist] 
        # 構建最終的關鍵片語字典。`dict.fromkeys` 用於去重，然後再轉回列表，並限制數量 
        key_phrases = {
            "positive_points": list(dict.fromkeys(all_positive))[:2], # 取前 2 個不重複的正面片語 
            "key_negative_keywords": list(dict.fromkeys(all_negative))[:3] # 取前 3 個不重複的負面片語 
        }
        print("INFO: 片語摘錄完成。") 

        # 調用私有方法 `_calculate_f3_trend`，計算並獲取趨勢相關的數據 
        trend_data = self._calculate_f3_trend(df, place_info) 
        
        # 將原始地點資訊中的評論總數和分佈信息添加到 `trend_data` 字典中 
        trend_data['total_reviews'] = place_info.get('reviewsCount', 0) 
        trend_data['reviews_distribution'] = place_info.get('reviewsDistribution', {}) 

        print("INFO: 進階特徵工程已全部完成。") 
        # 回傳處理後的 DataFrame、趨勢數據字典和關鍵片語字典 
        return df, trend_data, key_phrases 
import pandas as pd # 導入 pandas 庫 , 用於數據處理和表格操作，特別是 DataFrame 。
import numpy as np # 導入 numpy 庫, 用於數值計算 (此處雖未直接使用，但常與 pandas 搭配)。

class LandmineScorer:
    """
    踩雷分數計算器 (AI 增強版) 。
    接收包含多維度AI特徵的數據，並根據更新後的加權公式計算最終踩雷分數和動態摘要 。
    """
    def __init__(self, weights: dict = None):
        """
        初始化計分器 。可傳入自訂權重 。
        Args:
            weights (dict, optional): 自定義的特徵權重字典。如果為 None，則使用預設權重。
        """
        if weights is None: # 如果沒有提供自定義權重 
            # 重新分配權重，納入新的情感分析特徵 (F5) 
            self.weights = { # 定義預設的權重字典 
                "f1_neg_reviews": 0.25, # F1：負評深度的權重 
                "f2_keywords": 0.45,    # F2：關鍵字風險的權重 
                "f3_trend": 0.15,       # F3：趨勢惡化的權重 
                "f5_sentiment": 0.15    # F5：情感分析分數的權重 (新增) 
            }
        else: # 如果提供了自定義權重 
            self.weights = weights # 使用提供的權重 
        print("INFO: LandmineScorer (AI 增強版) 已準備就緒。") # 初始化成功時印出資訊 

    def _calculate_f1_score(self, reviews_distribution: dict, total_reviews: int) -> float:
        """ 私有方法：計算 F1 - 負評深度分數 (0-100) 
            基於評論星級分佈來衡量負評的嚴重程度。
        """
        if total_reviews == 0: # 如果沒有評論，分數為 0 
            return 0.0 # 回傳 0.0 
        
        one_star = reviews_distribution.get("oneStar", 0) # 獲取一星評論數量，如果沒有則為 0 
        two_star = reviews_distribution.get("twoStar", 0) # 獲取二星評論數量，如果沒有則為 0 
        
        weighted_negative_count = (one_star * 1.5) + two_star # 計算加權負面評論數，一星權重為 1.5，二星權重為 1 
        score = (weighted_negative_count / total_reviews) * 200 # 計算分數，並映射到 0-200 範圍 
        return min(score, 100.0) # 確保分數不超過 100 

    def _calculate_f2_score(self, df: pd.DataFrame) -> float:
        """ 
        私有方法：計算 F2 - 關鍵字風險分數 (0-100) 。
        處理三層級的風險關鍵字 。
        """
        if df.empty: # 如果 DataFrame 為空，分數為 0 
            return 0.0 # 回傳 0.0 
            
        total_reviews = len(df) # 獲取評論總數 
        if total_reviews == 0: # 如果評論總數為 0，分數為 0 
            return 0.0 # 回傳 0.0 
        
        high_risk_penalty = 15 # 高風險關鍵字的懲罰分數 
        medium_risk_penalty = 5 # 中風險關鍵字的懲罰分數 
        low_risk_penalty = 1 # 低風險關鍵字的懲罰分數 
        
        total_high_risk = df['high_risk_keyword_count'].sum() # 計算高風險關鍵字總數 
        total_medium_risk = df['medium_risk_keyword_count'].sum() # 計算中風險關鍵字總數 
        total_low_risk = df['low_risk_keyword_count'].sum() # 計算低風險關鍵字總數 
        
        # 計算綜合風險分數：各級別關鍵字總數乘以各自的懲罰分數後加總 
        risk_sum = (total_high_risk * high_risk_penalty) + \
                   (total_medium_risk * medium_risk_penalty) + \
                   (total_low_risk * low_risk_penalty)
        
        score = (risk_sum / total_reviews) * 100 # 將綜合風險分數歸一化到 0-100 範圍 
        return min(score, 100.0) # 確保分數不超過 100 

    def _calculate_f3_score(self, trend_score: float) -> float:
        """ 私有方法：計算 F3 - 趨勢惡化分數 (0-100)  """
        # 將趨勢分數映射到 0-100 範圍，`max(0, ...)` 確保分數不會為負 
        score = max(0, trend_score) * 50 
        return min(score, 100.0) # 確保分數不超過 100 

    def _calculate_f5_score(self, df: pd.DataFrame) -> float:
        """ 
        新增的私有方法：計算 F5 - 情感分析分數 (0-100) 。
        """
        if df.empty or 'sentiment_score' not in df.columns: # 如果 DataFrame 為空或沒有情感分數欄位 
            return 0.0 # 回傳 0.0 
        
        avg_sentiment = df['sentiment_score'].mean() # 計算評論的平均情感分數 (範圍 -1 到 1) 
        # 將情感分數轉換為踩雷分數：越負面 (接近 -1)，分數越高 (接近 100) 
        score = (1 - avg_sentiment) * 50 
        return max(0.0, min(score, 100.0)) # 確保分數在 0 到 100 之間 

    def calculate_score(self, processed_df: pd.DataFrame, trend_info: dict) -> tuple[float, str]:
        """
        公開方法：計算最終的 Landmine Score，並產生動態摘要 。
        回傳一個包含 (分數, 摘要文字) 的元組 。
        Args:
            processed_df (pd.DataFrame): 經過特徵工程處理後的評論數據 DataFrame。
            trend_info (dict): 包含歷史和近期平均評分、評論總數等趨勢相關的字典。
        Returns:
            tuple[float, str]: 一個包含 (最終踩雷分數, 動態摘要文字) 的元組。
        """
        f1_score = self._calculate_f1_score( # 計算 F1 分數 
            trend_info.get('reviews_distribution', {}), # 獲取評論分佈 
            trend_info.get('total_reviews', 0) # 獲取評論總數 
        )
        f2_score = self._calculate_f2_score(processed_df) # 計算 F2 分數 
        f3_score = self._calculate_f3_score(trend_info.get('trend_score', 0)) # 計算 F3 分數 
        f5_score = self._calculate_f5_score(processed_df) # 計算 F5 分數 
        
        print(f"INFO: AI 增強版特徵分數 -> F1(負評): {f1_score:.2f}, F2(關鍵字): {f2_score:.2f}, F3(趨勢): {f3_score:.2f}, F5(情感): {f5_score:.2f}") # 印出各特徵分數 

        # --- 動態摘要生成 ---
        scores_map = { # 建立風險原因與其分數的映射 
            "大量的低星負評": f1_score,
            "評論中提及的負面關鍵字 (如食安、服務)": f2_score,
            "近期的評價有下降趨勢": f3_score,
            "評論內容的整體負面情緒": f5_score
        }
        # 找到分數最高的風險來源 
        if max(scores_map.values()) > 20: # 只有在某項風險足夠顯著 (分數大於 20) 時才產生特定摘要 
            dominant_risk_reason = max(scores_map, key=scores_map.get) # 找出分數最高的風險原因 
            summary = f"注意，主要風險可能來自於「{dominant_risk_reason}」。" # 生成特定摘要 
        else:
            summary = "數據顯示此地點的負面指標較少，整體風險低。" # 如果所有風險分數都較低，則為低風險摘要 
            
        # --- 最終分數計算 ---
        final_score = ( # 根據各特徵分數及其權重計算最終分數 
            f1_score * self.weights['f1_neg_reviews'] +
            f2_score * self.weights['f2_keywords'] +
            f3_score * self.weights['f3_trend'] +
            f5_score * self.weights['f5_sentiment']
        )
        
        final_score = max(0.0, min(final_score, 100.0)) # 確保最終分數在 0.0 到 100.0 之間 
        
        # 如果最終分數很高，覆蓋預設的摘要，給出更強烈的警告 
        if final_score > 70:
            summary = f"警告！綜合多項指標分析，此地點踩雷風險高。主要風險來源為「{dominant_risk_reason}」。" # 生成高度風險警告 

        return final_score, summary # 回傳最終分數和摘要 
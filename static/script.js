// script.js
// 這個 JavaScript 檔案負責處理美食地標防雷系統前端網頁的所有動態互動邏輯。
// 它包括搜尋地點、顯示候選地點列表、發送分析請求到後端，以及最終展示分析結果等功能。

document.addEventListener('DOMContentLoaded', () => {
    // 當整個 HTML 文件和所有靜態資源（如圖片、CSS）都載入並解析完成後，執行此回調函數。
    // 這確保了在嘗試訪問 DOM 元素之前，這些元素已經存在於頁面中。

    // 獲取頁面上的核心元素
    const analyzeButton = document.getElementById('analyzeButton'); // 透過 ID 獲取「開始分析」按鈕元素 
    const searchTermInput = document.getElementById('searchTermInput'); // 透過 ID 獲取搜尋關鍵字輸入框元素 
    const resultsContainer = document.getElementById('resultsContainer'); // 透過 ID 獲取用於顯示結果的容器元素 

    // 主要的事件監聽：當使用者點擊「開始分析」按鈕時觸發
    analyzeButton.addEventListener('click', async () => {
        // 為「開始分析」按鈕添加一個點擊事件監聽器 
        const query = searchTermInput.value; // 獲取輸入框中的搜尋關鍵字（即使用者輸入的地點） 
        if (!query) { // 如果查詢關鍵字為空字串
            alert('請輸入要搜尋的地點！'); // 彈出一個警告框提示使用者 
            return; // 終止函數執行，不繼續後續操作 
        }

        // 顯示載入提示（一個轉圈的動畫和文字訊息），告知使用者正在進行搜尋
        resultsContainer.innerHTML = '<div class="loader"></div><p>正在搜尋地點...</p>'; // 在結果容器中插入 HTML 顯示載入動畫和文字 
        await searchForPlaces(query); // 呼叫非同步函數 searchForPlaces 進行地點搜尋，並等待其完成 
    });

    // 函式一：搜尋候選地點
    async function searchForPlaces(query) {
        // 定義一個非同步函數，用於向後端發送搜尋地點的請求
        try {
            // 步驟一：呼叫後端的 /search 端點
            // 使用 fetch API 向後端發送 GET 請求。
            // 請求路徑為 `/search`，並將查詢字串作為 URL 參數 `query` 傳遞。
            // `encodeURIComponent(query)` 用於將查詢字串進行 URL 編碼，確保特殊字元被正確處理。
            const response = await fetch(`/search?query=${encodeURIComponent(query)}`); 
            if (!response.ok) { // 檢查 HTTP 回應的 `ok` 屬性。如果為 false (表示狀態碼不是 2xx，如 404, 500 等)
                const errorData = await response.json(); // 解析錯誤回應的 JSON 數據，獲取更詳細的錯誤資訊 
                // 拋出一個新的 Error 對象，錯誤訊息來自後端 `detail` 字段或一個通用的伺服器錯誤訊息 
                throw new Error(errorData.detail || `伺服器錯誤: ${response.status}`);
            }
            const candidates = await response.json(); // 如果回應成功，解析 JSON 數據，得到候選地點的陣列 

            // 如果找不到任何地點（候選陣列為空），顯示提示訊息
            if (candidates.length === 0) {
                resultsContainer.innerHTML = '<p class="error">找不到相關地點，請嘗試更換關鍵字。</p>'; // 在結果容器中顯示錯誤訊息 
                return; // 終止函數執行 
            }

            // 步驟二：動態生成候選地點列表，讓使用者選擇
            displayCandidates(candidates); // 呼叫 `displayCandidates` 函數來在頁面上顯示候選地點列表 

        } catch (error) {
            // 捕獲在 `try` 區塊中可能發生的任何錯誤（例如網路問題、HTTP 請求失敗、JSON 解析失敗等）
            resultsContainer.innerHTML = `<p class="error">搜尋失敗：${error.message}</p>`; // 在結果容器中顯示失敗訊息 
        }
    }

    // 函式二：顯示候選地點列表
    function displayCandidates(candidates) {
        // 定義一個函數，用於在結果容器中動態生成候選地點的 HTML 列表
        let candidateHtml = '<h4>您是指以下這個地點嗎？</h4>'; // 初始化 HTML 字串，包含列表標題 
        candidateHtml += '<div class="candidate-list">'; // 開始候選列表的容器 div 
        // 遍歷 `candidates` 陣列中的每一個候選地點
        candidates.forEach(candidate => {
            // 為每一個候選地點創建一個按鈕。
            // `data-placeid` 和 `data-placename` 是 HTML5 的 `data-` 屬性，用於儲存自定義數據，
            // 這些數據之後可以透過 JavaScript 的 `dataset` 屬性輕鬆訪問。
            candidateHtml += `
                <button class="candidate-button" data-placeid="${candidate.place_id}" data-placename="${candidate.name}">
                    <strong>${candidate.name}</strong>
                    <small>${candidate.address}</small>
                </button>
            `; 
        });
        candidateHtml += '</div>'; // 結束候選列表的容器 div 
        resultsContainer.innerHTML = candidateHtml; // 將生成的 HTML 內容插入到結果容器中，替換掉之前的載入提示 

        // 為每一個新建立的候選按鈕，都加上點擊事件監聽
        document.querySelectorAll('.candidate-button').forEach(button => {
            // 獲取所有 class 為 `candidate-button` 的按鈕元素，並遍歷它們 
            button.addEventListener('click', () => { // 為每個按鈕添加一個點擊事件監聽器 
                const placeId = button.dataset.placeid; // 獲取點擊按鈕的 `data-placeid` 屬性值 
                const placeName = button.dataset.placename; // 獲取點擊按鈕的 `data-placename` 屬性值 
                // 直接呼叫 `analyzePlace` 函數，傳遞選定的地點 ID 和名稱。
                // 這裡不需要 `await`，因為 `analyzePlace` 函數內部會處理非同步操作，
                // 且這裡只是觸發一個新的分析流程，不需要等待其結果來影響當前 `displayCandidates` 函數的執行。
                analyzePlace(placeId, placeName); 
            });
        });
    }

    // 函式三：執行最終分析
    async function analyzePlace(placeId, placeName) {
        // 定義一個非同步函數，用於向後端發送分析地點的請求
        // 顯示分析中的提示訊息，並包含首次分析可能較長的提示，因為可能需要即時抓取數據
        resultsContainer.innerHTML = '<div class="loader"></div><p>分析中，請稍候... (首次分析可能需要較長時間抓取數據)</p>'; 
        
        // 步驟三：呼叫後端的 /analyze 端點
        try {
            const response = await fetch('/analyze', { // 向後端 `/analyze` 端點發送請求 
                method: 'POST', // 請求方法為 POST，因為它會傳送數據給伺服器 
                headers: { 'Content-Type': 'application/json' }, // 設定請求頭，告知伺服器請求體是 JSON 格式 
                body: JSON.stringify({ place_id: placeId }) // 將包含 `place_id` 的 JavaScript 對象轉換為 JSON 字串作為請求體 
            });

            if (!response.ok) { // 檢查 HTTP 回應狀態碼是否表示成功 (2xx) 
                const errorData = await response.json(); // 解析錯誤回應的 JSON 數據 
                // 拋出錯誤，錯誤訊息來自後端 `detail` 字段或一個通用的伺服器錯誤訊息 
                throw new Error(errorData.detail || `分析伺服器錯誤: ${response.status}`);
            }
            
            const data = await response.json(); // 如果回應成功，解析 JSON 數據，得到分析結果數據 
            // 使用我們原有的函式 `displayResults` 來顯示最終的分析結果卡片
            displayResults(data); 

        } catch (error) {
            // 捕獲並顯示分析過程中可能發生的錯誤
            resultsContainer.innerHTML = `<p class="error">分析失敗：${error.message}</p>`; // 在結果容器中顯示失敗訊息 
        }
    }

    // 函式四：顯示最終的分析結果卡片
    function displayResults(data) {
        // 定義一個函數，用於根據後端返回的分析數據，動態生成並顯示結果卡片
        let riskColor = '#28a745'; // 預設風險顏色為綠色 (對應 CSS 中的 success 顏色) 
        if (data.risk_level === '中度風險') riskColor = '#ffc107'; // 如果後端判斷為「中度風險」，顏色改為橘色 
        if (data.risk_level === '高度風險') riskColor = '#dc3545'; // 如果後端判斷為「高度風險」，顏色改為紅色 

        // --- 新增：動態生成關鍵片語的 HTML ---
        let negativeKeywordsHtml = ''; // 初始化負面關鍵片語的 HTML 字串 
        if (data.key_negative_keywords && data.key_negative_keywords.length > 0) { // 如果後端返回了負面關鍵片語且列表非空 
            negativeKeywordsHtml += '<h4>負面關鍵片語：</h4><ul>'; // 添加負面關鍵片語的標題和無序列表開頭 
            data.key_negative_keywords.forEach(phrase => { // 遍歷每一個負面片語 
                negativeKeywordsHtml += `<li>“...${phrase}...”</li>`; // 為每個片語創建一個列表項 
            });
            negativeKeywordsHtml += '</ul>'; // 結束無序列表 
        }

        let positivePointsHtml = ''; // 初始化正面提及片語的 HTML 字串 
        if (data.positive_points && data.positive_points.length > 0) { // 如果後端返回了正面提及片語且列表非空 
            positivePointsHtml += '<h4>正面提及：</h4><ul>'; // 添加正面提及的標題和無序列表開頭 
            data.positive_points.forEach(phrase => { // 遍歷每一個正面片語 
                positivePointsHtml += `<li>“...${phrase}...”</li>`; // 為每個片語創建一個列表項 
            });
            positivePointsHtml += '</ul>'; // 結束無序列表 
        }
        // --- 新增結束 ---

        // 將所有結果數據動態組合成一個大的 HTML 字串，並插入到結果容器中
        resultsContainer.innerHTML = `
            <div class="result-card">
                <h2>${data.place_name}</h2> <div class="score-circle" style="border-color: ${riskColor}; color: ${riskColor};">
                    ${data.landmine_score.toFixed(1)} </div>
                <div class="risk-level" style="color: ${riskColor};">
                    ${data.risk_level} 
                </div>
                <p class="summary">"${data.summary}"</p> ${negativeKeywordsHtml} ${positivePointsHtml} <div class="details" style="text-align: left; margin-top: 1rem;">
                    <h4>詳細數據：</h4>
                    <ul>
                        <li>歷史平均分：${data.details.historical_avg}</li> <li>近期平均分：${data.details.recent_avg}</li> <li>評論總數：${data.details.total_reviews}</li> <li>趨勢分數：${data.details.trend_score} (負數代表進步)</li> </ul>
                </div>
            </div>
        `;
    }
});
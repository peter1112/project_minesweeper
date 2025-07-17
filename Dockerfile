# 使用官方 Python 3.12 輕量級映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 將依賴項列表複製到映像中
COPY ./requirements.txt /app/requirements.txt

# 安裝依賴項
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 將專案所有相關資料夾複製到映像中
COPY ./app /app/app
COPY ./static /app/static
COPY ./data /app/data

# 向 Docker 外部開放容器的 8000 端口
EXPOSE 8000

# 容器啟動時執行的指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
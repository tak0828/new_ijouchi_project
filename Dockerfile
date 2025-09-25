# ベースイメージ
FROM python:3.9-slim-bullseye

ENV TZ=Asia/Tokyo
WORKDIR /app

# requirements.txtをコピー
COPY requirements.txt .

# ビルド用パッケージ、MySQL client ライブラリ、Chromium をインストール
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    build-essential \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    chromium \
    fonts-liberation \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential gcc python3-dev libffi-dev libssl-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# debugpy は開発用
RUN pip install debugpy

# Selenium + webdriver-manager 用環境変数（Chromium ヘッドレス用）
ENV CHROME_BIN=/usr/bin/chromium

# ソースコードをコピー
COPY ./src ./src

# デフォルトコマンド例（必要に応じて変更）
CMD ["python", "src/main.py"]

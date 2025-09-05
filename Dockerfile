FROM python:3.9-slim

ENV TZ=Asia/Tokyo

# ビルド用パッケージと MySQL client ライブラリをインストール
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# debugpy をインストール
RUN pip install debugpy

WORKDIR /app

# requirements をインストール
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY ./src ./src

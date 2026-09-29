FROM python:3.10-slim

# 표준 출력 버퍼링 끄기 (로그 실시간 확인)
ENV PYTHONUNBUFFERED=1

# PaddleOCR/OpenCV 구동에 필요한 OS 라이브러리 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 라이브러리 설치 (캐싱 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
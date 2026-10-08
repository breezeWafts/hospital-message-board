FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

# 入口：等待数据库 → 执行迁移 → 写入种子数据 → 启动 uvicorn
CMD ["python", "scripts/entrypoint.py"]

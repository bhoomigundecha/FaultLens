FROM python:3.12-slim
WORKDIR /app
RUN pip install httpx
COPY traffic.py .
CMD ["python", "traffic.py"]

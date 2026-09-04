FROM node:20-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY package*.json ./
RUN npm install --omit=dev
COPY src/ ./src/
EXPOSE 3003
CMD ["node", "-r", "./src/otel.js", "src/index.js"]

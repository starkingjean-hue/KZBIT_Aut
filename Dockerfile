# Utilisation d'une image Python légère
FROM python:3.11-slim

# Variables d'environnement pour Playwright et Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HEADLESS=true
ENV MAX_CONCURRENT_ACCOUNTS=1
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

# Installation des dépendances système critiques pour Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libpango-1-0-0 \
    libcairo2 \
    libasound2 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation du navigateur Chromium et de ses dépendances
RUN playwright install chromium

# Copie de tout le code du projet
COPY . .

# Création du dossier screenshots si nécessaire
RUN mkdir -p screenshots && chmod 777 screenshots

# Port exposé pour le serveur de santé (Railway l'utilise pour le status Healthy)
EXPOSE 8080
ENV PORT=8080

# Lancement en parallèle du serveur de santé et du bot
CMD python health_server.py & python main.py

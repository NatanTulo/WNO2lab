FROM python:3.11-slim

# Ustawienie katalogu roboczego
WORKDIR /app

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Konfiguracja pip z większym timeoutem i retry
RUN pip install --upgrade pip
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

# Kopiowanie pliku requirements.txt
COPY requirements.txt .

# Instalacja tylko PyTorch CPU (bez torchvision i torchaudio)
RUN pip install --retries 5 torch --index-url https://download.pytorch.org/whl/cpu

# Instalacja pozostałych zależności
RUN pip install transformers>=4.20.0 \
    numpy>=1.21.0 \
    flask>=2.0.0 \
    flask-cors>=3.0.0 \
    requests>=2.25.0 \
    gunicorn>=20.1.0

# Kopiowanie kodu aplikacji
COPY . .

# Utworzenie użytkownika nie-root dla bezpieczeństwa
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose portu
EXPOSE 5000

# Zmienne środowiskowe
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Healthcheck z curl
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Komenda uruchomienia z Gunicorn dla produkcji
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--preload", "app:app"]

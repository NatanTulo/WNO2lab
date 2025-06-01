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

# Pre-download modelu przed przełączeniem na użytkownika app
RUN python -c "from transformers import AutoTokenizer, AutoModelForTokenClassification; AutoTokenizer.from_pretrained('dslim/bert-base-NER'); AutoModelForTokenClassification.from_pretrained('dslim/bert-base-NER')" || echo "Model download skipped"

# Utworzenie użytkownika nie-root dla bezpieczeństwa
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && mkdir -p /home/app/.cache \
    && chown -R app:app /home/app/.cache
USER app

# Expose portu
EXPOSE 5000

# Zmienne środowiskowe
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV TRANSFORMERS_CACHE=/home/app/.cache

# Healthcheck z curl
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Komenda uruchomienia - usuwam preload i uruchamiam z jednym workerem
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]

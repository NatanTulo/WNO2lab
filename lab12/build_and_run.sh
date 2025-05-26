#!/bin/bash

echo "=== Budowanie obrazu Docker ==="
docker build -t ner-api:latest .

echo ""
echo "=== Uruchamianie kontenera ==="
docker run -d \
    --name ner-api-container \
    -p 5000:5000 \
    --restart unless-stopped \
    ner-api:latest

echo ""
echo "=== Status kontenera ==="
docker ps | grep ner-api

echo ""
echo "API dostępne pod adresem: http://localhost:5000"
echo "Health check: http://localhost:5000/health"
echo ""
echo "Aby zatrzymać kontener:"
echo "docker stop ner-api-container"
echo ""
echo "Aby usunąć kontener:"
echo "docker rm ner-api-container"

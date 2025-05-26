#!/bin/bash

# Kolory dla czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== NER API Docker Runner ===${NC}"

# Sprawdzenie czy Docker jest zainstalowany
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker nie jest zainstalowany lub niedostępny${NC}"
    exit 1
fi

# Nazwa obrazu i kontenera
IMAGE_NAME="ner-api"
CONTAINER_NAME="ner-api-container"
PORT="5000"

# Funkcja do zatrzymywania istniejącego kontenera
stop_existing_container() {
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo -e "${YELLOW}Zatrzymywanie istniejącego kontenera...${NC}"
        docker stop $CONTAINER_NAME
    fi
    
    if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
        echo -e "${YELLOW}Usuwanie istniejącego kontenera...${NC}"
        docker rm $CONTAINER_NAME
    fi
}

# Funkcja do budowania obrazu
build_image() {
    echo -e "${BLUE}Budowanie obrazu Docker...${NC}"
    if docker build -t $IMAGE_NAME .; then
        echo -e "${GREEN}Obraz zbudowany pomyślnie!${NC}"
    else
        echo -e "${RED}Błąd podczas budowania obrazu${NC}"
        exit 1
    fi
}

# Funkcja do uruchamiania kontenera
run_container() {
    echo -e "${BLUE}Uruchamianie kontenera z mapowaniem portu $PORT...${NC}"
    
    docker run -d \
        --name $CONTAINER_NAME \
        -p $PORT:5000 \
        --restart unless-stopped \
        -e FLASK_ENV=production \
        -e PYTHONUNBUFFERED=1 \
        $IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Kontener uruchomiony pomyślnie!${NC}"
        echo -e "${GREEN}API dostępne pod adresem: http://localhost:$PORT${NC}"
        echo -e "${GREEN}Health check: http://localhost:$PORT/health${NC}"
        echo -e "${GREEN}Dokumentacja: http://localhost:$PORT${NC}"
    else
        echo -e "${RED}Błąd podczas uruchamiania kontenera${NC}"
        exit 1
    fi
}

# Funkcja do wyświetlania logów
show_logs() {
    echo -e "${BLUE}Wyświetlanie logów kontenera...${NC}"
    docker logs -f $CONTAINER_NAME
}

# Funkcja do sprawdzenia statusu
check_status() {
    echo -e "${BLUE}Status kontenera:${NC}"
    docker ps | grep $CONTAINER_NAME || echo -e "${RED}Kontener nie jest uruchomiony${NC}"
    
    echo -e "\n${BLUE}Sprawdzanie health check...${NC}"
    sleep 5
    if curl -s http://localhost:$PORT/health > /dev/null; then
        echo -e "${GREEN}API odpowiada poprawnie!${NC}"
    else
        echo -e "${YELLOW}API jeszcze się uruchamia, sprawdź za chwilę...${NC}"
    fi
}

# Menu główne
case "${1:-run}" in
    "build")
        build_image
        ;;
    "run")
        stop_existing_container
        build_image
        run_container
        check_status
        ;;
    "start")
        run_container
        check_status
        ;;
    "stop")
        stop_existing_container
        echo -e "${GREEN}Kontener zatrzymany${NC}"
        ;;
    "restart")
        stop_existing_container
        run_container
        check_status
        ;;
    "logs")
        show_logs
        ;;
    "status")
        check_status
        ;;
    "clean")
        stop_existing_container
        if docker images -q $IMAGE_NAME > /dev/null; then
            echo -e "${YELLOW}Usuwanie obrazu...${NC}"
            docker rmi $IMAGE_NAME
        fi
        echo -e "${GREEN}Czyszczenie zakończone${NC}"
        ;;
    *)
        echo -e "${BLUE}Użycie: $0 [akcja]${NC}"
        echo ""
        echo "Dostępne akcje:"
        echo "  run     - Zbuduj i uruchom kontener (domyślne)"
        echo "  build   - Tylko zbuduj obraz"
        echo "  start   - Uruchom istniejący obraz"
        echo "  stop    - Zatrzymaj kontener"
        echo "  restart - Zatrzymaj i uruchom ponownie"
        echo "  logs    - Pokaż logi kontenera"
        echo "  status  - Sprawdź status kontenera"
        echo "  clean   - Zatrzymaj i usuń kontener oraz obraz"
        echo ""
        echo "Przykłady:"
        echo "  $0                # Zbuduj i uruchom"
        echo "  $0 run           # Zbuduj i uruchom"
        echo "  $0 logs          # Pokaż logi"
        echo "  $0 stop          # Zatrzymaj"
        ;;
esac

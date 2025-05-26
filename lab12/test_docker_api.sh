#!/bin/bash

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

API_URL="http://localhost:5000"

echo -e "${BLUE}=== Test NER API w Dockerze ===${NC}"

# Test health check
echo -e "\n${BLUE}1. Test Health Check${NC}"
curl -s "$API_URL/health" | python3 -m json.tool

# Test głównego endpointa
echo -e "\n${BLUE}2. Test głównego endpointa${NC}"
curl -s "$API_URL/" | python3 -m json.tool

# Test NER z przykładowym tekstem
echo -e "\n${BLUE}3. Test NER - przykład 1${NC}"
curl -X POST "$API_URL/ner" \
  -H "Content-Type: application/json" \
  -d '{"text": "Donald Trump met with Vladimir Putin in Moscow. Apple Inc. is located in Cupertino."}' | python3 -m json.tool

echo -e "\n${BLUE}4. Test NER - przykład 2${NC}"
curl -X POST "$API_URL/ner" \
  -H "Content-Type: application/json" \
  -d '{"text": "John Smith works at Microsoft Corporation in Seattle, Washington."}' | python3 -m json.tool

# Test błędnych danych
echo -e "\n${BLUE}5. Test błędnych danych${NC}"
curl -X POST "$API_URL/ner" \
  -H "Content-Type: application/json" \
  -d '{"wrong_field": "test"}' | python3 -m json.tool

echo -e "\n${GREEN}Testowanie zakończone!${NC}"

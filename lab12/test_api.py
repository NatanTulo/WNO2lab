import requests
import json

def test_ner_api():
    """Testuje API NER."""
    base_url = "http://localhost:5000"
    
    # Test health check
    print("=== Test Health Check ===")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Błąd: {e}")
    
    print("\n=== Test NER Endpoint ===")
    
    # Dane testowe
    test_cases = [
        {
            "name": "Tekst angielski z bytami",
            "text": "Donald Trump met with Vladimir Putin in Moscow. Apple Inc. is located in Cupertino."
        },
        {
            "name": "Krótki tekst",
            "text": "John works at Microsoft."
        },
        {
            "name": "Tekst bez bytów",
            "text": "This is a simple sentence without named entities."
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        try:
            payload = {"text": test_case["text"]}
            response = requests.post(
                f"{base_url}/ner",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            result = response.json()
            
            if response.status_code == 200:
                print(f"Znaleziono {result.get('entities_count', 0)} bytów:")
                for entity in result.get('entities', []):
                    print(f"  - {entity['text']} ({entity['label']}) - {entity['confidence']:.2%}")
            else:
                print(f"Błąd: {result}")
                
        except Exception as e:
            print(f"Błąd podczas testu: {e}")
    
    # Test błędnych danych
    print("\n=== Test Błędnych Danych ===")
    
    error_cases = [
        {"name": "Brak pola text", "data": {}},
        {"name": "Pusty tekst", "data": {"text": ""}},
        {"name": "Tylko spacje", "data": {"text": "   "}}
    ]
    
    for case in error_cases:
        print(f"\n--- {case['name']} ---")
        try:
            response = requests.post(
                f"{base_url}/ner",
                json=case["data"],
                headers={"Content-Type": "application/json"}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Błąd: {e}")

if __name__ == "__main__":
    test_ner_api()

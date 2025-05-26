from app import app
import json

def test_flask_directly():
    """Testuje Flask API bezpośrednio bez uruchamiania serwera."""
    
    print("=== Test Flask API bezpośrednio ===")
    
    with app.test_client() as client:
        # Test health check
        print("1. Test health check...")
        response = client.get('/health')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        # Test NER endpoint
        print("\n2. Test NER endpoint...")
        test_data = {"text": "John Smith works at Microsoft."}
        response = client.post('/ner', 
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        
        # Test z bardziej złożonym tekstem
        print("\n3. Test z złożonym tekstem...")
        complex_data = {"text": "Donald Trump met with Vladimir Putin in Moscow."}
        response = client.post('/ner',
                             data=json.dumps(complex_data),
                             content_type='application/json')
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

if __name__ == "__main__":
    test_flask_directly()

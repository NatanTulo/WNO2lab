from ner_model import recognize_named_entities, load_ner_model

def main():
    """Przykład użycia funkcji rozpoznawania bytów nazwanych."""
    
    # Tekst testowy (angielski dla lepszej kompatybilności z dostępnymi modelami)
    text = """
    Donald Trump was the President of the United States. 
    He met with Vladimir Putin in Helsinki in 2018.
    Apple Inc. has its headquarters in Cupertino, California.
    Microsoft Corporation was founded by Bill Gates and Paul Allen.
    """
    
    print("Tekst do analizy:")
    print(text)
    print("\n" + "="*50 + "\n")
    
    try:
        # Rozpoznanie bytów nazwanych
        entities = recognize_named_entities(text)
        
        # Wyświetlenie wyników
        print("Rozpoznane byty nazwane:")
        print("-" * 30)
        
        if entities:
            for i, entity in enumerate(entities, 1):
                print(f"{i}. Tekst: '{entity['text']}'")
                print(f"   Typ: {entity['label']}")
                print(f"   Pewność: {entity['confidence']:.2%}")
                print(f"   Pozycja: {entity['start']}-{entity['end']}")
                print()
        else:
            print("Nie znaleziono bytów nazwanych.")
            
    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        print("Sprawdź połączenie internetowe i spróbuj ponownie.")

if __name__ == "__main__":
    main()

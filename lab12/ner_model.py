from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import torch
from typing import List, Dict

class NERProcessor:
    def __init__(self, model_name: str = "dslim/bert-base-NER"):
        """
        Inicjalizuje procesor NER z modelem działającym na CPU.
        
        Args:
            model_name: Nazwa modelu do załadowania (domyślnie dslim/bert-base-NER)
        """
        self.device = "cpu"
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        
    def load_model(self) -> None:
        """Ładuje model i tokenizer na CPU."""
        print(f"Ładowanie modelu {self.model_name} na CPU...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
        
        # Upewnienie się, że model działa na CPU
        self.model.to(self.device)
        
        # Utworzenie pipeline dla łatwiejszego użycia
        self.pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy="simple",
            device=-1  # -1 oznacza CPU
        )
        
        print("Model załadowany pomyślnie!")
    
    def recognize_entities(self, text: str) -> List[Dict]:
        """
        Rozpoznaje byty nazwane w tekście.
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Lista słowników z rozpoznanymi bytami
        """
        if self.pipeline is None:
            raise ValueError("Model nie został załadowany. Użyj load_model() najpierw.")
        
        try:
            # Rozpoznawanie bytów
            entities = self.pipeline(text)
            
            # Przetworzenie wyników do czytelniejszego formatu
            processed_entities = []
            for entity in entities:
                # Obsługa różnych formatów odpowiedzi modelu
                word = entity.get("word", "")
                if not word:
                    word = entity.get("text", "")
                
                # Obsługa różnych nazw pól dla etykiet
                label = entity.get("entity_group")
                if not label:
                    label = entity.get("entity", "UNKNOWN")
                
                processed_entity = {
                    "text": word,
                    "label": label,
                    "confidence": float(entity.get("score", 0.0)),  # Konwersja na Python float
                    "start": entity.get("start", 0),
                    "end": entity.get("end", 0)
                }
                processed_entities.append(processed_entity)
            
            return processed_entities
            
        except Exception as e:
            print(f"Błąd podczas rozpoznawania bytów: {e}")
            print(f"Typ błędu: {type(e)}")
            import traceback
            traceback.print_exc()
            raise e

def load_ner_model(model_name: str = "dslim/bert-base-NER") -> NERProcessor:
    """
    Funkcja pomocnicza do szybkiego ładowania modelu NER.
    
    Args:
        model_name: Nazwa modelu do załadowania
        
    Returns:
        Załadowany procesor NER
    """
    processor = NERProcessor(model_name)
    processor.load_model()
    return processor

def recognize_named_entities(text: str, processor: NERProcessor = None) -> List[Dict]:
    """
    Główna funkcja do rozpoznawania bytów nazwanych w tekście.
    
    Args:
        text: Tekst do analizy
        processor: Opcjonalny procesor NER (jeśli None, zostanie utworzony nowy)
        
    Returns:
        Lista słowników z rozpoznanymi bytami nazwanymi
    """
    if processor is None:
        processor = load_ner_model()
    
    return processor.recognize_entities(text)

# Przykład użycia
if __name__ == "__main__":
    # Przykładowy tekst (w języku angielskim dla lepszej kompatybilności)
    sample_text = """
    John Smith lives in New York and works for Microsoft Corporation. 
    Yesterday he met with Anna Johnson at a restaurant on Fifth Avenue.
    They discussed the upcoming conference in San Francisco.
    """
    
    # Załadowanie modelu
    ner_processor = load_ner_model()
    
    # Rozpoznanie bytów
    entities = recognize_named_entities(sample_text, ner_processor)
    
    # Wyświetlenie wyników
    print("Rozpoznane byty nazwane:")
    for entity in entities:
        print(f"- {entity['text']} ({entity['label']}) - pewność: {entity['confidence']}")

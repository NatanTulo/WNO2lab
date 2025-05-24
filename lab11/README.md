# Analizator Audio - System Rozpoznawania i Generowania Mowy

## Funkcje

- **Speech-to-Text**: Rozpoznawanie mowy z plików audio przy użyciu Whisper
- **Text-to-Speech**: Generowanie mowy z tekstu
- **Analiza jakości**: Automatyczne zliczanie poprawnych próbek audio
- **Wyszukiwanie słów kluczowych**: Znajdowanie określonych słów w nagraniach

## Instalacja

```bash
pip install -r requirements.txt
```

### Pomoc
```bash
# Ogólna pomoc
python main.py -h

# Pomoc dla konkretnej komendy
python main.py stt -h
python main.py tts -h
python main.py quality -h
python main.py count -h
python main.py search -h
```

## Użycie programistyczne

```python
from audio_analyzer import AudioAnalyzer

analyzer = AudioAnalyzer()

# Rozpoznawanie mowy
text = analyzer.speech_to_text("nagranie.wav")

# Generowanie mowy
analyzer.text_to_speech("Witaj świecie", "output.wav")

# Analiza jakości
quality = analyzer.analyze_audio_quality("nagranie.wav")

# Wyszukiwanie słów kluczowych
result = analyzer.find_keyword_in_audio("nagranie.wav", "test")
```

## Kryteria poprawnych próbek

- Długość nagrania: maksymalnie 5 sekund
- Poziom głośności: powyżej -40 dB
- Spektrum mowy: obecność sygnału w paśmie 300-3000 Hz

## Uwagi dotyczące języków

- **Whisper** automatycznie wykrywa język w nagraniu
- **Jakość rozpoznawania** jest najlepsza dla języka angielskiego, ale polski jest bardzo dobrze obsługiwany
- **TTS** wymaga zainstalowanych głosów systemowych dla danego języka
- **Wyszukiwanie słów kluczowych** działa dla wszystkich języków obsługiwanych przez Whisper

## Obsługiwane języki

### Rozpoznawanie mowy (Whisper):
Model Whisper obsługuje ponad 90 języków, w tym:
- **Polski** (pl)
- Angielski (en)
- Niemiecki (de)
- Francuski (fr)
- Hiszpański (es)
- Włoski (it)
- Rosyjski (ru)
- Chiński (zh)
- Japoński (ja)
- Koreański (ko)
- Arabski (ar)
- Hindi (hi)
- Portugalski (pt)
- Holenderski (nl)
- Szwedzki (sv)
- Norweski (no)
- Duński (da)
- Fiński (fi)
- Czeski (cs)
- Słowacki (sk)
- Ukraiński (uk)
- I wiele innych...

### Generowanie mowy (pyttsx3):
System TTS obsługuje języki dostępne w systemie operacyjnym:
- **Polski** (pl-PL) - domyślnie na polskich systemach
- Angielski (en-US, en-GB)
- Niemiecki (de-DE)
- Francuski (fr-FR)
- Hiszpański (es-ES)
- Inne języki w zależności od zainstalowanych głosów w systemie
import whisper
import librosa
import numpy as np
import soundfile as sf
from typing import Tuple, Dict, List
import pyttsx3
import os
import argparse
import glob
import sys

class AudioAnalyzer:
    def __init__(self):
        """Inicjalizacja analizatora audio z modelem Whisper."""
        print("Ładowanie modelu Whisper...")
        self.whisper_model = whisper.load_model("base")
        self.tts_engine = pyttsx3.init()
        
    def speech_to_text(self, audio_path: str) -> str:
        """
        Rozpoznawanie mowy z pliku audio przy użyciu Whisper.
        
        Args:
            audio_path: Ścieżka do pliku audio
            
        Returns:
            Rozpoznany tekst
        """
        try:
            result = self.whisper_model.transcribe(audio_path)
            return result["text"].strip()
        except Exception as e:
            print(f"Błąd podczas rozpoznawania mowy: {e}")
            return ""
    
    def text_to_speech(self, text: str, output_path: str = None) -> bool:
        """
        Generowanie mowy z tekstu.
        
        Args:
            text: Tekst do przekształcenia na mowę
            output_path: Opcjonalna ścieżka do zapisu pliku audio
            
        Returns:
            True jeśli operacja się powiodła
        """
        try:
            if output_path:
                self.tts_engine.save_to_file(text, output_path)
                self.tts_engine.runAndWait()
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"Błąd podczas generowania mowy: {e}")
            return False
    
    def analyze_audio_quality(self, audio_path: str) -> Dict:
        """
        Analiza jakości nagrania audio.
        
        Args:
            audio_path: Ścieżka do pliku audio
            
        Returns:
            Słownik z metrykami jakości
        """
        try:
            # Wczytanie pliku audio
            y, sr = librosa.load(audio_path)
            
            # Długość nagrania
            duration = len(y) / sr
            
            # Średni poziom głośności w dB
            rms = librosa.feature.rms(y=y)[0]
            db_level = 20 * np.log10(np.mean(rms) + 1e-10)  # Dodanie małej wartości aby uniknąć log(0)
            
            # Analiza spektrum - sprawdzenie obecności sygnału w paśmie 300-3000 Hz
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Znalezienie indeksów dla pasma 300-3000 Hz
            freq_mask = (freqs >= 300) & (freqs <= 3000)
            speech_band_energy = np.mean(magnitude[freq_mask, :])
            total_energy = np.mean(magnitude)
            speech_ratio = speech_band_energy / (total_energy + 1e-10)
            
            # Określenie czy nagranie jest poprawne
            is_valid = (
                duration <= 5.0 and          # Długość do 5s
                db_level > -40 and           # Poziom głośności > -40 dB
                speech_ratio > 0.1           # Obecność sygnału w paśmie mowy
            )
            
            return {
                'duration': duration,
                'db_level': db_level,
                'speech_ratio': speech_ratio,
                'is_valid': is_valid,
                'details': {
                    'duration_ok': duration <= 5.0,
                    'volume_ok': db_level > -40,
                    'spectrum_ok': speech_ratio > 0.1
                }
            }
            
        except Exception as e:
            print(f"Błąd podczas analizy audio: {e}")
            return {
                'duration': 0,
                'db_level': -100,
                'speech_ratio': 0,
                'is_valid': False,
                'details': {
                    'duration_ok': False,
                    'volume_ok': False,
                    'spectrum_ok': False
                }
            }
    
    def count_valid_samples(self, audio_files: List[str]) -> Dict:
        """
        Zliczanie poprawnych próbek audio.
        
        Args:
            audio_files: Lista ścieżek do plików audio
            
        Returns:
            Statystyki analizy
        """
        valid_count = 0
        total_count = len(audio_files)
        results = []
        
        for audio_file in audio_files:
            quality = self.analyze_audio_quality(audio_file)
            results.append({
                'file': audio_file,
                'quality': quality
            })
            
            if quality['is_valid']:
                valid_count += 1
                
        return {
            'total_files': total_count,
            'valid_files': valid_count,
            'invalid_files': total_count - valid_count,
            'valid_percentage': (valid_count / total_count * 100) if total_count > 0 else 0,
            'results': results
        }
    
    def find_keyword_in_audio(self, audio_path: str, keyword: str) -> Dict:
        """
        Wyszukiwanie słowa kluczowego w nagraniu.
        
        Args:
            audio_path: Ścieżka do pliku audio
            keyword: Słowo kluczowe do wyszukania
            
        Returns:
            Informacje o znalezieniu słowa kluczowego
        """
        # Rozpoznanie tekstu z nagrania
        transcribed_text = self.speech_to_text(audio_path)
        
        # Wyszukiwanie słowa kluczowego (bez rozróżniania wielkości liter)
        keyword_lower = keyword.lower()
        text_lower = transcribed_text.lower()
        
        found = keyword_lower in text_lower
        
        # Znajdowanie pozycji słowa kluczowego
        positions = []
        if found:
            words = text_lower.split()
            for i, word in enumerate(words):
                if keyword_lower in word:
                    positions.append(i)
        
        return {
            'transcribed_text': transcribed_text,
            'keyword': keyword,
            'found': found,
            'positions': positions,
            'word_count': len(transcribed_text.split()) if transcribed_text else 0
        }

def cmd_speech_to_text(analyzer, args):
    """Komenda rozpoznawania mowy."""
    if not os.path.exists(args.input):
        print(f"Błąd: Plik {args.input} nie istnieje")
        return
    
    print(f"Rozpoznawanie mowy z pliku: {args.input}")
    text = analyzer.speech_to_text(args.input)
    print(f"Rozpoznany tekst: '{text}'")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Tekst zapisany do: {args.output}")

def cmd_text_to_speech(analyzer, args):
    """Komenda generowania mowy z tekstu."""
    if args.input_file:
        if not os.path.exists(args.input_file):
            print(f"Błąd: Plik {args.input_file} nie istnieje")
            return
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        text = args.text
    
    if not text:
        print("Błąd: Brak tekstu do przetworzenia")
        return
    
    print(f"Generowanie mowy dla tekstu: '{text[:50]}...' " if len(text) > 50 else f"'{text}'")
    
    output_path = args.output or "generated_speech.wav"
    if analyzer.text_to_speech(text, output_path):
        print(f"Mowa zapisana do: {output_path}")
    else:
        print("Błąd podczas generowania mowy")

def cmd_analyze_quality(analyzer, args):
    """Komenda analizy jakości pojedynczego pliku."""
    if not os.path.exists(args.input):
        print(f"Błąd: Plik {args.input} nie istnieje")
        return
    
    print(f"Analiza jakości pliku: {args.input}")
    quality = analyzer.analyze_audio_quality(args.input)
    
    print(f"\nWyniki analizy:")
    print(f"Długość: {quality['duration']:.2f}s (max 5s)")
    print(f"Poziom głośności: {quality['db_level']:.2f} dB (min -40 dB)")
    print(f"Współczynnik mowy: {quality['speech_ratio']:.3f} (min 0.1)")
    print(f"Poprawne nagranie: {'TAK' if quality['is_valid'] else 'NIE'}")
    
    print(f"\nSzczegóły:")
    details = quality['details']
    print(f"  - Długość OK: {'✓' if details['duration_ok'] else '✗'}")
    print(f"  - Głośność OK: {'✓' if details['volume_ok'] else '✗'}")
    print(f"  - Spektrum OK: {'✓' if details['spectrum_ok'] else '✗'}")

def cmd_count_valid(analyzer, args):
    """Komenda zliczania poprawnych próbek."""
    if args.directory:
        audio_files = []
        for ext in ['*.wav', '*.mp3', '*.m4a', '*.flac']:
            audio_files.extend(glob.glob(os.path.join(args.directory, ext)))
    else:
        audio_files = args.files
    
    if not audio_files:
        print("Brak plików audio do analizy")
        return
    
    print(f"Analiza {len(audio_files)} plików audio...")
    stats = analyzer.count_valid_samples(audio_files)
    
    print(f"\n=== STATYSTYKI ===")
    print(f"Łączna liczba plików: {stats['total_files']}")
    print(f"Poprawne nagrania: {stats['valid_files']}")
    print(f"Niepoprawne nagrania: {stats['invalid_files']}")
    print(f"Procent poprawnych: {stats['valid_percentage']:.1f}%")
    
    if args.verbose:
        print(f"\n=== SZCZEGÓŁOWY RAPORT ===")
        for result in stats['results']:
            filename = os.path.basename(result['file'])
            is_valid = result['quality']['is_valid']
            status = "✓ POPRAWNE" if is_valid else "✗ NIEPOPRAWNE"
            print(f"  {filename}: {status}")

def cmd_find_keyword(analyzer, args):
    """Komenda wyszukiwania słów kluczowych."""
    if args.directory:
        audio_files = []
        for ext in ['*.wav', '*.mp3', '*.m4a', '*.flac']:
            audio_files.extend(glob.glob(os.path.join(args.directory, ext)))
    else:
        audio_files = [args.input]
    
    if not audio_files:
        print("Brak plików audio do przeszukania")
        return
    
    keyword = args.keyword
    print(f"Szukam słowa kluczowego: '{keyword}' w {len(audio_files)} plikach...")
    
    found_files = []
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            continue
            
        print(f"\nAnalizuję: {os.path.basename(audio_file)}")
        result = analyzer.find_keyword_in_audio(audio_file, keyword)
        
        print(f"Tekst: '{result['transcribed_text']}'")
        print(f"Słowo kluczowe znalezione: {'TAK' if result['found'] else 'NIE'}")
        
        if result['found']:
            found_files.append(audio_file)
            print(f"Pozycje w tekście: {result['positions']}")
    
    print(f"\n=== PODSUMOWANIE ===")
    print(f"Przeszukano plików: {len(audio_files)}")
    print(f"Znaleziono słowo kluczowe w: {len(found_files)} plikach")

def main():
    parser = argparse.ArgumentParser(
        description="Analizator Audio - System Rozpoznawania i Generowania Mowy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SZCZEGÓŁOWY OPIS KOMEND I ARGUMENTÓW:

═══════════════════════════════════════════════════════════════════

1. ROZPOZNAWANIE MOWY (stt - Speech-to-Text):
   Konwertuje pliki audio na tekst przy użyciu modelu Whisper AI

   Argumenty:
   -i, --input     [WYMAGANY] Ścieżka do pliku audio wejściowego
                   Obsługiwane formaty: .wav, .mp3, .m4a, .flac
   -o, --output    [OPCJONALNY] Ścieżka do pliku tekstowego wyjściowego
                   Jeśli nie podano, tekst wyświetli się tylko na konsoli

   Przykłady:
   python main.py stt -i nagranie.wav
   python main.py stt -i nagranie.mp3 -o rozpoznany_tekst.txt

═══════════════════════════════════════════════════════════════════

2. GENEROWANIE MOWY (tts - Text-to-Speech):
   Konwertuje tekst na mowę syntetyczną

   Argumenty (jeden z dwóch wymagany):
   -t, --text      Tekst do przetworzenia podany bezpośrednio w cudzysłowie
   -f, --input-file Ścieżka do pliku tekstowego zawierającego tekst
   
   -o, --output    [OPCJONALNY] Ścieżka do pliku audio wyjściowego (.wav)
                   Domyślnie: "generated_speech.wav"
                   Bez tego argumentu mowa jest tylko odtwarzana

   Przykłady:
   python main.py tts -t "Witaj świecie"
   python main.py tts -t "Tekst do odczytania" -o mowa.wav
   python main.py tts -f dokument.txt -o audio_z_dokumentu.wav

═══════════════════════════════════════════════════════════════════

3. ANALIZA JAKOŚCI AUDIO (quality):
   Sprawdza czy nagranie spełnia kryteria poprawności

   Kryteria oceny:
   - Długość nagrania: maksymalnie 5 sekund
   - Poziom głośności: powyżej -40 dB
   - Spektrum mowy: obecność sygnału w paśmie 300-3000 Hz

   Argumenty:
   -i, --input     [WYMAGANY] Ścieżka do pliku audio do analizy

   Przykład:
   python main.py quality -i nagranie.wav

═══════════════════════════════════════════════════════════════════

4. ZLICZANIE POPRAWNYCH PRÓBEK (count):
   Analizuje wiele plików audio i zlicza ile spełnia kryteria jakości

   Argumenty (jeden z dwóch wymagany):
   -d, --directory Ścieżka do katalogu zawierającego pliki audio
                   Przeszukuje automatycznie pliki: .wav, .mp3, .m4a, .flac
   -f, --files     Lista konkretnych plików audio oddzielonych spacją
   
   -v, --verbose   [OPCJONALNY] Wyświetla szczegółowy raport dla każdego pliku
                   Bez tej flagi pokazuje tylko statystyki ogólne

   Przykłady:
   python main.py count -d ./audio_files/
   python main.py count -d ./nagrania/ -v
   python main.py count -f plik1.wav plik2.wav plik3.mp3
   python main.py count -f *.wav -v

═══════════════════════════════════════════════════════════════════

5. WYSZUKIWANIE SŁÓW KLUCZOWYCH (search):
   Znajduje określone słowo w nagraniach audio poprzez rozpoznawanie mowy

   Argumenty (jeden z dwóch wymagany):
   -i, --input     Ścieżka do pojedynczego pliku audio do przeszukania
   -d, --directory Ścieżka do katalogu z plikami audio do przeszukania
   
   -k, --keyword   [WYMAGANY] Słowo kluczowe do wyszukania
                   Wyszukiwanie jest niewrażliwe na wielkość liter
                   Znajduje również częściowe dopasowania w słowach

   Przykłady:
   python main.py search -i nagranie.wav -k "test"
   python main.py search -d ./audio_files/ -k "ważne"
   python main.py search -d ./nagrania/ -k "spotkanie"

═══════════════════════════════════════════════════════════════════

OBSŁUGIWANE FORMATY PLIKÓW:

Wejściowe (audio):
• .wav - format WAV (zalecany dla najlepszej jakości)
• .mp3 - format MP3 (skompresowany)
• .m4a - format M4A/AAC
• .flac - format FLAC (bezstratny)

Wyjściowe:
• .wav - pliki audio (TTS)
• .txt - pliki tekstowe (STT)

═══════════════════════════════════════════════════════════════════

OBSŁUGIWANE JĘZYKI:

Model Whisper automatycznie wykrywa język w nagraniu.
Obsługuje ponad 90 języków, w tym polski, angielski, niemiecki,
francuski, hiszpański, włoski, rosyjski i wiele innych.

System TTS wykorzystuje głosy zainstalowane w systemie operacyjnym.

═══════════════════════════════════════════════════════════════════

KODY WYJŚCIA:
0 - Sukces
1 - Błąd argumentów lub błąd wykonania
2 - Brak wymaganego pliku wejściowego

Aby uzyskać pomoc dla konkretnej komendy, użyj:
python main.py <komenda> -h

Przykład: python main.py stt -h
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Dostępne komendy')
    
    # Speech-to-Text
    stt_parser = subparsers.add_parser('stt', help='Rozpoznawanie mowy')
    stt_parser.add_argument('-i', '--input', required=True, help='Plik audio wejściowy')
    stt_parser.add_argument('-o', '--output', help='Plik tekstowy wyjściowy')
    
    # Text-to-Speech
    tts_parser = subparsers.add_parser('tts', help='Generowanie mowy')
    tts_group = tts_parser.add_mutually_exclusive_group(required=True)
    tts_group.add_argument('-t', '--text', help='Tekst do przetworzenia')
    tts_group.add_argument('-f', '--input-file', help='Plik tekstowy wejściowy')
    tts_parser.add_argument('-o', '--output', help='Plik audio wyjściowy (domyślnie: generated_speech.wav)')
    
    # Analiza jakości
    quality_parser = subparsers.add_parser('quality', help='Analiza jakości audio')
    quality_parser.add_argument('-i', '--input', required=True, help='Plik audio do analizy')
    
    # Zliczanie poprawnych próbek
    count_parser = subparsers.add_parser('count', help='Zliczanie poprawnych próbek')
    count_group = count_parser.add_mutually_exclusive_group(required=True)
    count_group.add_argument('-d', '--directory', help='Katalog z plikami audio')
    count_group.add_argument('-f', '--files', nargs='+', help='Lista plików audio')
    count_parser.add_argument('-v', '--verbose', action='store_true', help='Szczegółowy raport')
    
    # Wyszukiwanie słów kluczowych
    search_parser = subparsers.add_parser('search', help='Wyszukiwanie słów kluczowych')
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument('-i', '--input', help='Plik audio do przeszukania')
    search_group.add_argument('-d', '--directory', help='Katalog z plikami audio')
    search_parser.add_argument('-k', '--keyword', required=True, help='Słowo kluczowe do wyszukania')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Inicjalizacja analizatora
    print("Inicjalizacja analizatora audio...")
    analyzer = AudioAnalyzer()
    
    # Wykonanie odpowiedniej komendy
    if args.command == 'stt':
        cmd_speech_to_text(analyzer, args)
    elif args.command == 'tts':
        cmd_text_to_speech(analyzer, args)
    elif args.command == 'quality':
        cmd_analyze_quality(analyzer, args)
    elif args.command == 'count':
        cmd_count_valid(analyzer, args)
    elif args.command == 'search':
        cmd_find_keyword(analyzer, args)

if __name__ == "__main__":
    main()
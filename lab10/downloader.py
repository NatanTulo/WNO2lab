import requests
import shutil

def download_image(url, file_name):
    """Pobiera obraz z podanego adresu URL i zapisuje go do pliku."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Sprawdza, czy żądanie zakończyło się sukcesem
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        print(f"Obraz został pomyślnie pobrany i zapisany jako {file_name}")
    except requests.exceptions.RequestException as e:
        print(f"Wystąpił błąd podczas pobierania obrazu: {e}")
    except IOError as e:
        print(f"Wystąpił błąd podczas zapisywania pliku: {e}")

if __name__ == "__main__":
    image_url_base = "https://picsum.photos/1024"
    num_images = 20
    for i in range(num_images):
        output_file_name = f"placeholder_image_{i+1}.jpg"
        download_image(image_url_base, "in/backgrounds/"+output_file_name)
import requests
import shutil
import os

def download_image(url, file_name):
    """Pobiera obraz z podanego adresu URL i zapisuje go do pliku."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        print(f"Obraz został pomyślnie pobrany i zapisany jako {file_name}")
    except requests.exceptions.RequestException as e:
        print(f"Wystąpił błąd podczas pobierania obrazu: {e}")
    except IOError as e:
        print(f"Wystąpił błąd podczas zapisywania pliku: {e}")

if __name__ == "__main__":
    folder_path = "in/backgrounds"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    image_url_base = "https://picsum.photos/1024"
    num_images = 20
    for i in range(num_images):
        output_file_name = f"placeholder_image_{i+1}.jpg"
        # Poprawiono łączenie ścieżek
        full_output_path = os.path.join(folder_path, output_file_name)
        download_image(image_url_base, full_output_path)
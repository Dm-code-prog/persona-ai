import requests

def download_file(url: str, save_path: str):
    try:
        # Stream the request for downloading large files efficiently
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # Raise an error for bad HTTP responses
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):  # Download in chunks of 8 KB
                    if chunk:  # Filter out keep-alive chunks
                        file.write(chunk)
        print(f"File downloaded successfully to {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
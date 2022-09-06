import requests

def download(uri: str) -> requests.Response:
    """Download text file with the application's header."""
    headers = {'User-Agent': 'python-feed-reader'}
    try:
        request = requests.get(uri, headers=headers)
        request.raise_for_status()
    except Exception as exc:
        raise Exception(f"Request feed error: {exc if 'request' in locals() else 'cannot connect'}") from exc
    return request

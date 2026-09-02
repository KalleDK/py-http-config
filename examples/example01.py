from http_config import HTTPConfig
from http_config.httpx2 import sync_client

if __name__ == "__main__":
    conf = HTTPConfig()

    client = sync_client(conf)
    response = client.get("https://httpbin.org/get")
    print(response.status_code)
    print(response.json())

import requests
import json

# Load configuration from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

bot_token = config['bot_token']

def get_updates():
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    response = requests.get(url)
    data = response.json()
    print(json.dumps(data, indent=4))

if __name__ == "__main__":
    get_updates()
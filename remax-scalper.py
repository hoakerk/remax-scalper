import time
import requests
import json
import sqlite3
import asyncio
import logging
from telegram import Bot

# Load configuration from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

url = config['url']
currency = config['currency'],
base_url = config['base_url']
filters = config['filters']
bot_token = config['bot_token']
chat_id = config['chat_id']
MAX_LISTING_PRICE = config['max_listing_price'] # Maximum price to send a Telegram message
send_telegram_msg = config['send_telegram_msg'] # Enable or disable sending Telegram messages (boolean)

# Configure logging
logging.basicConfig(filename='remax_scalper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=bot_token)

async def send_telegram_message(chat_id, text, send_telegram_msg):
    if send_telegram_msg:
        await bot.send_message(chat_id=chat_id, text=text)
        logging.info(f"Sent Telegram message: {text}")
        time.sleep(10) # 10 seconds delay to prevent Telegram rate limiting

def submit_filters(url, filters):
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, data=filters, headers=headers)
    logging.info(f"Submitted filters to URL: {url}")
    return response.json()

def initialize_db():
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            listingTitle TEXT PRIMARY KEY,
            smallDescription TEXT,
            listingStatusID INTEGER,
            descriptionTags TEXT,
            listingPrice REAL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Initialized database and created table if not exists")

async def store_in_db(data, send_telegram_msg):
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    for item in data:
        cursor.execute('SELECT listingPrice FROM listings WHERE listingTitle = ?', (item['listingTitle'],))
        result = cursor.fetchone()
        if item['listingStatusID'] == 1 and item['listingPrice'] >= 0:
            if result:
                previous_price = result[0]
                cursor.execute('''
                    UPDATE listings
                    SET smallDescription = ?, listingStatusID = ?, descriptionTags = ?, listingPrice = ?
                    WHERE listingTitle = ?
                ''', (item['smallDescription'], item['listingStatusID'], item['descriptionTags'], item['listingPrice'], item['listingTitle']))
                if item['listingPrice'] <= MAX_LISTING_PRICE and item['listingPrice'] < previous_price:
                    link = f"{base_url}/{item['descriptionTags']}/{item['listingTitle']}"
                    message = f"Price dropped to: {item['listingPrice']} {currency} (from {previous_price} {currency})\n{link}"
                    try:
                        await send_telegram_message(chat_id, message, send_telegram_msg)
                        logging.info(f"Updated listing in database and sent price drop message: {item['listingTitle']}")
                    except Exception as e:
                        logging.error(f"Failed to send message: {e}")
            else:
                cursor.execute('''
                    INSERT INTO listings (listingTitle, smallDescription, listingStatusID, descriptionTags, listingPrice)
                    VALUES (?, ?, ?, ?, ?)
                ''', (item['listingTitle'], item['smallDescription'], item['listingStatusID'], item['descriptionTags'], item['listingPrice']))
                if item['listingPrice'] <= MAX_LISTING_PRICE:
                    link = f"{base_url}/{item['descriptionTags']}/{item['listingTitle']}"
                    message = f"Price: {item['listingPrice']} {currency}\n{link}"
                    try:
                        await send_telegram_message(chat_id, message, send_telegram_msg)
                        logging.info(f"Inserted new listing into database: {item['listingTitle']}")
                    except Exception as e:
                        logging.error(f"Failed to send message: {e}")
        else:
            if result:
                cursor.execute('''
                    DELETE FROM listings WHERE listingTitle = ?
                ''', (item['listingTitle'],))
                logging.info(f"Deleted listing from database: {item['listingTitle']}")
    conn.commit()
    conn.close()

async def main():
    response = submit_filters(url, filters)
    
    # Initialize the database
    initialize_db()
    
    # Log the message if Telegram messages are disabled
    if not send_telegram_msg:
        logging.info("Telegram messages are disabled in the configuration.")
    
    # Extract relevant information
    results = response.get('results', [])
    relevant_info = []
    for result in results:
        relevant_info.append({
            'smallDescription': result.get('smallDescription', ''),
            'listingStatusID': result.get('listingStatusID', ''),
            'listingTitle': result.get('listingTitle', ''),
            'descriptionTags': result.get('descriptionTags', ''),
            'listingPrice': result.get('listingPrice', 0)
        })
    
    # Store the relevant information in the database
    await store_in_db(relevant_info, send_telegram_msg)
    
    # Save the full response to a file
    with open('response.json', 'w') as f:
        json.dump(response, f, indent=4)
    logging.info("Saved full response to response.json")

if __name__ == "__main__":
    logging.info("Starting remax-scalper script")
    asyncio.run(main())
    logging.info("Finished remax-scalper script")


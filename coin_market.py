import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests

options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-popup-blocking")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

chrome_service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=chrome_service, options=options)

url = "https://coinmarketcap.com/new/"
driver.get(url)

cryptos = []

# Fetch all SPOT trading pairs from Binance
url_binance = "https://api.binance.com/api/v3/exchangeInfo"
response_binance = requests.get(url_binance)

if response_binance.status_code == 200:
    data_binance = response_binance.json()
    symbols = data_binance['symbols']
    binance_symbols = {s['baseAsset'].lower() for s in symbols}
    print("✅ Fetched data from Binance")
else:
    print(f"Error fetching data from Binance: {response_binance.status_code}")
    binance_symbols = set()

def scrape_page():
    print("🔄 Starting page scan...")
    # Wait until the table loads – timeout set to 10 seconds
    wait = WebDriverWait(driver, 10)
    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cmc-table")))

    # Fetch table rows
    rows = table.find_elements(By.XPATH, ".//tbody/tr")

    for row in rows:
        try:
            volume_text = row.find_element(By.XPATH, ".//td[8]").text.replace('$', '').replace(',', '')
            if volume_text == '--':
                continue
            volume = float(volume_text)
            if volume > 3_000_000:
                volume_m = f"{round(volume / 1_000_000, 1)}M"
                name = row.find_element(By.XPATH, ".//td[3]//p").text.lower()
                if any(symbol in name for symbol in binance_symbols):
                    print(f"❌ {name} is on Binance, skipping...")
                    continue
                try:
                    symbol = row.find_element(By.XPATH, ".//td[3]//p[2]").text.lower()
                except:
                    symbol = "N/A"
                price = row.find_element(By.XPATH, ".//td[4]").text
                blockchain = row.find_element(By.XPATH, ".//td[9]").text
                added = row.find_element(By.XPATH, ".//td[10]").text

                cryptos.append([name, symbol, price, volume_m, blockchain, added])
                print(f"✅ Added {name} ({symbol})")
        except Exception as e:
            print(f"Error fetching data from row: {e}")

# Ensure the driver quits properly even if an exception occurs
try:
    page_count = 0
    while page_count < 5:
        scrape_page()
        try:
            next_button = driver.find_element(By.XPATH, "//li[@class='next']/a")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            driver.execute_script("arguments[0].click();", next_button)
            print(f"➡️ Moving to page {page_count + 2}")
            time.sleep(5)  # Wait for the new page to load
            page_count += 1
        except Exception as e:
            print(f"Error navigating to the next page: {e}")
            break
finally:
    driver.quit()

# Fetch token ID and symbol from CoinGecko using API
url_coingecko = "https://api.coingecko.com/api/v3/coins/list"
response_coingecko = requests.get(url_coingecko)
if response_coingecko.status_code == 200:
    coins_list = response_coingecko.json()
    for crypto in cryptos:
        name = crypto[0]
        coin_data = next((coin for coin in coins_list if coin['name'].lower() == name), {"id": "No data", "symbol": "No data"})
        coin_id = coin_data['id']
        coin_symbol = coin_data['symbol']
        crypto.append(coin_id)
        crypto.append(coin_symbol.upper())
        print(f"✅ Assigned ID {coin_id} and symbol {coin_symbol.upper()} for {name}")

        # Fetch additional data from CoinGecko
        if coin_id != "No data":
            url_coin_data = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            response_coin_data = requests.get(url_coin_data)
            if response_coin_data.status_code == 200:
                coin_data = response_coin_data.json()
                total_supply = coin_data.get('market_data', {}).get('total_supply', "Unknown")
                max_supply = coin_data.get('market_data', {}).get('max_supply', "Unknown")
                market_cap = coin_data.get('market_data', {}).get('market_cap', {}).get('usd', "Unknown")
                market_cap_rank = coin_data.get('market_cap_rank', "Unknown")

                # If values are None, set to "Unknown"
                total_supply = total_supply if total_supply is not None else "Unknown"
                max_supply = max_supply if max_supply is not None else "Unknown"
                market_cap = f"{round(market_cap / 1_000_000, 1)}M" if market_cap is not None else "Unknown"
                market_cap_rank = market_cap_rank if market_cap_rank is not None else "Unknown"
            else:
                total_supply = "Unknown"
                max_supply = "Unknown"
                market_cap = "Unknown"
                market_cap_rank = "Unknown"
        else:
            total_supply = "Unknown"
            max_supply = "Unknown"
            market_cap = "Unknown"
            market_cap_rank = "Unknown"

        crypto.extend([total_supply, max_supply, market_cap, market_cap_rank])

else:
    print(f"Error fetching data from CoinGecko: {response_coingecko.status_code}")

# Save the data to a CSV file
try:
    df = pd.DataFrame(cryptos, columns=[
        "Name", "Symbol", "Price", "Volume", "Blockchain", "Added", 
        "Coin ID", "Coin Symbol", "Total Supply", "Max Supply", 
        "Market Cap", "Market Cap Rank"
    ])
    df.to_csv("new_cryptocurrencies.csv", index=False, encoding="utf-8")
    print("✅ Data saved to new_cryptocurrencies.csv")
except Exception as e:
    print(f"❌ Error saving CSV file: {e}")

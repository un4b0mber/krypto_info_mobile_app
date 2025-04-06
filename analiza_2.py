import requests
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from pytrends.request import TrendReq
import re

def clean_name(name):
    return re.sub(r"[^a-zA-Z0-9 ]", "", str(name)).strip()

# Selenium configuration
chrome_options = Options()
chrome_options.add_argument("start-maximized")  # Fullscreen
chrome_options.add_argument("disable-infobars")  # Removes "Chrome is being controlled by automation" bar
chrome_options.add_argument("--disable-popup-blocking")  # Blocks pop-ups
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--no-sandbox")  # Bypasses environment restrictions

# Initialize ChromeDriverManager service (automatically installs and manages ChromeDriver)
chrome_service = Service(ChromeDriverManager().install())

# Initialize WebDriver
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

pytrends = TrendReq(hl='en-US', tz=360)

# Fetch TOP 100 cryptocurrencies from CoinGecko
url_coingecko = "https://api.coingecko.com/api/v3/coins/markets"
params_coingecko = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 200,
    "page": 1
}

response_coingecko = requests.get(url_coingecko, params=params_coingecko)

if response_coingecko.status_code == 200:
    data_coingecko = response_coingecko.json()
    df_coingecko = pd.DataFrame(data_coingecko)
    df_coingecko = df_coingecko[['id', 'symbol', 'market_cap', 'total_volume', 'current_price', 'market_cap_rank']]
    df_coingecko['current_price'] = df_coingecko['current_price'].round(5)
    
    df_coingecko['total_volume'] = (df_coingecko['total_volume'] / 1_000_000).round(1).astype(str) + 'M'
    df_coingecko['market_cap'] = (df_coingecko['market_cap'] / 1_000_000).round(1).astype(str) + 'M'
else:
    print(f"Error fetching data from CoinGecko: {response_coingecko.status_code}")
    exit()

# Fetch all SPOT trading pairs from Binance
url_binance = "https://api.binance.com/api/v3/exchangeInfo"

response_binance = requests.get(url_binance)

if response_binance.status_code == 200:
    data_binance = response_binance.json()
    symbols = data_binance['symbols']

    binance_coins = {s['baseAsset'].lower() for s in symbols}
else:
    print(f"Error fetching data from Binance: {response_binance.status_code}")
    exit()

# Remove cryptocurrencies that are on Binance
df_filtered = df_coingecko[~df_coingecko['symbol'].isin(binance_coins)]

# Sort by price in ascending order
df_filtered = df_filtered.sort_values(by='current_price')

# Remove cryptocurrencies with volume above 80M
df_filtered['total_volume'] = df_filtered['total_volume'].str.replace('M', '').astype(float)
df_filtered = df_filtered[df_filtered['total_volume'] >= 10]

# Remove cryptocurrencies priced above $10
df_filtered = df_filtered[df_filtered['current_price'] <= 10]

df_filtered['total_volume'] = df_filtered['total_volume'].astype(str) + 'M'
df_filtered['current_price'] = '$' + df_filtered['current_price'].astype(str)

# Fetch categories and exchanges (now using Selenium)
categories = []
exchanges = []
blockchains = []
total_supplies = []
max_supplies = []
twitter_followers_list = []
certik_scores_list = []
activity_score = []
active_users_7days = []
trends_data = {}
market_cap_ranks = []
meme_coins = set()

for coin_id in df_filtered['id']:
    driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
    time.sleep(2)  # Reduced sleep time
    
    # Hide cookie banner
    try:
        WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ot-sdk-row"))
        )
        cookie_banner = driver.find_element(By.CSS_SELECTOR, ".ot-sdk-row")
        driver.execute_script("arguments[0].style.display = 'none';", cookie_banner)
        print("Cookie banner hidden!")
    except:
        print("No interfering element found, continuing...")

    button_xpath = "/html/body/div[2]/main/div/div[2]/div[6]/div[5]/div[8]/div[2]/div/div/div[1]/button"

    try:
        button = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.element_to_be_clickable((By.XPATH, button_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", button)  # Scroll to button
        driver.execute_script("arguments[0].click();", button)  # Click using JavaScript
        time.sleep(2)  # Reduced sleep time
        print("Button clicked!")
    except Exception as e:
        print(f"Failed to click button: {e}")
        pass
    
    # Fetch category
    try:
        category_element = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/categories/')]"))
        )
        categories_text = [elem.text for elem in category_element]
        category = ', '.join(categories_text) if categories_text else "No category"

        # Check if the coin is a meme coin
        if "Meme" in categories_text:
            meme_coins.add(coin_id)

        print(f"Category for {coin_id}: {category}")  # DEBUG
    except Exception as e:
        print(f"Error fetching category for {coin_id}: {e}")
        category = "No category"

    categories.append(category)
    
    # Fetch exchange with the highest volume
    url_tickers = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
    response_tickers = requests.get(url_tickers)

    if response_tickers.status_code == 200:
        tickers_data = response_tickers.json().get('tickers', [])
        if tickers_data:
            top_exchange = max(tickers_data, key=lambda x: x.get('volume', 0)).get('market', {}).get('name', 'No data')
        else:
            top_exchange = "No data"
    else:
        top_exchange = "No data" 
        print(f"Error fetching ticker for {coin_id}")
        print(response_tickers.status_code)

    # If exchange not found, try Selenium
    if top_exchange == "No data": 
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time
            exchange_element = driver.find_element(By.XPATH, "//div[@data-coin-show-target='markets']//table/tbody/tr[1]/td[2]")
            top_exchange = exchange_element.text if exchange_element else "No data"
        except:
            top_exchange = "No data"

    exchanges.append(top_exchange)
    time.sleep(1)  # Reduced sleep time

    url_coin_data = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    response_coin_data = requests.get(url_coin_data)

    if response_coin_data.status_code == 200:
        coin_data = response_coin_data.json()
        blockchain_platforms = coin_data.get('platforms', {})
        blockchain = list(blockchain_platforms.keys())[0] if blockchain_platforms else "Unknown"

        total_supply = coin_data.get('market_data', {}).get('total_supply', "Unknown")
        max_supply = coin_data.get('market_data', {}).get('max_supply', "Unknown")

        # If values are None, set to "Unknown"
        total_supply = total_supply if total_supply is not None else "Unknown"
        max_supply = max_supply if max_supply is not None else "Unknown"
    else:
        blockchain = "Unknown"
        total_supply = "Unknown"
        max_supply = "Unknown" 

    # Fallback: If blockchain is "No data", try Selenium
    if not blockchain or blockchain == "Unknown":
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time

            blockchain_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//a[contains(@data-analytics-event, 'select_coin_category')]"))
            )
            blockchain = blockchain_element.text.strip() if blockchain_element.text.strip() else "Unknown"
            print(f"Blockchain for {coin_id} fetched via Selenium: {blockchain}")
        except:
            print(f"Error fetching blockchain for {coin_id}")
            blockchain = "Unknown"

    # Fallback: If total_supply is "No data" or empty string, try Selenium
    if not total_supply or total_supply == "Unknown":
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time

            total_supply_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Total Supply')]]/td"))
            )
            total_supply = total_supply_element.text.strip().replace(",", "") if total_supply_element.text.strip() else "Unknown" 
            print(f"Total Supply for {coin_id} fetched via Selenium: {total_supply}")
        except:
            print(f"Error fetching total_supply for {coin_id}")
            total_supply = "Unknown" 

    # Fallback: If max_supply is "No data", fetch from CoinGecko
    if not max_supply or max_supply == "Unknown":
        try:
            max_supply_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Max Supply')]]/td"))
            )
            max_supply = max_supply_element.text.strip().replace(",", "") if max_supply_element.text.strip() else "Unknown" 
        except:
            max_supply = "Unknown" 

    driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
    time.sleep(2)  # Reduced sleep time

    try:
        cookie_banner = WebDriverWait(driver, 1).until(  # Reduced wait time
            EC.presence_of_element_located((By.ID, "onetrust-close-btn-container"))
        )
        driver.execute_script("arguments[0].click();", cookie_banner)
        time.sleep(1)
        print("✅ Cookie banner closed")
    except:
        print("ℹ️ No cookie banner, continuing...")

    try:
        # Find Twitter button
        twitter_button = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'twitter.com')]"))
        )
        twitter_url = twitter_button.get_attribute("href")
        print(f"🔗 Twitter link: {twitter_url}")  # DEBUG
        
        # Scroll to button to make it visible
        driver.execute_script("arguments[0].scrollIntoView();", twitter_button)
        time.sleep(1)

        # Click button via JavaScript (bypasses block)
        driver.execute_script("arguments[0].click();", twitter_button)
        time.sleep(2)  # Reduced sleep time

        # Switch to new tab (Twitter)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)  # Reduced sleep time
    
        # Fetch followers count
        try:
            followers_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/verified_followers')]/span[1]"))
            )
            followers_count = followers_element.text.strip().replace(",", ".")
            print(f"✅ Followers for {coin_id}: {followers_count}")  # DEBUG
        except Exception as e:
            print(f"❌ Error fetching followers for {coin_id}: {e}")
            followers_count = "No data"

        # Close Twitter tab and return to CoinGecko
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"❌ Error fetching followers for {coin_id}: {e}")
        followers_count = "No data"

    try:
        # 1. Visit CertiK page for the project
        certik_url = f"https://skynet.certik.com/projects/{coin_id}"
        driver.get(certik_url)
        time.sleep(2)  # Reduced sleep time

        # 2. Handle cookie pop-ups (if any)
        try:
            cookie_button = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Agree')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", cookie_button)
            time.sleep(1)
            cookie_button.click()
            print(f"✅ Closed cookie pop-up for {coin_id}")
        except Exception:
            print(f"⚠️ No cookie pop-up for {coin_id}")

        # 3. Scroll to CertiK Skynet Score section
        try:
            score_container = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'relative text-score')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", score_container)
            time.sleep(1)

            # Fetch score consisting of two parts
            score_main = score_container.find_element(By.XPATH, ".//span[contains(@class, 'text-5xl')]").text.strip()
            score_decimal = score_container.find_element(By.XPATH, ".//span[contains(@class, 'text-[2rem]')]").text.strip()

            certik_score = f"{score_main}{score_decimal}"
            print(f"✅ CertiK Skynet Score for {coin_id}: {certik_score}")

            # Fetch rating level (e.g., "High", "Medium", etc.)
            certik_level_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-[20px]')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", certik_level_element)
            time.sleep(1)  # Allow time for loading

            certik_level = certik_level_element.text.strip()

            active_users_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Total Active Users (7d)')]/following::span[1]"))
            )   
            driver.execute_script("arguments[0].scrollIntoView();", active_users_element)
            time.sleep(1)  # Wait for full loading

            active_users = active_users_element.text.strip().replace(",", ".")
        except Exception as e:
            print(f"❌ Error fetching CertiK Skynet Score for {coin_id}: {e}")
            certik_level = "No data"
            certik_score = "No data"
            active_users = "No data"

    except Exception as e:
        print(f"❌ Error accessing CertiK page for {coin_id}: {e}")
        certik_score = "No data"

    coin_name = clean_name(coin_id)

    if not coin_name:
        continue  # Skip empty names

    try:
        print(f"🔍 Checking Google Trends for: {coin_name}")
        pytrends.build_payload([coin_name], timeframe='now 7-d', geo='')  # Last 7 days
        trend = pytrends.interest_over_time()
        
        if not trend.empty:
            trends_data[coin_id] = trend[coin_name].mean()  # Average popularity over 7 days
        else:
            trends_data[coin_id] = 0  # No data

        time.sleep(2)  # Reduced sleep time to avoid Google ban

    except Exception as e:
        print(f"⚠️ Error for {coin_name}: {e}")
        trends_data[coin_id] = 0

    certik_scores_list.append(certik_score)
    activity_score.append(certik_level)
    active_users_7days.append(active_users)
    twitter_followers_list.append(followers_count)
    blockchains.append(blockchain)
    total_supplies.append(total_supply)
    max_supplies.append(max_supply)
    market_cap_ranks.append(df_coingecko.loc[df_coingecko['id'] == coin_id, 'market_cap_rank'].values[0])
    time.sleep(1)  # Reduced sleep time

df_filtered['exchange'] = exchanges
df_filtered['blockchain'] = blockchains
df_filtered['total_supply'] = total_supplies
df_filtered['max_supply'] = max_supplies
df_filtered['twitter_followers'] = twitter_followers_list
df_filtered['certik_score'] = certik_scores_list
df_filtered['activity_score'] = activity_score
df_filtered['total_active_users_7d'] = active_users_7days
df_filtered['google_trends_score'] = df_filtered['id'].map(trends_data)
df_filtered['market_cap_rank'] = market_cap_ranks

df_filtered = df_filtered[~df_filtered['max_supply'].astype(str).isin(['∞', 'inf', 'nan'])]
df_filtered = df_filtered.drop_duplicates()

# Remove cryptocurrencies with Google Trends score below 10, except for meme coins
df_filtered = df_filtered[(df_filtered['google_trends_score'] >= 10) | (df_filtered['id'].isin(meme_coins))]

# Sort by market cap rank in ascending order
df_filtered = df_filtered.sort_values(by='market_cap_rank')

# Create dictionary {category: list of cryptocurrencies}
category_dict = defaultdict(set)

print("File saved! ✅")
df_filtered.to_csv("filtered_top_100_coins.csv", index=False, encoding="utf-8")

time.sleep(5)  # Reduced sleep time
driver.quit()
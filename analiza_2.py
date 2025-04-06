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

# Konfiguracja Selenium
chrome_options = Options()
chrome_options.add_argument("start-maximized")  # Pełny ekran
chrome_options.add_argument("disable-infobars")  # Usuwa pasek "Chrome sterowany przez automatyzację"
chrome_options.add_argument("--disable-popup-blocking")  # Blokuje wyskakujące okienka
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--no-sandbox")  # Pomija ograniczenia środowiskowe

# Inicjalizacja usługi ChromeDriverManager (automatycznie instaluje i zarządza ChromeDriverem)
chrome_service = Service(ChromeDriverManager().install())

# Inicjalizacja WebDrivera
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

pytrends = TrendReq(hl='en-US', tz=360)

# Pobranie TOP 100 kryptowalut z CoinGecko
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
    print(f"Błąd pobierania danych z CoinGecko: {response_coingecko.status_code}")
    exit()

# Pobranie wszystkich par handlowych SPOT z Binance
url_binance = "https://api.binance.com/api/v3/exchangeInfo"

response_binance = requests.get(url_binance)

if response_binance.status_code == 200:
    data_binance = response_binance.json()
    symbols = data_binance['symbols']

    binance_coins = {s['baseAsset'].lower() for s in symbols}
else:
    print(f"Błąd pobierania danych z Binance: {response_binance.status_code}")
    exit()

# Usunięcie kryptowalut, które są na Binance
df_filtered = df_coingecko[~df_coingecko['symbol'].isin(binance_coins)]

# Posortowanie według ceny rosnąco
df_filtered = df_filtered.sort_values(by='current_price')

# Usunięcie kryptowalut z wolumenem powyżej 80M
df_filtered['total_volume'] = df_filtered['total_volume'].str.replace('M', '').astype(float)
df_filtered = df_filtered[df_filtered['total_volume'] >= 10]

# Usunięcie kryptowalut, które kosztują powyżej $10
df_filtered = df_filtered[df_filtered['current_price'] <= 10]

df_filtered['total_volume'] = df_filtered['total_volume'].astype(str) + 'M'
df_filtered['current_price'] = '$' + df_filtered['current_price'].astype(str)

# Pobranie kategorii i giełdy (teraz z Selenium)
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
    
    # Kliknięcie w przycisk (przewinięcie do elementu najpierw)
    try:
        WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ot-sdk-row"))
        )
        cookie_banner = driver.find_element(By.CSS_SELECTOR, ".ot-sdk-row")
        driver.execute_script("arguments[0].style.display = 'none';", cookie_banner)
        print("Cookies banner ukryty – teraz już nic nie przeszkadza!")
    except:
        print("Nie znaleziono przeszkadzającego elementu, kontynuujemy...")

    button_xpath = "/html/body/div[2]/main/div/div[2]/div[6]/div[5]/div[8]/div[2]/div/div/div[1]/button"

    try:
        button = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.element_to_be_clickable((By.XPATH, button_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", button)  # Przewiń do przycisku
        driver.execute_script("arguments[0].click();", button)  # Kliknięcie JavaScript
        time.sleep(2)  # Reduced sleep time
        print("Przycisk kliknięty!")
    except Exception as e:
        print(f"Nie udało się kliknąć przycisku: {e}")
        pass
    
    # Pobranie kategorii
    try:
        category_element = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/categories/')]"))
        )
        categories_text = [elem.text for elem in category_element]
        category = ', '.join(categories_text) if categories_text else "Brak kategorii"

        # Check if the coin is a meme coin
        if "Meme" in categories_text:
            meme_coins.add(coin_id)

        print(f"Kategoria dla {coin_id}: {category}")  # DEBUG
    except Exception as e:
        print(f"Błąd pobierania kategorii dla {coin_id}: {e}")
        category = "Brak kategorii"

    categories.append(category)
    
    # Pobranie giełdy z największym wolumenem
    url_tickers = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
    response_tickers = requests.get(url_tickers)

    if response_tickers.status_code == 200:
        tickers_data = response_tickers.json().get('tickers', [])
        if tickers_data:
            top_exchange = max(tickers_data, key=lambda x: x.get('volume', 0)).get('market', {}).get('name', 'Brak danych')
        else:
            top_exchange = "Brak danych"
    else:
        top_exchange = "Brak danych" 
        print(f"bład pibierania tickera dla {coin_id}")
        print(response_tickers.status_code)

    # Jeśli giełda nie została znaleziona, próbujemy Selenium
    if top_exchange == "Brak danych": 
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time
            exchange_element = driver.find_element(By.XPATH, "//div[@data-coin-show-target='markets']//table/tbody/tr[1]/td[2]")
            top_exchange = exchange_element.text if exchange_element else "Brak danych"
        except:
            top_exchange = "Brak danych"

    exchanges.append(top_exchange)
    time.sleep(1)  # Reduced sleep time

    url_coin_data = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    response_coin_data = requests.get(url_coin_data)

    if response_coin_data.status_code == 200:
        coin_data = response_coin_data.json()
        blockchain_platforms = coin_data.get('platforms', {})
        blockchain = list(blockchain_platforms.keys())[0] if blockchain_platforms else "Nieznane"

        total_supply = coin_data.get('market_data', {}).get('total_supply', "Nieznane")
        max_supply = coin_data.get('market_data', {}).get('max_supply', "Nieznane")

        # Jeśli wartości są None, ustaw "Nieznane"
        total_supply = total_supply if total_supply is not None else "Nieznane"
        max_supply = max_supply if max_supply is not None else "Nieznane"
    else:
        blockchain = "Nieznane"
        total_supply = "Nieznane"
        max_supply = "Nieznane" 

    # Fallback: Jeśli blockchain to "Brak danych", próbujemy Selenium
    if not blockchain or blockchain == "Nieznane":
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time

            blockchain_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//a[contains(@data-analytics-event, 'select_coin_category')]"))
            )
            blockchain = blockchain_element.text.strip() if blockchain_element.text.strip() else "Nieznane"
            print(f"Blockchain dla {coin_id} pobrany przez Selenium: {blockchain}")
        except:
            print(f"Błąd pobierania blockchaina dla {coin_id}")
            blockchain = "Nieznane"

    # Fallback: Jeśli total_supply to "Brak danych" lub pusty string, próbujemy Selenium
    if not total_supply or total_supply == "Nieznane":
        try:
            driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
            time.sleep(1)  # Reduced sleep time

            total_supply_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Total Supply')]]/td"))
            )
            total_supply = total_supply_element.text.strip().replace(",", "") if total_supply_element.text.strip() else "Nieznane" 
            print(f"Total Supply dla {coin_id} pobrane przez Selenium: {total_supply}")
        except:
            print(f"Błąd pobierania total_supply dla {coin_id}")
            total_supply = "Nieznane" 

    # Fallback: Jeśli max_supply to "Brak danych", pobieramy z CoinGecko
    if not max_supply or max_supply == "Nieznane":
        try:
            max_supply_element = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Max Supply')]]/td"))
            )
            max_supply = max_supply_element.text.strip().replace(",", "") if max_supply_element.text.strip() else "Nieznane" 
        except:
            max_supply = "Nieznane" 

    driver.get(f"https://www.coingecko.com/en/coins/{coin_id}")
    time.sleep(2)  # Reduced sleep time

    try:
        cookie_banner = WebDriverWait(driver, 1).until(  # Reduced wait time
            EC.presence_of_element_located((By.ID, "onetrust-close-btn-container"))
        )
        driver.execute_script("arguments[0].click();", cookie_banner)
        time.sleep(1)
        print("✅ Baner cookies zamknięty")
    except:
        print("ℹ️ Brak banera cookies, kontynuujemy...")

    try:
        # Znajdź przycisk Twittera
        twitter_button = WebDriverWait(driver, 2).until(  # Reduced wait time
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'twitter.com')]"))
        )
        twitter_url = twitter_button.get_attribute("href")
        print(f"🔗 Link do Twittera: {twitter_url}")  # DEBUG
        
        # Przewinięcie strony do przycisku, aby był widoczny
        driver.execute_script("arguments[0].scrollIntoView();", twitter_button)
        time.sleep(1)

        # Kliknięcie przycisku przez JavaScript (omija problem blokady)
        driver.execute_script("arguments[0].click();", twitter_button)
        time.sleep(2)  # Reduced sleep time

        # Przełącz się na nową kartę (Twitter)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)  # Reduced sleep time
    
        # Pobierz liczbę followersów
        try:
            followers_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/verified_followers')]/span[1]"))
            )
            followers_count = followers_element.text.strip().replace(",", ".")
            print(f"✅ Followers dla {coin_id}: {followers_count}")  # DEBUG
        except Exception as e:
            print(f"❌ Błąd pobierania followersów dla {coin_id}: {e}")
            followers_count = "Brak danych"

        # Zamknij kartę Twittera i wróć do CoinGecko
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"❌ Błąd pobierania followersów dla {coin_id}: {e}")
        followers_count = "Brak danych"

    try:
        # 1. Wejdź na stronę CertiK dla projektu
        certik_url = f"https://skynet.certik.com/projects/{coin_id}"
        driver.get(certik_url)
        time.sleep(2)  # Reduced sleep time

        # 2. Obsługa okien cookie (jeśli są)
        try:
            cookie_button = WebDriverWait(driver, 2).until(  # Reduced wait time
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Akceptuj') or contains(text(), 'Zgadzam się')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", cookie_button)
            time.sleep(1)
            cookie_button.click()
            print(f"✅ Zamknięto okno cookie dla {coin_id}")
        except Exception:
            print(f"⚠️ Brak okna cookie dla {coin_id}")

        # 3. Przewiń stronę do sekcji CertiK Skynet Score
        try:
            score_container = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'relative text-score')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", score_container)
            time.sleep(1)

            # Pobranie wyniku składającego się z dwóch części
            score_main = score_container.find_element(By.XPATH, ".//span[contains(@class, 'text-5xl')]").text.strip()
            score_decimal = score_container.find_element(By.XPATH, ".//span[contains(@class, 'text-[2rem]')]").text.strip()

            certik_score = f"{score_main}{score_decimal}"
            print(f"✅ CertiK Skynet Score dla {coin_id}: {certik_score}")

            # Pobranie poziomu oceny (np. "High", "Medium", itp.)
            certik_level_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-[20px]')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", certik_level_element)
            time.sleep(1)  # Dajemy czas na załadowanie

            certik_level = certik_level_element.text.strip()

            active_users_element = WebDriverWait(driver, 3).until(  # Reduced wait time
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Total Active Users (7d)')]/following::span[1]"))
            )   
            driver.execute_script("arguments[0].scrollIntoView();", active_users_element)
            time.sleep(1)  # Czekamy na pełne załadowanie

            active_users = active_users_element.text.strip().replace(",", ".")
        except Exception as e:
            print(f"❌ Błąd pobierania CertiK Skynet Score dla {coin_id}: {e}")
            certik_level = "Brak danych"
            certik_score = "Brak danych"
            active_users = "Brak danych"

    except Exception as e:
        print(f"❌ Błąd wejścia na stronę CertiK dla {coin_id}: {e}")
        certik_score = "Brak danych"

    coin_name = clean_name(coin_id)

    if not coin_name:
        continue  # Pomijamy puste nazwy

    try:
        print(f"🔍 Sprawdzam Google Trends dla: {coin_name}")
        pytrends.build_payload([coin_name], timeframe='now 7-d', geo='')  # Ostatnie 7 dni
        trend = pytrends.interest_over_time()
        
        if not trend.empty:
            trends_data[coin_id] = trend[coin_name].mean()  # Średnia popularność z 7 dni
        else:
            trends_data[coin_id] = 0  # Brak danych

        time.sleep(2)  # Reduced sleep time to avoid Google ban

    except Exception as e:
        print(f"⚠️ Błąd dla {coin_name}: {e}")
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

# Usunięcie kryptowalut z wynikiem Google Trends poniżej 10, z wyjątkiem meme coins
df_filtered = df_filtered[(df_filtered['google_trends_score'] >= 10) | (df_filtered['id'].isin(meme_coins))]

# Sortowanie według rankingu rynkowego rosnąco
df_filtered = df_filtered.sort_values(by='market_cap_rank')

# Tworzenie słownika {kategoria: lista kryptowalut}
category_dict = defaultdict(set)

print("Plik zapisany! ✅")
df_filtered.to_csv("filtered_top_100_coins.csv", index=False, encoding="utf-8")

time.sleep(5)  # Reduced sleep time
driver.quit()
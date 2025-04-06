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

# Pobranie wszystkich par handlowych SPOT z Binance
url_binance = "https://api.binance.com/api/v3/exchangeInfo"
response_binance = requests.get(url_binance)

if response_binance.status_code == 200:
    data_binance = response_binance.json()
    symbols = data_binance['symbols']
    binance_symbols = {s['baseAsset'].lower() for s in symbols}
    print("✅ Pobrano dane z Binance")
else:
    print(f"Błąd pobierania danych z Binance: {response_binance.status_code}")
    binance_symbols = set()

def scrape_page():
    print("🔄 Rozpoczynam skanowanie strony...")
    # Czekamy aż tabela się załaduje – timeout ustawiony na 10 sekund
    wait = WebDriverWait(driver, 10)
    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cmc-table")))

    # Pobieramy wiersze tabeli
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
                    print(f"❌ {name} jest na Binance, pomijam...")
                    continue
                try:
                    symbol = row.find_element(By.XPATH, ".//td[3]//p[2]").text.lower()
                except:
                    symbol = "N/A"
                price = row.find_element(By.XPATH, ".//td[4]").text
                blockchain = row.find_element(By.XPATH, ".//td[9]").text
                added = row.find_element(By.XPATH, ".//td[10]").text

                cryptos.append([name, symbol, price, volume_m, blockchain, added])
                print(f"✅ Dodano {name} ({symbol})")
        except Exception as e:
            print(f"Błąd przy pobieraniu danych z wiersza: {e}")

# Ensure the driver quits properly even if an exception occurs
try:
    page_count = 0
    while page_count < 5:
        scrape_page()
        try:
            next_button = driver.find_element(By.XPATH, "//li[@class='next']/a")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            driver.execute_script("arguments[0].click();", next_button)
            print(f"➡️ Przechodzę do strony {page_count + 2}")
            time.sleep(5)  # Wait for the new page to load
            page_count += 1
        except Exception as e:
            print(f"Błąd przy przechodzeniu do następnej strony: {e}")
            break
finally:
    driver.quit()

# Pobranie ID i symbolu tokena z CoinGecko za pomocą API
url_coingecko = "https://api.coingecko.com/api/v3/coins/list"
response_coingecko = requests.get(url_coingecko)
if response_coingecko.status_code == 200:
    coins_list = response_coingecko.json()
    for crypto in cryptos:
        name = crypto[0]
        coin_data = next((coin for coin in coins_list if coin['name'].lower() == name), {"id": "Brak danych", "symbol": "Brak danych"})
        coin_id = coin_data['id']
        coin_symbol = coin_data['symbol']
        crypto.append(coin_id)
        crypto.append(coin_symbol.upper())
        print(f"✅ Przypisano ID {coin_id} i symbol {coin_symbol.upper()} dla {name}")

        # Pobranie dodatkowych danych z CoinGecko
        if coin_id != "Brak danych":
            url_coin_data = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            response_coin_data = requests.get(url_coin_data)
            if response_coin_data.status_code == 200:
                coin_data = response_coin_data.json()
                total_supply = coin_data.get('market_data', {}).get('total_supply', "Nieznane")
                max_supply = coin_data.get('market_data', {}).get('max_supply', "Nieznane")
                market_cap = coin_data.get('market_data', {}).get('market_cap', {}).get('usd', "Nieznane")
                market_cap_rank = coin_data.get('market_cap_rank', "Nieznane")

                # Jeśli wartości są None, ustaw "Nieznane"
                total_supply = total_supply if total_supply is not None else "Nieznane"
                max_supply = max_supply if max_supply is not None else "Nieznane"
                market_cap = f"{round(market_cap / 1_000_000, 1)}M" if market_cap is not None else "Nieznane"
                market_cap_rank = market_cap_rank if market_cap_rank is not None else "Nieznane"
            else:
                total_supply = "Nieznane"
                max_supply = "Nieznane"
                market_cap = "Nieznane"
                market_cap_rank = "Nieznane"
        else:
            total_supply = "Nieznane"
            max_supply = "Nieznane"
            market_cap = "Nieznane"
            market_cap_rank = "Nieznane"

        crypto.extend([total_supply, max_supply, market_cap, market_cap_rank])

        # Fetch Twitter followers and CertiK Skynet Score
        try:
            driver = webdriver.Chrome(service=chrome_service, options=options)
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

           # crypto.append(followers_count)  # Append followers count before extending with other data

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

            except Exception as e:
                print(f"❌ Błąd wejścia na stronę CertiK dla {coin_id}: {e}")
                certik_score = "Brak danych"

            crypto.extend([certik_score, certik_level, active_users])

        except Exception as e:
            print(f"❌ Błąd przy pobieraniu danych z CoinGecko dla {coin_id}: {e}")
            crypto.extend(["Brak danych", "Brak danych", "Brak danych", "Brak danych"])

        finally:
            driver.quit()

else:
    print(f"Błąd pobierania danych z CoinGecko: {response_coingecko.status_code}")

# Save the data to a CSV file
try:
    df = pd.DataFrame(cryptos, columns=[
        "Name", "Symbol", "Price", "Volume", "Blockchain", "Added", 
        "Coin ID", "Coin Symbol", "Total Supply", "Max Supply", 
        "Market Cap", "Market Cap Rank", "Twitter Followers", 
        "CertiK Score", "CertiK Level", "Active Users (7d)"
    ])
    df.to_csv("new_cryptocurrencies.csv", index=False, encoding="utf-8")
    print("✅ Zapisano dane do pliku new_cryptocurrencies.csv")
except Exception as e:
    print(f"❌ Błąd przy zapisywaniu pliku CSV: {e}")

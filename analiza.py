from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
import os

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

accounts = [
    "elonmusk", "saylor", "VitalikButerin", "aantonop", "100trillionUSD", "CryptoKaleo", 
    "WClementeIII", "lopp", "APompliano", "federalreserve", "realDonaldTrump", "binance", 
    "NewYorkFed", "NickTimiraos", "lisaabramowicz1", "biancoresearch", "NorthmanTrader"
]

output_folder = "twitter_screenshots"
os.makedirs(output_folder, exist_ok=True)

# Keywords to filter relevant posts, including meme coins
relevant_keywords = [
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain", "finance", 
    "interest rates", "inflation", "market", "economy", "federal reserve", "monetary policy",
    "doge", "shiba", "inu", "meme", "pepe", "baby", "floki", "elon", "cat", "dog"
]

def is_relevant_post(content):
    """Check if the post content contains any relevant keywords."""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in relevant_keywords)

try:
    driver.get("https://twitter.com/login")
    time.sleep(5)  # Wait for the page to load

    # Log in to Twitter
    username = "@Kamil4466187250"
    password = "Kamil236689"

    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='text']"))
    )
    username_input.send_keys(username)
    driver.find_element(By.XPATH, "//span[text()='Dalej']").click()

    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='password']"))
    )
    password_input.send_keys(password)
    time.sleep(3)
    driver.find_element(By.XPATH, "//span[text()='Zaloguj się']").click()

    time.sleep(5)  # Wait for the login to complete

    for account in accounts:
        driver.get(f"https://twitter.com/{account}?lang=en")
        time.sleep(5)  # Wait for the page to load

        # Close the cookie banner if it appears
        try:
            cookie_banner = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button'][text()='Accept all cookies']"))
            )
            cookie_banner.click()
            print("✅ Baner cookies zamknięty")
        except:
            print("ℹ️ Brak banera cookies, kontynuujemy...")

        # Find the latest 5 tweets, skipping the pinned tweet if it exists
        tweets = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//article[@role='article']"))
        )
        latest_tweet = None
        latest_time = None

        for tweet in tweets[:5]:
            try:
                time_element = tweet.find_element(By.XPATH, ".//time")
                tweet_time = datetime.strptime(time_element.get_attribute("datetime"), "%Y-%m-%dT%H:%M:%S.%fZ")
                tweet_content = tweet.text

                # Filter tweets based on relevance
                if is_relevant_post(tweet_content):
                    if latest_time is None or tweet_time > latest_time:
                        latest_time = tweet_time
                        latest_tweet = tweet
                        print(f"✅ Relevant tweet found: {tweet_content}")
                else:
                    print(f"❌ Irrelevant tweet skipped: {tweet_content}")
            except Exception as e:
                print(f"❌ Błąd przy pobieraniu daty tweeta: {e}")

        if latest_tweet:
            tweet_content = latest_tweet.get_attribute('innerHTML')
            print(f"📝 Najnowszy tweet {account}: {tweet_content}")

            # Scroll to the latest tweet and a bit further down
            driver.execute_script("arguments[0].scrollIntoView(true); window.scrollBy(0, -30);", latest_tweet)
            time.sleep(1)  # Wait for the scroll to complete

            # Take a larger screenshot of the latest tweet
            driver.set_window_size(1280, 1300)
            latest_tweet.screenshot(os.path.join(output_folder, f"{account}_latest_tweet.png"))
            print(f"📸 Zapisano zrzut ekranu najnowszego tweeta {account} jako {account}_latest_tweet.png")

        # Navigate to the "Replies" tab using the provided link
        driver.get(f"https://x.com/{account}/with_replies")
        time.sleep(5)  # Wait for the page to load

        # Find the latest reply to the latest tweet
        latest_reply = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "(//article[@role='article'])[1]"))
        )
        reply_content = latest_reply.get_attribute('innerHTML')

        # Filter replies based on relevance
        if is_relevant_post(reply_content):
            print(f"📝 Najnowsza odpowiedź na tweet {account}: {reply_content}")

            # Scroll to the latest reply and a bit further down
            driver.execute_script("arguments[0].scrollIntoView(true); window.scrollBy(0, -30);", latest_reply)
            time.sleep(1)  # Wait for the scroll to complete

            # Take a larger screenshot of the latest reply
            driver.set_window_size(1280, 1300)
            latest_reply.screenshot(os.path.join(output_folder, f"{account}_latest_reply.png"))
            print(f"📸 Zapisano zrzut ekranu najnowszej odpowiedzi na tweet {account} jako {account}_latest_reply.png")
        else:
            print(f"❌ Irrelevant reply skipped: {reply_content}")

    try:
        # Fetch news about Jerome Powell
        driver.get("https://news.google.com/search?q=Jerome%20Powell")
        time.sleep(5)  # Wait for the page to load

        # Find the two latest news articles
        news_articles = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//article"))
        )[:2]  # Limit to the first two articles

        for i, article in enumerate(news_articles, start=1):
            try:
                # Scroll to the article and click it
                driver.execute_script("arguments[0].scrollIntoView(true);", article)
                time.sleep(1)
                article.click()
                time.sleep(5)  # Wait for the article to load

                # Switch to the new tab
                driver.switch_to.window(driver.window_handles[-1])

                # Extract the text content of the article
                paragraphs = driver.find_elements(By.TAG_NAME, "p")
                article_text = " ".join([p.text for p in paragraphs[:10]])  # Limit to the first 10 paragraphs
                article_text = article_text[:500]  # Limit to 500 characters

                # Save the article text to a file
                with open(os.path.join(output_folder, f"Jerome_Powell_latest_news_{i}.txt"), "w", encoding="utf-8") as file:
                    file.write(article_text)
                print(f"📄 Zapisano tekst najnowszej wiadomości o Jerome Powell jako Jerome_Powell_latest_news_{i}.txt")

                # Close the article tab and switch back to the main tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"❌ Błąd przy pobieraniu wiadomości o Jerome Powell: {e}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"❌ Błąd przy wyszukiwaniu wiadomości o Jerome Powell: {e}")

finally:
    driver.quit()

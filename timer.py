import threading
import time
import subprocess

def run_script(script_path, interval):
    """Run a script at a specified interval."""
    while True:
        try:
            print(f"Running {script_path}...")
            subprocess.run(["python", script_path], check=True)
            print(f"Finished running {script_path}. Waiting {interval} seconds for the next run.")
        except subprocess.CalledProcessError as e:
            print(f"Error while running {script_path}: {e}")
        time.sleep(interval)

# Paths to the scripts
analiza_path = "{YOUR PATH}\\analiza.py"
analiza_2_path = "{YOUR PATH}\\analiza_2.py"
coin_market_path = "{YOUR PATH}\\coin_market.py"

# Intervals in seconds
one_hour = 3600
twenty_four_hours = 86400

# Create threads for each script
thread_analiza = threading.Thread(target=run_script, args=(analiza_path, one_hour), daemon=True)
thread_analiza_2 = threading.Thread(target=run_script, args=(analiza_2_path, twenty_four_hours), daemon=True)
thread_coin_market = threading.Thread(target=run_script, args=(coin_market_path, one_hour), daemon=True)

# Start the threads
thread_analiza.start()
thread_analiza_2.start()
thread_coin_market.start()

# Keep the main thread alive
while True:
    time.sleep(1)

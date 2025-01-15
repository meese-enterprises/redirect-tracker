#!/usr/bin/env python3

import argparse
import csv
import time
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

def setup_driver(chromedriver_path):
    """
    Sets up the Selenium WebDriver with appropriate options.

    Args:
        chromedriver_path (str): Path to the ChromeDriver executable.

    Returns:
        WebDriver: Configured Selenium WebDriver instance.
    """
    chrome_options = Options()
    # Only disable headless mode for debugging
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def fetch_redirect_chain(url, results, lock, chromedriver_path):
    """
    Fetches the redirect chain for a given URL using Selenium and stores unique chains in the shared results dictionary.

    Args:
        url (str): The URL to fetch the redirect chain for.
        results (dict): A thread-safe dictionary to store unique redirect chains.
        lock (threading.Lock): A lock to synchronize access to the results dictionary.
        chromedriver_path (str): Path to the ChromeDriver executable.
    """
    driver = setup_driver(chromedriver_path)
    try:
        driver.get(url)
        redirect_chain = [url]
        current_url = driver.current_url

        while True:
            try:
                # Explicitly wait for potential JavaScript redirection
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return window.location.href") != current_url)
                current_url = driver.execute_script("return window.location.href")
                redirect_chain.append(current_url)
                driver.get(current_url)  # Follow the redirection
            except:
                # No further redirects detected
                break

        # Convert the redirect chain to a tuple (lists are not hashable)
        chain_tuple = tuple(redirect_chain)

        # Acquire lock to ensure thread-safe access to results
        with lock:
            if chain_tuple not in results:
                results[chain_tuple] += 1

    except Exception as e:
        print(f"Error fetching {url}: {e}")
    finally:
        driver.quit()

def main(url, num_threads, output_file, chromedriver_path):
    """
    Main function to initiate multiple threads to fetch redirect chains and save unique results to a CSV file.

    Args:
        url (str): The URL to process.
        num_threads (int): The number of threads to run concurrently.
        output_file (str): The filename to save the unique redirect chains.
        chromedriver_path (str): Path to the ChromeDriver executable.
    """
    results = defaultdict(int)
    lock = threading.Lock()
    threads = []

    for _ in range(num_threads):
        thread = threading.Thread(
          target=fetch_redirect_chain,
          args=(url, results, lock, chromedriver_path),
        )
        thread.start()
        threads.append(thread)
        time.sleep(0.1)  # Slight delay to prevent overwhelming the server

    for thread in threads:
        thread.join()

    # Write unique redirect chains to CSV
    with open(output_file, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Redirect Chain", "Occurrences"])
        for chain, count in results.items():
            csvwriter.writerow([" -> ".join(chain), count])

    print(f"Unique redirect chains have been saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch unique redirect chains from a given URL.")
    parser.add_argument("--url", type=str, required=True, help="The URL to process.")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads to run concurrently.")
    parser.add_argument("--output", type=str, default="redirect_chains.csv", help="Output CSV file name.")
    parser.add_argument("--chromedriver", type=str, required=True, help="Path to the ChromeDriver executable.")
    args = parser.parse_args()

    main(args.url, args.threads, args.output, args.chromedriver)

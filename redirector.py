#!/usr/bin/env python3

import argparse
import csv
from collections import defaultdict
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import logging
import signal
import sys
import os

# Global duplicate count and shutdown flag
duplicate_count = 0
shutdown_flag = False
duplicate_lock = threading.Lock()

# Configure dedicated logger for the script
logger = logging.getLogger("redirector")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def setup_driver(chromedriver_path):
    """
    Sets up the Selenium WebDriver with appropriate options, including a random user agent.

    Args:
        chromedriver_path (str): Path to the ChromeDriver executable.

    Returns:
        WebDriver: Configured Selenium WebDriver instance.
    """
    ua = UserAgent()
    random_user_agent = ua.random

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={random_user_agent}")

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    logger.info(f"Initialized WebDriver with User-Agent: {random_user_agent}")
    return driver


def save_html_for_debugging(driver, current_url, output_dir):
    """
    Saves the HTML content of a site for debugging purposes.

    Args:
        driver (WebDriver): Selenium WebDriver instance.
        current_url (str): URL of the site being saved.
        output_dir (str): Directory to save the HTML file.
    """
    try:
        html_content = driver.page_source
        safe_filename = current_url.replace("://", "_").replace("/", "_")
        file_path = os.path.join(output_dir, f"{safe_filename}.html")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(html_content)
        logger.info(f"Saved HTML content for {current_url} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save HTML for {current_url}: {e}")


def update_csv_file(results, output_file):
    """
    Updates the CSV file with the latest redirect chain data.
    *TODO*: This is inefficient, but I don't know a better way to update the count in real-time.

    Args:
        results (dict): Dictionary containing the redirect chains and their occurrences.
        output_file (str): Path to the output CSV file.
    """
    try:
        with open(output_file, "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(["Redirect Chain", "Occurrences"])
            for chain, count in results.items():
                csvwriter.writerow([" -> ".join(chain), count])
        logger.debug(f"CSV file updated successfully: {output_file}")
    except Exception as e:
        logger.error(f"Failed to update CSV file: {e}")


def fetch_redirect_chain(url, results, lock, chromedriver_path, output_file, output_dir):
    """
    Fetches redirect chains continuously until the duplicate threshold is reached.

    Args:
        url (str): The starting URL.
        results (dict): A thread-safe dictionary to store unique redirect chains.
        lock (threading.Lock): A lock to synchronize access to shared data.
        chromedriver_path (str): Path to the ChromeDriver executable.
        output_file (str): Path to the output CSV file.
        output_dir (str): Directory to save HTML files for debugging.
    """
    global duplicate_count, shutdown_flag

    logger.debug(f"Starting fetch_redirect_chain with URL: {url}")

    while not shutdown_flag:
        driver = setup_driver(chromedriver_path)
        try:
            redirect_chain = []
            current_url = url

            # Validate URL
            if not current_url.startswith("http"):
                logger.error(f"Invalid URL encountered: {current_url}")
                break

            redirect_chain.append(current_url)
            logger.info(f"Visiting: {current_url}")

            try:
                driver.get(current_url)
            except Exception as e:
                logger.error(f"Failed to navigate to {current_url}: {e}")
                break

            while True:
                try:
                    # Wait for the URL to change
                    WebDriverWait(driver, 5).until(lambda d: d.execute_script("return window.location.href") != current_url)
                    current_url = driver.execute_script("return window.location.href")
                    logger.info(f"Redirected to: {current_url}")
                    redirect_chain.append(current_url)
                    driver.get(current_url)
                except:
                    logger.debug("No further redirects detected.")
                    # Save HTML content for debugging, only for the first occurrence
                    chain_tuple = tuple(redirect_chain)
                    with lock:
                        if chain_tuple not in results:
                            save_html_for_debugging(driver, current_url, output_dir)
                    break

            # Convert the redirect chain to a tuple
            chain_tuple = tuple(redirect_chain)

            with lock:
                if chain_tuple in results:
                    results[chain_tuple] += 1
                    logger.debug(f"Incrementing count for chain: {chain_tuple}")
                    update_csv_file(results, output_file)
                    with duplicate_lock:
                        duplicate_count += 1
                else:
                    results[chain_tuple] = 1
                    logger.info(f"Adding new chain: {chain_tuple}")
                    update_csv_file(results, output_file)
                    with duplicate_lock:
                        duplicate_count = 0

            # Stop execution if duplicate count reaches 100
            with duplicate_lock:
                if duplicate_count >= 100:
                    shutdown_flag = True
                    break

        except Exception as e:
            logger.error(f"Exception occurred in fetch_redirect_chain: {e}")
        finally:
            driver.quit()


def signal_handler(sig, frame):
    """
    Handles CTRL+C to gracefully shut down all threads.

    Args:
        sig (int): Signal number.
        frame (FrameType): Current stack frame.
    """
    global shutdown_flag
    logger.info("CTRL+C detected! Shutting down gracefully...")
    shutdown_flag = True


def main(url, num_threads, output_file, chromedriver_path, log_level, output_dir):
    """
    Main function to run multiple threads fetching redirect chains.

    Args:
        url (str): The starting URL.
        num_threads (int): Number of threads to use.
        output_file (str): Output file to save results.
        chromedriver_path (str): Path to the ChromeDriver executable.
        log_level (str): Logging level as a string.
        output_dir (str): Directory to save HTML files for debugging.
    """
    global shutdown_flag

    # Set the logging level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    results = defaultdict(int)
    lock = threading.Lock()
    threads = []

    # Handle CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    # Open the file in append mode and write the header
    with open(output_file, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Redirect Chain", "Occurrences"])

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for _ in range(num_threads):
        thread = threading.Thread(target=fetch_redirect_chain, args=(url, results, lock, chromedriver_path, output_file, output_dir))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    logger.info(f"Unique redirect chains have been saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch unique redirect chains from a given URL.")
    parser.add_argument("--url", type=str, required=True, help="The URL to process.")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads to run concurrently.")
    parser.add_argument("--output", type=str, default="redirect_chains.csv", help="Output CSV file name.")
    parser.add_argument("--chromedriver", type=str, required=True, help="Path to the ChromeDriver executable.")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="OFF", help="Set the logging level (default: OFF).")
    parser.add_argument("--output-dir", type=str, default="html_collection", help="Directory to save HTML files for debugging or further analysis.")
    args = parser.parse_args()

    main(args.url, args.threads, args.output, args.chromedriver, args.log_level, args.output_dir)

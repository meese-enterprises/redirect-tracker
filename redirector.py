#!/usr/bin/env python3

import argparse
import csv
from urllib.parse import urlparse
from collections import defaultdict
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
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


def setup_driver(chromedriver_path, user_agent=None):
    """
    Sets up the Selenium WebDriver with appropriate options, including a random or custom user agent.

    Args:
        chromedriver_path (str): Path to the ChromeDriver executable.
        user_agent (str): Custom user agent string. If None, a random user agent is used.

    Returns:
        WebDriver: Configured Selenium WebDriver instance.
    """
    if not user_agent:
        ua = UserAgent()
        user_agent = ua.random

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
    chrome_options.add_argument(f"--user-agent={user_agent}")

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    logger.info(f"Initialized WebDriver with User-Agent: {user_agent}")
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
        domain = urlparse(current_url).netloc
        file_path = os.path.join(output_dir, f"{domain}.html")
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(html_content)
            logger.info(f"Saved HTML content for {current_url} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save HTML for {current_url}: {e}")


def load_existing_results(output_file):
    """
    Loads existing results from a CSV file to resume tracking.

    Args:
        output_file (str): Path to the output CSV file.

    Returns:
        dict: Dictionary of existing redirect chains and their occurrences.
    """
    results = defaultdict(int)
    if os.path.exists(output_file):
        with open(output_file, "r", newline="") as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader, None)
            for row in csvreader:
                chain = tuple(row[0].split(" -> "))
                count = int(row[1])
                results[chain] = count
        logger.info(f"Loaded {len(results)} chains from {output_file}")
    return results


def fetch_redirect_chain(url, results, lock, chromedriver_path, output_file, output_dir, collect_html, user_agent, wait_time):
    """
    Fetches redirect chains continuously until the duplicate threshold is reached.

    Args:
        url (str): The starting URL.
        results (dict): A thread-safe dictionary to store unique redirect chains.
        lock (threading.Lock): A lock to synchronize access to shared data.
        chromedriver_path (str): Path to the ChromeDriver executable.
        output_file (str): Path to the output CSV file.
        output_dir (str): Directory to save HTML files for debugging.
        collect_html (bool): Whether to save HTML files for debugging.
        user_agent (str): Custom user agent string. If None, a random user agent is used.
        wait_time (int): Time to wait for redirects to complete.
    """
    global duplicate_count, shutdown_flag

    logger.debug(f"Starting fetch_redirect_chain with URL: {url}")

    while not shutdown_flag:
        driver = setup_driver(chromedriver_path, user_agent)
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
                    WebDriverWait(driver, wait_time).until(lambda d: d.execute_script("return window.location.href") != current_url)
                    current_url = driver.execute_script("return window.location.href")
                    logger.info(f"Redirected to: {current_url}")
                    redirect_chain.append(current_url)
                    driver.get(current_url)
                except:
                    logger.debug("No further redirects detected.")
                    # Save HTML content, only for the first occurrence of a domain
                    if collect_html:
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
                    with duplicate_lock:
                        duplicate_count += 1
                else:
                    results[chain_tuple] = 1
                    logger.info(f"Adding new chain: {chain_tuple}")
                    with duplicate_lock:
                        duplicate_count = 0

                # Update CSV file
                with open(output_file, "w", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow(["Redirect Chain", "Occurrences"])
                    for chain, count in results.items():
                        csvwriter.writerow([" -> ".join(chain), count])

                # Stop if 100 duplicate chains are reached
                with duplicate_lock:
                    if duplicate_count >= 100:
                        shutdown_flag = True
                        logger.info("100 duplicate chains observed. Stopping.")
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


def main(url, num_threads, output_file, chromedriver_path, log_level, output_dir, collect_html, user_agent, resume, wait_time):
    """
    Main function to run multiple threads fetching redirect chains.

    Args:
        url (str): The starting URL.
        num_threads (int): Number of threads to use.
        output_file (str): Output file to save results.
        chromedriver_path (str): Path to the ChromeDriver executable.
        log_level (str): Logging level as a string.
        output_dir (str): Directory to save HTML files for debugging.
        collect_html (bool): Whether to save HTML files for debugging.
        user_agent (str): Custom user agent string. If None, a random user agent is used.
        resume (bool): Whether to resume from an existing output file.
        wait_time (int): Time to wait for redirects to complete.
    """
    global shutdown_flag

    # Set the logging level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Load existing results if resuming
    results = load_existing_results(output_file) if resume else defaultdict(int)
    lock = threading.Lock()
    threads = []

    # Handle CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for _ in range(num_threads):
        thread = threading.Thread(target=fetch_redirect_chain, args=(url, results, lock, chromedriver_path, output_file, output_dir, collect_html, user_agent, wait_time))
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
    parser.add_argument("--collect-html", action="store_true", help="Enable saving HTML files for debugging.")
    parser.add_argument("--user-agent", type=str, default=None, help="Custom user agent string. If not set, a random user agent is used on each request.")
    parser.add_argument("--resume", action="store_true", help="Resume from an existing output file.")
    parser.add_argument("--wait-time", type=int, default=5, help="Custom wait time (in seconds) for redirects (default: 5).")
    args = parser.parse_args()

    main(args.url, args.threads, args.output, args.chromedriver, args.log_level, args.output_dir, args.collect_html, args.user_agent, args.resume, args.wait_time)

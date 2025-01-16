#!/usr/bin/env python3

import argparse
import csv
import os
from urllib.parse import urlparse


def load_ignorelist(ignore_file):
    """
    Loads the ignore list from a text file.

    Args:
        ignore_file (str): Path to the ignore list file.

    Returns:
        set: A set of domains to ignore.
    """
    ignorelist = set()
    try:
        with open(ignore_file, "r", encoding="utf-8") as file:
            for line in file:
                domain = line.strip()
                if domain:
                    ignorelist.add(domain)
        print(f"Loaded {len(ignorelist)} domains from ignore list '{ignore_file}'.")
    except FileNotFoundError:
        print(f"Error: Ignore list file '{ignore_file}' not found.")
    except Exception as e:
        print(f"Error reading ignore list file: {e}")
    return ignorelist


def extract_urls(input_csv, output_file, fang, ignore_file):
    """
    Extracts all unique URLs from a CSV file containing redirect chains and saves them to a text file.

    Args:
        input_csv (str): Path to the input CSV file.
        output_file (str): Path to the output text file.
        fang (bool): Whether to "defang" URLs by adding square brackets around the period before the TLD.
        ignore_file (str): Path to the ignore list file. URLs with domains in this list are skipped.
    """
    unique_urls = set()
    ignorelist = set()

    # Load the ignore list if provided
    if ignore_file:
        ignorelist = load_ignorelist(ignore_file)

    # Read the CSV file and extract URLs
    try:
        with open(input_csv, "r", newline="", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile)

            # Skip the header
            next(csvreader, None)

            for row in csvreader:
                if len(row) > 0:
                    chain = row[0].split(" -> ")
                    for url in chain:
                        domain = urlparse(url).netloc
                        if domain not in ignorelist:
                            unique_urls.add(url)
    except FileNotFoundError:
        print(f"Error: File '{input_csv}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Apply "fang" if requested
    if fang:
        unique_urls = {url.replace(".", "[.]") for url in unique_urls}

    # Write unique URLs to the output file
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            for url in sorted(unique_urls):
                outfile.write(url + "\n")
        print(f"Extracted {len(unique_urls)} unique URLs to '{output_file}'.")
    except Exception as e:
        print(f"Error writing to output file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract unique URLs from a CSV file of redirect chains.")
    parser.add_argument("--input", type=str, required=True, help="Path to the input CSV file containing redirect chains.")
    parser.add_argument("--output", type=str, default="unique_urls.txt", help="Path to the output text file. Default is 'unique_urls.txt'.")
    parser.add_argument("--fang", action="store_true", help="Defang URLs by adding square brackets around the period before the TLD.")
    parser.add_argument("--ignore-file", type=str, default="ignorelist.txt", help="Path to a text file containing domains to ignore. Default is 'ignorelist.txt'.")
    args = parser.parse_args()

    # Ensure input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' does not exist.")
    else:
        extract_urls(args.input, args.output, args.fang, args.ignore_file)

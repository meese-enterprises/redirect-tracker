#!/usr/bin/env python3

import argparse
import csv
import os


def extract_urls(input_csv, output_file, fang):
    """
    Extracts all unique URLs from a CSV file containing redirect chains and saves them to a text file.

    Args:
        input_csv (str): Path to the input CSV file.
        output_file (str): Path to the output text file.
        fang (bool): Whether to "defang" URLs by adding square brackets around the period before the TLD.
    """
    unique_urls = set()

    # Read the CSV file and extract URLs
    try:
        with open(input_csv, "r", newline="", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile)

            # Skip the header
            next(csvreader, None)

            for row in csvreader:
                if len(row) > 0:
                    chain = row[0].split(" -> ")
                    unique_urls.update(chain)
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
    args = parser.parse_args()

    # Ensure input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' does not exist.")
    else:
        extract_urls(args.input, args.output, args.fang)

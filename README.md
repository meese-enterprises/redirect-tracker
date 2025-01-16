# Redirect Chain Analyzer

This tool analyzes the redirect chains of a given URL, capturing all unique redirect paths, including those initiated via JavaScript. It utilizes Python's Selenium library to handle JavaScript-based redirects and stores the results in a CSV file.

## Features

- Executes JavaScript to capture client-side redirects.
- Runs multiple threads to explore various redirect paths.
- Stores unique redirect chains in a structured CSV format.
- Supports resuming from an existing CSV file to continue analysis.
- Allows custom user-agent strings for testing, or defaults to random user-agent rotation.
- Saves HTML files of pages for debugging purposes (optional).
- Terminates execution after detecting 100 duplicate redirect chains.
- Allows a custom wait time for redirects to complete.

## Prerequisites

- Python 3.6 or higher
- Google Chrome browser
- ChromeDriver compatible with your Chrome browser version

## Installation

1. **Clone the Repository**:

   ```sh
   git clone https://github.com/meese-enterprises/redirect-tracker.git
   cd redirect-tracker
   ```

2. **Set Up a Virtual Environment** (Optional but recommended):

   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install Required Python Packages**:

   ```sh
   pip3 install -r requirements.txt
   ```

4. **Install ChromeDriver**:

   - **Download the Corresponding ChromeDriver**:

     - Visit the ChromeDriver download page:
       `https://googlechromelabs.github.io/chrome-for-testing/#stable`
     - Download the appropriate driver for your operating system.

   - **Install ChromeDriver**:

     - Extract the downloaded file.
     - Move the `chromedriver` executable to a directory included in your system's `PATH`.
     - Alternatively, specify the path to `chromedriver` directly in the script by modifying the `setup_driver()` function.

   - **Provide the Path to ChromeDriver**:
     - When running the script, specify the path to the ChromeDriver executable using the `--chromedriver` argument.

## Usage

```sh
python3 redirect_follower.py --url <URL> --chromedriver <path_to_chromedriver> [--threads <number_of_threads>] [--output <output_file>]
```

- `--url`: The target URL to analyze. This argument is required.
- `--chromedriver`: The path to the ChromeDriver executable. This argument is required.
- `--threads`: (Optional) Number of concurrent threads to use. Default is 10.
- `--output`: (Optional) Name of the output CSV file. Default is `redirect_chains.csv`.
- `--collect-html`: (Optional) Enable saving HTML files for debugging.
- `--user-agent`: (Optional) Specify a custom user-agent string. Defaults to random user-agent rotation if not set.
- `--resume`: (Optional) Resume tracking from an existing CSV file.
- `--wait-time`: (Optional) Specify the wait time (in seconds) for redirects. Default is 5 seconds.

**Example**:

```sh
python3 redirect_follower.py --url https://example.com --chromedriver ./chromedriver-linux64/chromedriver --threads 10 --output results.csv --collect-html --user-agent "Custom User Agent String" --resume --wait-time 15
```

## Output

The script generates a CSV file with the following columns:

- `Redirect Chain`: A sequence of URLs representing the redirect path, separated by ` -> `.
- `Occurrences`: The number of times each unique redirect chain was encountered.

## Unique URL Extraction

```sh
python3 extract_urls.py --input <input_file> --output <output_file> [--fang]
```

- `--input`: The path to the input CSV file containing redirect chains.
- `--output`: The path to the output text file. Default is `unique_urls.txt`.
- `--fang`: (Optional) Defang URLs by adding square brackets around the period before the TLD.

## Notes

- **Error Handling**: The script handles exceptions during URL fetching and continues processing.
- **Resource Usage**: Be cautious with the number of threads to avoid overwhelming your system or the target server.
- **Legal Considerations**: Ensure you have permission to analyze the target URLs and comply with relevant laws and terms of service.

## License

This project is licensed under the BSD 3-Clause License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Selenium WebDriver](https://www.selenium.dev/documentation/webdriver/getting_started/)
- [ChromeDriver](https://sites.google.com/chromium.org/driver/)

---

For more information, visit the official Selenium documentation:
`https://www.selenium.dev/documentation/webdriver/getting_started/`

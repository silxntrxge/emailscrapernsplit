#tompithsatom/qifshamotrenemail:0.1.0 - works perfectly
#still stable 0.1.1
#still stable 0.2.1/0 good
import sys
import os
import json
import time
import re
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from functools import wraps
import threading
import validators
import random
from urllib.parse import unquote
from collections import Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add this new class definition
class CustomUserAgent:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'
        ]
    
    def random(self):
        return random.choice(self.user_agents)

# Initialize the CustomUserAgent
ua = CustomUserAgent()

app = Flask(__name__)

def get_emails(text, driver):
    # More comprehensive regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    potential_emails = re.findall(email_pattern, text)
    
    # Search for emails in href attributes
    links = driver.find_elements_by_xpath("//a[contains(@href, 'mailto:')]")
    for link in links:
        href = link.get_attribute('href')
        if href.startswith('mailto:'):
            potential_emails.append(unquote(href[7:]))  # Remove 'mailto:' and decode
    
    # Additional validation and filtering
    valid_emails = []
    for email in potential_emails:
        if validators.email(email):
            # Check if it's a Gmail address (modify if you want to include other domains)
            if email.lower().endswith('@gmail.com'):
                valid_emails.append(email.lower())  # Convert to lowercase for consistency
    
    return list(set(valid_emails))  # Remove duplicates

def save_emails(emails, output_file='emails.txt'):
    logger.info(f"Saving {len(emails)} emails to {output_file}...")
    try:
        with open(output_file, 'w') as f:
            for email in emails:
                f.write(email + '\n')
        logger.info("Emails saved successfully.")
    except Exception as e:
        logger.error(f"Error saving emails: {e}")

def send_to_webhook(emails, webhook_url, record_id, zero_result_names):
    logger.info(f"Sending {len(emails)} emails and {len(zero_result_names)} zero-result names to webhook: {webhook_url}")
    try:
        # Remove any potential duplicates and sort the emails
        unique_emails = sorted(set(emails))
        
        # Format the emails as a single comma-separated string
        formatted_emails = ', '.join(unique_emails)
        
        # Format the zero-result names as a single comma-separated string
        formatted_zero_results = ', '.join(zero_result_names)
        
        payload = {
            'emails': formatted_emails,
            'recordId': record_id,
            'zeroResultNames': formatted_zero_results
        }
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logger.info("Emails, recordId, and zero-result names sent to webhook successfully.")
    except Exception as e:
        logger.error(f"Error sending data to webhook: {e}")

def initialize_driver():
    logger.info("Initializing Selenium WebDriver...")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Use the new CustomUserAgent class
        chrome_options.add_argument(f"user-agent={ua.random()}")
        chrome_options.binary_location = "/usr/bin/google-chrome-stable"
        
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logger.error(f"Error initializing WebDriver: {e}")
        sys.exit(1)

def generate_urls(names, domain, niches, num_pages=2):
    logger.info("Generating URLs...")
    urls = []
    for name in names:
        for niche in niches:
            for page in range(0, num_pages):
                start = page * 100
                url = f"https://www.google.com/search?q=%22{name}%22+%22{domain}%22+%22{niche}%22&num=100&start={page}"
                urls.append(url)
    logger.info(f"Generated {len(urls)} URLs.")
    return urls

def scrape_emails_from_url(driver, url, email_counter):
    logger.info(f"Scraping emails from URL: {url}")
    # Set a new random user agent for each request
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua.random()})
    driver.get(url)
    
    # Add a small random delay after loading the page
    time.sleep(random.uniform(1, 3))  # Random delay between 1 and 3 seconds
    
    page_source = driver.page_source
    emails = get_emails(page_source, driver)
    
    # Update the counter with new emails
    for email in emails:
        email_counter[email] += 1
    
    unique_emails = set(emails)
    logger.info(f"Found {len(unique_emails)} unique emails on this page.")
    return unique_emails

def scrape_emails(names, domain, niches, webhook_url=None, record_id=None):
    logger.info("Starting the scraper...")
    driver = initialize_driver()
    
    all_emails = set()
    email_counter = Counter()
    zero_result_names = []
    
    total_combinations = len(names) * len(niches)
    completed_combinations = 0

    for name in names:
        name_has_results = False
        for niche in niches:
            urls = generate_urls([name], domain, [niche])

            for url in urls:
                try:
                    emails = scrape_emails_from_url(driver, url, email_counter)
                    if emails:
                        all_emails.update(emails)
                        name_has_results = True
                    
                    # Implement rate limiting
                    delay = random.uniform(3, 7)  # Random delay between 3 and 7 seconds
                    logger.info(f"Waiting for {delay:.2f} seconds before the next request...")
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Error scraping URL {url}: {e}")
            
            completed_combinations += 1
            progress = (completed_combinations / total_combinations) * 100
            if progress % 20 < (1 / total_combinations) * 100:  # Check if we've crossed a 20% threshold
                logger.info(f"Search progress: {progress:.2f}% completed")
        
        if not name_has_results:
            zero_result_names.append(name)
    
    driver.quit()
    logger.info("WebDriver closed.")
    
    email_list = list(all_emails)
    save_emails(email_list)
    
    if webhook_url:
        send_to_webhook(email_list, webhook_url, record_id, zero_result_names)
    
    logger.info(f"Scraper finished successfully. Total unique emails collected: {len(email_list)}")
    logger.info(f"Names with zero results: {len(zero_result_names)}")
    logger.info("Email frequency:")
    for email, count in email_counter.most_common():
        logger.info(f"{email}: {count} times")
    
    return email_list, zero_result_names

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == os.environ.get('GOOGLE_API_KEY'):
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401
    return decorated

def background_scrape(names_list, domain, niches_list, webhook_url, record_id):
    emails, zero_result_names = scrape_emails(names_list, domain, niches_list, webhook_url, record_id)
    logger.info(f"Background scraping completed. Emails found: {len(emails)}, Names with zero results: {len(zero_result_names)}")

@app.route('/scrape', methods=['POST'])
@require_api_key
def scrape():
    logger.info("Received scrape request")
    data = request.json
    names = data.get('names', '')
    domain = data.get('domain', '')
    niches = data.get('niche', '')
    webhook_url = data.get('webhook', '')
    record_id = data.get('recordId', '')

    logger.info(f"Scrape request parameters: names={names}, domain={domain}, niches={niches}")

    names_list = [name.strip() for name in names.split(',') if name.strip()]
    niches_list = [niche.strip() for niche in niches.split(',') if niche.strip()]

    # Start the scraping process in a background thread
    thread = threading.Thread(target=background_scrape, args=(names_list, domain, niches_list, webhook_url, record_id))
    thread.start()
    
    logger.info(f"Scraping started for record ID: {record_id}")
    return jsonify({'message': 'Scraping started, will be sent to:', 'recordId': record_id}), 200

# Add the following functions from split_processor.py
def split_names(names, group_size=6):
    return [', '.join(names[i:i+group_size]) for i in range(0, len(names), group_size)]

def format_text(text, words_per_line=6):
    words = text.split(', ')
    return ', '.join(words[:words_per_line])

run_counter = 0

def split_and_process(data):
    global run_counter
    run_counter += 1
    
    try:
        names = data['names']
        domain = data['domain']
        niche = data['niche']
        webhook_url = data['webhook']
        
        name_list = names.split(', ')
        name_groups = split_names(name_list)
        
        for group in name_groups:
            formatted_names = format_text(group)
            payload = {
                "names": formatted_names,
                "domain": domain,
                "niche": niche,
                "run_id": str(run_counter)
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
        
        return {"message": "Processing complete", "run_id": run_counter}
    
    except KeyError as e:
        return {"error": f"Missing required field: {str(e)}"}
    except requests.RequestException as e:
        return {"error": f"Error sending to webhook: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def split(data):
    # Your splitting logic here
    # For now, let's just echo back the input data
    return data

@app.route('/split', methods=['POST'])
@require_api_key
def split_route():
    logger.info("Received split request")
    data = request.json
    result = split_and_process(data)
    return jsonify(result), 200

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'split':
        # Handle split request from command line
        input_data = json.loads(sys.stdin.read())
        result = split_and_process(input_data)
        print(json.dumps(result))
    else:
        # Handle scrape request or run as a web server
        logger.info("Starting the Flask application")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
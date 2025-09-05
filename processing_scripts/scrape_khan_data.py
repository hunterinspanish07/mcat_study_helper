#!/usr/bin/env python3
"""
Khan Academy Web Scraper
Automatically scrapes Khan Academy foundation pages and saves HTML content
that can be processed by the existing extract_khan_data.py script.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KhanAcademyScraper:
    """Scrape Khan Academy foundation pages and save HTML content."""
    
    def __init__(self, csv_file: str = "foundation_unit_urls.csv", output_dir: str = "Input", 
                 timeout: int = 30):
        self.csv_file = Path(csv_file)
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.driver = None
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        # Load foundation mappings
        self.foundation_mappings = self._load_foundation_mappings()
        
        # Setup Chrome driver
        self._setup_driver()
        
    def _load_foundation_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load foundation URLs from CSV file."""
        mappings = {}
        
        if not self.csv_file.exists():
            logger.error(f"CSV file {self.csv_file} not found")
            return mappings
            
        try:
            df = pd.read_csv(self.csv_file)
            for _, row in df.iterrows():
                foundation_num = str(row.get('foundation_number', ''))
                mappings[foundation_num] = {
                    'foundation_name': row.get('foundation_name', ''),
                    'foundation_url': row.get('foundation_url', '')
                }
            logger.info(f"Loaded {len(mappings)} foundation mappings from CSV")
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            
        return mappings
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Get the correct chromedriver path
            import os
            import glob
            
            # Find the actual chromedriver binary
            cache_dir = "/home/hhouse/.wdm/drivers/chromedriver/linux64/140.0.7339.80/chromedriver-linux64/"
            actual_driver_path = os.path.join(cache_dir, "chromedriver")
            
            if not os.path.exists(actual_driver_path):
                # Fallback: use ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                if os.path.isfile(driver_path):
                    actual_driver_path = driver_path
                else:
                    # Search for chromedriver binary in the directory
                    search_paths = glob.glob(os.path.join(os.path.dirname(driver_path), "**/chromedriver"), recursive=True)
                    if search_paths:
                        actual_driver_path = search_paths[0]
                    else:
                        raise Exception("Could not find chromedriver binary")
            
            # Make sure it's executable
            os.chmod(actual_driver_path, 0o755)
            logger.info(f"Using ChromeDriver at: {actual_driver_path}")
            
            service = Service(actual_driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def _fetch_page_content(self, foundation_url: str) -> Optional[str]:
        """Fetch page content using Selenium WebDriver."""
        try:
            logger.info(f"Navigating to: {foundation_url}")
            self.driver.get(foundation_url)
            
            # Wait for the page to load and find subtopic elements
            wait = WebDriverWait(self.driver, self.timeout)
            
            # Wait for subtopic containers to be present
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="_qcjzh6"]')))
                logger.info("Page loaded, found subtopic containers")
            except:
                logger.warning("Timeout waiting for subtopic containers, proceeding anyway")
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"Error fetching page {foundation_url}: {e}")
            return None
            
    def _extract_page_content(self, html_content: str) -> Optional[str]:
        """Extract the relevant HTML content from the page."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for subtopic sections that match the pattern in existing files
            subtopic_elements = soup.find_all('div', class_=lambda x: x and '_qcjzh6' in x)
            
            if not subtopic_elements:
                logger.warning("No subtopic containers found with _qcjzh6 class")
                return None
                
            logger.info(f"Found {len(subtopic_elements)} subtopic sections")
            
            # Extract HTML content from all subtopic containers
            html_parts = []
            for element in subtopic_elements:
                try:
                    # Skip "About this unit" sections as per requirements
                    element_html = str(element)
                    if 'about this unit' in element_html.lower():
                        logger.info("Skipping 'About this unit' section")
                        continue
                        
                    # Look for sections that have Learn content
                    learn_sections = element.find_all('ul', class_=lambda x: x and '_37mhyh' in x)
                    if learn_sections:
                        html_parts.append(element_html)
                        logger.debug(f"Added section with {len(learn_sections)} learn lists")
                    else:
                        logger.debug(f"Skipping section without Learn content")
                        
                except Exception as e:
                    logger.warning(f"Error processing element: {e}")
                    continue
                    
            if not html_parts:
                logger.error("No valid content sections found")
                return None
                
            # Combine all HTML parts
            full_content = ''.join(html_parts)
            logger.info(f"Extracted {len(full_content)} characters of HTML content")
            
            return full_content
            
        except Exception as e:
            logger.error(f"Error parsing HTML content: {e}")
            return None
            
    def _save_html_content(self, content: str, foundation_num: str) -> bool:
        """Save HTML content to file."""
        try:
            output_filename = f'resourcehtml_{foundation_num}.txt'
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info(f"Saved content to {output_filename} ({len(content)} characters)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving content for foundation {foundation_num}: {e}")
            return False
            
    def scrape_foundation(self, foundation_num: str, retry_count: int = 3) -> bool:
        """Scrape a single foundation page."""
        if foundation_num not in self.foundation_mappings:
            logger.error(f"Foundation {foundation_num} not found in mappings")
            return False
            
        foundation_info = self.foundation_mappings[foundation_num]
        foundation_url = foundation_info['foundation_url']
        foundation_name = foundation_info['foundation_name']
        
        logger.info(f"Scraping Foundation {foundation_num}: {foundation_name}")
        
        for attempt in range(retry_count):
            try:
                # Fetch the page content using Selenium
                html_content = self._fetch_page_content(foundation_url)
                
                if not html_content:
                    logger.warning(f"Failed to fetch content for foundation {foundation_num}")
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    continue
                
                # Extract the relevant content
                extracted_content = self._extract_page_content(html_content)
                
                if extracted_content:
                    if self._save_html_content(extracted_content, foundation_num):
                        logger.info(f"Successfully scraped foundation {foundation_num}")
                        return True
                    else:
                        logger.error(f"Failed to save content for foundation {foundation_num}")
                        
                logger.warning(f"Attempt {attempt + 1} failed for foundation {foundation_num}")
                
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"Error in attempt {attempt + 1} for foundation {foundation_num}: {e}")
                
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
        logger.error(f"Failed to scrape foundation {foundation_num} after {retry_count} attempts")
        return False
        
    def scrape_foundations(self, foundation_numbers: Optional[List[str]] = None) -> Dict[str, bool]:
        """Scrape multiple foundation pages."""
        if foundation_numbers is None:
            # Default to foundations 3-10 (since 1 and 2 already exist)
            foundation_numbers = [str(i) for i in range(3, 11)]
            
        results = {}
        
        try:
            for foundation_num in foundation_numbers:
                logger.info(f"Starting scrape for foundation {foundation_num}")
                success = self.scrape_foundation(foundation_num)
                results[foundation_num] = success
                
                if success:
                    logger.info(f"✓ Foundation {foundation_num} completed successfully")
                else:
                    logger.error(f"✗ Foundation {foundation_num} failed")
                    
                # Small delay between foundations
                time.sleep(2)
                
        finally:
            # Cleanup
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                    logger.info("WebDriver closed")
                except:
                    pass
                    
        return results
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Scrape Khan Academy foundation pages')
    parser.add_argument('--csv-file', default='foundation_unit_urls.csv', 
                       help='CSV file with foundation mappings')
    parser.add_argument('--output-dir', default='Input', 
                       help='Output directory for HTML files')
    parser.add_argument('--foundations', nargs='+', type=str, 
                       help='Specific foundation numbers to scrape (default: 3-10)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout in seconds for HTTP requests (default: 30)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        with KhanAcademyScraper(
            csv_file=args.csv_file,
            output_dir=args.output_dir,
            timeout=args.timeout
        ) as scraper:
            
            results = scraper.scrape_foundations(args.foundations)
            
            # Print summary
            successful = [f for f, success in results.items() if success]
            failed = [f for f, success in results.items() if not success]
            
            print(f"\n{'='*50}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*50}")
            print(f"Successful: {len(successful)} foundations")
            if successful:
                print(f"  {', '.join(successful)}")
            print(f"Failed: {len(failed)} foundations")
            if failed:
                print(f"  {', '.join(failed)}")
            print(f"{'='*50}")
            
            # Exit with error code if any failed
            if failed:
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
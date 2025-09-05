#!/usr/bin/env python3
"""
Script to add estimated_time field to Khan Academy resource JSON files.

For videos: Extract duration from Khan Academy video pages
For articles: Calculate reading time based on word count (180 WPM)
"""

import json
import time
import re
import logging
import os
import glob
import pickle
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime, timedelta


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('estimated_times.log')
    ]
)
logger = logging.getLogger(__name__)


class EstimatedTimeCalculator:
    """Calculate estimated times for Khan Academy resources."""
    
    def __init__(self, delay: float = 0.5, timeout: int = 10, worker_id: int = 0):
        """
        Initialize calculator.
        
        Args:
            delay: Delay between requests in seconds
            timeout: Timeout for page loading
            worker_id: Unique identifier for this worker instance
        """
        self.delay = delay
        self.timeout = timeout
        self.worker_id = worker_id
        self.driver = None
        self.cache_file = Path(f'.cache_worker_{worker_id}.pkl')
        self.cache = self._load_cache()
        
        # Reading speed: 180 words per minute
        self.words_per_minute = 180
        
        # Thread-safe lock for cache operations
        self._cache_lock = threading.Lock()
        
        # Adaptive timing
        self.request_times = []
        self.failed_requests = 0
        
        # Debug logging files
        self.video_debug_file = Path(f'video_durations_debug_worker_{worker_id}.log')
        self.article_debug_file = Path(f'article_wordcount_debug_worker_{worker_id}.log')
        
        # Initialize debug log files
        self._init_debug_logs()
        
        # Setup WebDriver
        self._setup_driver()
    
    def _init_debug_logs(self):
        """Initialize debug log files with headers."""
        try:
            # Video debug log
            with open(self.video_debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Video Duration Debug Log - Worker {self.worker_id} ===\n")
                f.write(f"Started: {datetime.now()}\n")
                f.write("Format: [TIMESTAMP] RESOURCE_NAME | URL | RAW_HTML_ELEMENT | EXTRACTED_DURATION\n\n")
            
            # Article debug log
            with open(self.article_debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Article Word Count Debug Log - Worker {self.worker_id} ===\n")
                f.write(f"Started: {datetime.now()}\n")
                f.write("Format: [TIMESTAMP] RESOURCE_NAME | URL | SELECTOR_USED | WORD_COUNT | CALCULATED_TIME\n\n")
        except Exception as e:
            logger.warning(f"Could not initialize debug log files: {e}")
    
    def _log_video_debug(self, resource_name: str, url: str, raw_element: str, extracted_duration: str):
        """Log video duration extraction details to debug file."""
        try:
            with open(self.video_debug_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                f.write(f"[{timestamp}] {resource_name} | {url} | {raw_element} | {extracted_duration}\n")
        except Exception as e:
            logger.warning(f"Could not write to video debug log: {e}")
    
    def _log_article_debug(self, resource_name: str, url: str, selector_used: str, word_count: int, calculated_time: str):
        """Log article word count calculation details to debug file."""
        try:
            with open(self.article_debug_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                f.write(f"[{timestamp}] {resource_name} | {url} | {selector_used} | {word_count} | {calculated_time}\n")
        except Exception as e:
            logger.warning(f"Could not write to article debug log: {e}")
    
    def _setup_driver(self):
        """Setup Chrome WebDriver with optimized options for speed."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-images")
            # Removed --disable-javascript to allow article content loading
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--window-size=800,600")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Performance optimizations
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Find the actual chromedriver binary (copied from scrape_khan_data.py)
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
            self.driver.implicitly_wait(2)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def _load_cache(self) -> Dict[str, str]:
        """Load cache from file if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Could not load cache file: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        with self._cache_lock:
            try:
                with open(self.cache_file, 'wb') as f:
                    pickle.dump(self.cache, f)
            except Exception as e:
                logger.warning(f"Could not save cache file: {e}")
    
    def _get_adaptive_delay(self) -> float:
        """Calculate adaptive delay based on recent response times and failures."""
        base_delay = self.delay
        
        # Increase delay if we've had recent failures
        if self.failed_requests > 0:
            failure_penalty = min(self.failed_requests * 0.5, 3.0)
            base_delay += failure_penalty
        
        # Adjust based on recent response times
        if self.request_times:
            avg_response_time = sum(self.request_times[-10:]) / len(self.request_times[-10:])
            if avg_response_time > 5.0:  # If responses are slow, slow down
                base_delay += 0.5
            elif avg_response_time < 2.0:  # If responses are fast, speed up
                base_delay = max(0.1, base_delay - 0.2)
        
        return base_delay
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page using Selenium with caching."""
        # Check cache first
        with self._cache_lock:
            if url in self.cache:
                logger.debug(f"Cache hit for: {url}")
                return BeautifulSoup(self.cache[url], 'html.parser')
        
        start_time = time.time()
        try:
            logger.debug(f"Worker {self.worker_id} fetching: {url}")
            self.driver.get(url)
            
            # Simplified wait strategy for speed
            wait = WebDriverWait(self.driver, min(self.timeout, 8))
            
            try:
                if '/v/' in url:  # Video URL
                    # Wait for video-specific element that contains duration
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="video-time-hidden"]')))
                    except:
                        # Fallback to body if video element doesn't load
                        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                else:  # Article URL
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            except:
                # If wait fails, continue anyway - page might have loaded
                pass
            
            # Additional wait for video pages to ensure video elements are loaded
            if '/v/' in url:
                time.sleep(2.0)  # Longer wait for video elements
            else:
                time.sleep(0.5)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Cache the result
            with self._cache_lock:
                self.cache[url] = str(soup)
                
            # Track successful request time
            response_time = time.time() - start_time
            self.request_times.append(response_time)
            if len(self.request_times) > 20:  # Keep only recent times
                self.request_times = self.request_times[-20:]
            
            self.failed_requests = max(0, self.failed_requests - 1)  # Decrease failure count on success
            
            return soup
            
        except Exception as e:
            response_time = time.time() - start_time
            self.request_times.append(response_time)
            self.failed_requests += 1
            logger.error(f"Worker {self.worker_id} failed to fetch {url}: {e}")
            return None
    
    def extract_video_duration(self, soup: BeautifulSoup, resource_name: str = "Unknown", url: str = "") -> Optional[str]:
        """Extract video duration from Khan Academy video page."""
        try:
            # Primary target: <span data-testid="video-time-hidden">
            video_time_element = soup.find('span', {'data-testid': 'video-time-hidden'})
            if video_time_element:
                text = video_time_element.get_text()
                raw_element = str(video_time_element)
                
                # Fixed regex pattern - no space after colon in "Total duration:10:55"
                match = re.search(r'Total duration:(\d+):(\d+)', text)
                if match:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    total_minutes = minutes + (seconds / 60)
                    duration_str = f"{total_minutes:.1f} minutes"
                    logger.info(f"Found duration in video-time-hidden: {duration_str}")
                    
                    # Log to debug file
                    self._log_video_debug(resource_name, url, raw_element, duration_str)
                    
                    return duration_str
                else:
                    logger.warning(f"Found video-time-hidden element but couldn't parse duration from: '{text}'")
                    self._log_video_debug(resource_name, url, raw_element, "PARSE_FAILED")

            # Look for duration in various possible locations
            duration_patterns = [
                # JSON-LD structured data
                r'"duration":\s*"PT(\d+M)?(\d+S)?"',
                # Video duration in page data
                r'duration["\']:\s*["\']PT(\d+M)?(\d+S)?["\']',
                # Alternative patterns
                r'PT(\d+M)?(\d+S)?'
            ]
            
            page_text = str(soup)
            
            for pattern in duration_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if any(match):  # If any group matched
                        minutes = 0
                        seconds = 0
                        
                        if match[0]:  # Minutes match
                            minutes = int(match[0].replace('M', ''))
                        if match[1]:  # Seconds match
                            seconds = int(match[1].replace('S', ''))
                        
                        total_minutes = minutes + (seconds / 60)
                        duration_str = f"{total_minutes:.1f} minutes"
                        self._log_video_debug(resource_name, url, f"PATTERN_MATCH: {pattern}", duration_str)
                        return duration_str
            
            # Fallback: Look for duration display text
            duration_elements = soup.find_all(['span', 'div'], string=re.compile(r'\d+:\d+'))
            for element in duration_elements:
                duration_text = element.get_text().strip()
                if re.match(r'\d+:\d+', duration_text):
                    parts = duration_text.split(':')
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        total_minutes = minutes + (seconds / 60)
                        duration_str = f"{total_minutes:.1f} minutes"
                        self._log_video_debug(resource_name, url, str(element), duration_str)
                        return duration_str
            
            logger.warning(f"Could not extract video duration from page")
            self._log_video_debug(resource_name, url, "NO_ELEMENT_FOUND", "EXTRACTION_FAILED")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting video duration: {e}")
            return None
    
    def calculate_article_reading_time(self, soup: BeautifulSoup, resource_name: str = "Unknown", url: str = "") -> Optional[str]:
        """Calculate reading time for article based on word count."""
        try:
            # Remove script, style, and other non-content elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Look for main content areas - Khan Academy specific selectors
            content_selectors = [
                '[data-ka-test-id="article-content"]',
                '.article-content',
                '.perseus-article',
                '.perseus-renderer',
                '[data-testid="article-content"]',
                '.main-content',
                'article',
                '.content',
                '[role="main"]',
                '.article-body'
            ]
            
            content_text = ""
            used_selector = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text()
                    used_selector = selector
                    logger.debug(f"Found content using selector: {selector}")
                    break
            
            # If no specific content area found, use body text
            if not content_text:
                body = soup.find('body')
                if body:
                    content_text = body.get_text()
                    used_selector = "body"
                    logger.debug("Using body text as fallback")
            
            # Clean the text better
            import re
            # Remove extra whitespace and normalize
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            
            # Count words more accurately
            words = len([word for word in content_text.split() if word.strip()])
            
            # Higher threshold for meaningful content (Khan Academy articles are substantial)
            if words < 100:
                logger.warning(f"Article appears to have very few words ({words}) using selector '{used_selector}', may not have loaded content properly")
                fallback_time = "5.0 minutes"
                self._log_article_debug(resource_name, url, used_selector or "NONE", words, fallback_time)
                return fallback_time
            
            # Calculate reading time
            reading_time_minutes = words / self.words_per_minute
            
            # Minimum 1 minute, maximum 60 minutes for sanity
            reading_time_minutes = max(1.0, min(60.0, reading_time_minutes))
            
            calculated_time = f"{reading_time_minutes:.1f} minutes"
            logger.info(f"Article word count: {words} (selector: {used_selector}), estimated time: {calculated_time}")
            
            # Log to debug file
            self._log_article_debug(resource_name, url, used_selector or "NONE", words, calculated_time)
            
            return calculated_time
            
        except Exception as e:
            logger.error(f"Error calculating article reading time: {e}")
            fallback_time = "5.0 minutes"
            self._log_article_debug(resource_name, url, "ERROR", 0, fallback_time)
            return fallback_time
    
    def get_estimated_time(self, resource: Dict) -> str:
        """Get estimated time for a resource with adaptive delays."""
        url = resource.get('resource_url', '')
        resource_type = resource.get('resource_type', '')
        resource_name = resource.get('resource_name', 'Unknown')
        
        logger.debug(f"Worker {self.worker_id} processing {resource_type}: {resource_name}")
        
        # Add adaptive delay to be respectful
        adaptive_delay = self._get_adaptive_delay()
        time.sleep(adaptive_delay)
        
        # Fetch the page
        soup = self.fetch_page(url)
        if not soup:
            logger.warning(f"Worker {self.worker_id} failed to fetch page for {resource_name}, using default")
            return "5.0 minutes"  # Default fallback
        
        # Extract estimated time based on resource type
        if resource_type.lower() == 'video':
            estimated_time = self.extract_video_duration(soup, resource_name, url)
        elif resource_type.lower() == 'article':
            estimated_time = self.calculate_article_reading_time(soup, resource_name, url)
        else:
            logger.warning(f"Unknown resource type: {resource_type}")
            estimated_time = "5.0 minutes"
        
        # Use fallback if extraction failed
        if not estimated_time:
            estimated_time = "10.0 minutes" if resource_type.lower() == 'video' else "5.0 minutes"
            logger.warning(f"Using fallback time for {resource_name}: {estimated_time}")
        
        # Periodically save cache
        if len(self.cache) % 10 == 0:
            self._save_cache()
        
        return estimated_time
    
    def cleanup(self):
        """Cleanup WebDriver resources and save cache."""
        # Save cache before cleanup
        self._save_cache()
        
        if self.driver:
            try:
                self.driver.quit()
                logger.debug(f"Worker {self.worker_id} WebDriver closed")
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def merge_debug_logs():
    """Merge debug log files from all workers into consolidated files."""
    try:
        # Merge video debug logs
        video_debug_files = list(Path('.').glob('video_durations_debug_worker_*.log'))
        if video_debug_files:
            with open('video_durations_debug.log', 'w', encoding='utf-8') as merged_file:
                merged_file.write(f"=== Merged Video Duration Debug Log ===\n")
                merged_file.write(f"Merged at: {datetime.now()}\n")
                merged_file.write("Format: [TIMESTAMP] RESOURCE_NAME | URL | RAW_HTML_ELEMENT | EXTRACTED_DURATION\n\n")
                
                for debug_file in video_debug_files:
                    try:
                        with open(debug_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            merged_file.write(f"\n--- From {debug_file.name} ---\n")
                            merged_file.write(content)
                        debug_file.unlink()  # Clean up individual worker file
                        logger.debug(f"Merged and cleaned up {debug_file}")
                    except Exception as e:
                        logger.warning(f"Could not merge {debug_file}: {e}")
        
        # Merge article debug logs
        article_debug_files = list(Path('.').glob('article_wordcount_debug_worker_*.log'))
        if article_debug_files:
            with open('article_wordcount_debug.log', 'w', encoding='utf-8') as merged_file:
                merged_file.write(f"=== Merged Article Word Count Debug Log ===\n")
                merged_file.write(f"Merged at: {datetime.now()}\n")
                merged_file.write("Format: [TIMESTAMP] RESOURCE_NAME | URL | SELECTOR_USED | WORD_COUNT | CALCULATED_TIME\n\n")
                
                for debug_file in article_debug_files:
                    try:
                        with open(debug_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            merged_file.write(f"\n--- From {debug_file.name} ---\n")
                            merged_file.write(content)
                        debug_file.unlink()  # Clean up individual worker file
                        logger.debug(f"Merged and cleaned up {debug_file}")
                    except Exception as e:
                        logger.warning(f"Could not merge {debug_file}: {e}")
        
        if video_debug_files or article_debug_files:
            logger.info("Debug logs merged into video_durations_debug.log and article_wordcount_debug.log")
        
    except Exception as e:
        logger.error(f"Error merging debug logs: {e}")


def process_resource_batch(resources_batch: List[Tuple[int, Dict]], worker_id: int, delay: float, timeout: int) -> List[Tuple[int, str, str]]:
    """
    Process a batch of resources in a single worker.
    
    Returns:
        List of (index, estimated_time, error_message) tuples
    """
    results = []
    
    with EstimatedTimeCalculator(delay=delay, timeout=timeout, worker_id=worker_id) as calculator:
        for idx, resource in resources_batch:
            try:
                estimated_time = calculator.get_estimated_time(resource)
                results.append((idx, estimated_time, None))
                logger.debug(f"Worker {worker_id} processed resource {idx}: {estimated_time}")
            except Exception as e:
                error_msg = str(e)
                results.append((idx, "5.0 minutes", error_msg))
                logger.error(f"Worker {worker_id} failed on resource {idx}: {e}")
    
    return results


def process_json_file(file_path: Path, num_workers: int = 4, delay: float = 0.5, timeout: int = 10, limit: Optional[int] = None) -> Tuple[int, int]:
    """
    Process a JSON file to add estimated times using concurrent workers.
    
    Returns:
        Tuple of (successful_updates, total_resources)
    """
    logger.info(f"Processing file: {file_path} with {num_workers} workers")
    
    # Read existing data
    with open(file_path, 'r', encoding='utf-8') as f:
        resources = json.load(f)
    
    total_resources = len(resources)
    
    # Process only resources with missing or fallback estimated_time values
    resources_to_process = []
    for i, resource in enumerate(resources):
        estimated_time = resource.get('estimated_time')
        
        # Process if: no estimated_time OR estimated_time is a fallback value
        if (not estimated_time or 
            estimated_time == "10.0 minutes" or  # Video fallback
            estimated_time == "5.0 minutes"):    # Article fallback
            resources_to_process.append((i, resource))
    
    if limit:
        resources_to_process = resources_to_process[:limit]
        logger.info(f"Limited to first {limit} resources for testing")
    
    if not resources_to_process:
        logger.info("No resources to process")
        return total_resources, total_resources
    
    logger.info(f"Processing {len(resources_to_process)} resources (only missing or fallback estimated_time values)")
    
    # Split work into batches for workers
    batch_size = max(1, len(resources_to_process) // num_workers)
    batches = []
    for i in range(0, len(resources_to_process), batch_size):
        batch = resources_to_process[i:i + batch_size]
        if batch:  # Only add non-empty batches
            batches.append(batch)
    
    # Limit to actual number of workers needed
    num_workers = min(num_workers, len(batches))
    
    successful_updates = 0  # Count successful updates
    start_time = datetime.now()
    
    logger.info(f"Starting {num_workers} workers to process {len(resources_to_process)} resources")
    
    # Create backup file path
    backup_file_path = file_path.with_suffix('.backup.json')
    
    # Process batches concurrently with incremental saving
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit jobs
        future_to_worker = {}
        for worker_id, batch in enumerate(batches[:num_workers]):
            future = executor.submit(process_resource_batch, batch, worker_id, delay, timeout)
            future_to_worker[future] = worker_id
        
        # Collect results and save incrementally
        processed_count = 0
        batches_completed = 0
        for future in as_completed(future_to_worker):
            worker_id = future_to_worker[future]
            try:
                batch_results = future.result()
                
                # Update resources with results
                batch_success_count = 0
                for idx, estimated_time, error_msg in batch_results:
                    resources[idx]['estimated_time'] = estimated_time
                    if not error_msg:
                        successful_updates += 1
                        batch_success_count += 1
                    processed_count += 1
                
                batches_completed += 1
                
                # Save progress every batch completion (incremental saving)
                try:
                    with open(backup_file_path, 'w', encoding='utf-8') as f:
                        json.dump(resources, f, indent=2, ensure_ascii=False)
                    
                    # After successful backup, update main file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(resources, f, indent=2, ensure_ascii=False)
                        
                    logger.debug(f"Progress saved after worker {worker_id} completion")
                except Exception as save_error:
                    logger.error(f"Failed to save progress: {save_error}")
                
                # Progress update
                elapsed = datetime.now() - start_time
                if len(resources_to_process) > 0:
                    eta = elapsed * (len(resources_to_process) / processed_count - 1) if processed_count > 0 else timedelta(0)
                    logger.info(f"Worker {worker_id} completed ({batch_success_count}/{len(batch_results)} successful). Progress: {processed_count}/{len(resources_to_process)} ({processed_count/len(resources_to_process)*100:.1f}%). ETA: {eta}")
                
            except Exception as e:
                logger.error(f"Worker {worker_id} failed completely: {e}")
                # Set default times for failed batch
                for idx, resource in batches[worker_id]:
                    if 'estimated_time' not in resources[idx]:
                        resources[idx]['estimated_time'] = "5.0 minutes"
                
                # Still save progress even after worker failure
                try:
                    with open(backup_file_path, 'w', encoding='utf-8') as f:
                        json.dump(resources, f, indent=2, ensure_ascii=False)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(resources, f, indent=2, ensure_ascii=False)
                    logger.debug(f"Progress saved after worker {worker_id} failure")
                except Exception as save_error:
                    logger.error(f"Failed to save progress after worker failure: {save_error}")
    
    # Final save (redundant but ensures consistency)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(resources, f, indent=2, ensure_ascii=False)
        
        # Clean up backup file on successful completion
        if backup_file_path.exists():
            backup_file_path.unlink()
            logger.debug(f"Cleaned up backup file: {backup_file_path}")
            
    except Exception as e:
        logger.error(f"Failed final save: {e}")
        logger.info(f"Backup file preserved at: {backup_file_path}")
    
    elapsed = datetime.now() - start_time
    logger.info(f"Successfully updated {successful_updates}/{total_resources} resources in {file_path}. Time taken: {elapsed}")
    
    return successful_updates, total_resources


def main():
    """Main function with concurrent processing."""
    parser = argparse.ArgumentParser(description='Add estimated times to Khan Academy resource files (Optimized)')
    parser.add_argument('--file', type=str, help='Specific JSON file to process (default: all files)')
    parser.add_argument('--limit', type=int, help='Limit number of resources to process (for testing)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for page loading (default: 10)')
    parser.add_argument('--workers', type=int, default=4, help='Number of concurrent workers (default: 4)')
    parser.add_argument('--resume', action='store_true', help='Resume from previous run using cache')
    
    args = parser.parse_args()
    
    logger.info(f"Starting optimized processing with {args.workers} workers")
    logger.info(f"Settings: delay={args.delay}s, timeout={args.timeout}s")
    
    # Determine which files to process
    output_dir = Path('output')
    if args.file:
        files_to_process = [Path(args.file)]
    else:
        files_to_process = list(output_dir.glob('foundation_*_resources.json'))
        files_to_process.sort()
    
    total_successful = 0
    total_resources = 0
    overall_start_time = datetime.now()
    
    try:
        # Process files
        for file_path in files_to_process:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                continue
            
            try:
                successful, total = process_json_file(
                    file_path, 
                    num_workers=args.workers,
                    delay=args.delay, 
                    timeout=args.timeout, 
                    limit=args.limit
                )
                total_successful += successful
                total_resources += total
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        # Cleanup cache files
        cache_files = list(Path('.').glob('.cache_worker_*.pkl'))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                logger.debug(f"Cleaned up cache file: {cache_file}")
            except:
                pass
        
        # Merge debug log files
        merge_debug_logs()
        
        overall_elapsed = datetime.now() - overall_start_time
        logger.info(f"\n=== PROCESSING COMPLETE ===")
        logger.info(f"Successfully updated {total_successful}/{total_resources} total resources")
        logger.info(f"Total time taken: {overall_elapsed}")
        if total_resources > 0:
            rate = total_resources / overall_elapsed.total_seconds()
            logger.info(f"Processing rate: {rate:.2f} resources/second")
        
    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
        logger.info("Cache files preserved for resume capability")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
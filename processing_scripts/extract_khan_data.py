#!/usr/bin/env python3
"""
Khan Academy HTML Data Extractor
Extracts structured learning resources from Khan Academy foundation HTML files.
"""

import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from bs4 import BeautifulSoup, Tag

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KhanAcademyExtractor:
    """Extract structured data from Khan Academy HTML files."""
    
    def __init__(self, input_dir: str = "./Input", output_dir: str = "./output", csv_file: str = "foundation_unit_urls.csv"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.csv_file = Path(csv_file)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        
        # Load foundation mappings
        self.foundation_mappings = self._load_foundation_mappings()

    def _load_foundation_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load foundation name and URL mappings from CSV file."""
        mappings = {}
        
        if not self.csv_file.exists():
            logger.warning(f"CSV file {self.csv_file} not found. Will create placeholder data.")
            return mappings
            
        try:
            df = pd.read_csv(self.csv_file)
            for _, row in df.iterrows():
                # Extract foundation number from filename pattern
                foundation_num = str(row.get('foundation_number', ''))
                mappings[foundation_num] = {
                    'foundation_name': row.get('foundation_name', ''),
                    'foundation_url': row.get('foundation_url', '')
                }
            logger.info(f"Loaded {len(mappings)} foundation mappings from CSV")
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            
        return mappings

    def _extract_foundation_number(self, filename: str) -> str:
        """Extract foundation number from filename like 'resourcehtml_1.txt'."""
        try:
            return filename.split('_')[1].split('.')[0]
        except IndexError:
            logger.warning(f"Could not extract foundation number from {filename}")
            return "unknown"

    def _parse_html_file(self, file_path: Path) -> List[Dict]:
        """Parse a single HTML file and extract resource data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            resources = []
            
            # Find all subtopic sections (h2 with class _4oiy0kp)
            subtopic_headers = soup.find_all('h2', class_='_4oiy0kp')
            
            for header in subtopic_headers:
                try:
                    # Extract subtopic name
                    subtopic_link = header.find('a')
                    if not subtopic_link:
                        continue
                        
                    subtopic_name = subtopic_link.get_text(strip=True)
                    
                    # Skip sections that don't fit our target format
                    if not subtopic_name or subtopic_name.lower() in ['about this unit']:
                        continue
                    
                    # Find the parent container and look for Learn sections
                    parent_section = header.find_parent()
                    while parent_section and not parent_section.find('ul', class_='_37mhyh'):
                        parent_section = parent_section.find_parent()
                    
                    if not parent_section:
                        continue
                    
                    # Find all resource lists under "Learn" sections
                    resource_lists = parent_section.find_all('ul', class_='_37mhyh')
                    
                    for resource_list in resource_lists:
                        # Find all individual resources
                        resource_items = resource_list.find_all('li')
                        
                        for item in resource_items:
                            resource_data = self._extract_resource_data(item, subtopic_name)
                            if resource_data:
                                resources.append(resource_data)
                                
                except Exception as e:
                    logger.warning(f"Error processing subtopic {subtopic_name}: {e}")
                    continue
            
            logger.info(f"Extracted {len(resources)} resources from {file_path.name}")
            return resources
            
        except Exception as e:
            logger.error(f"Error parsing HTML file {file_path}: {e}")
            return []

    def _extract_resource_data(self, item: Tag, subtopic_name: str) -> Optional[Dict]:
        """Extract individual resource data from a list item."""
        try:
            # Find the resource link
            resource_link = item.find('a')
            if not resource_link:
                return None
            
            # Extract resource URL
            href = resource_link.get('href', '')
            if not href:
                return None
                
            resource_url = f"https://www.khanacademy.org{href}" if href.startswith('/') else href
            
            # Extract resource name from span with class _e7vc6cd
            name_span = item.find('span', class_='_e7vc6cd')
            if not name_span:
                return None
                
            resource_name = name_span.get_text(strip=True)
            
            # Determine resource type from aria-label
            resource_type = "Unknown"
            type_spans = item.find_all('span', {'aria-label': ['Article', 'Video']})
            for span in type_spans:
                aria_label = span.get('aria-label', '')
                if aria_label in ['Article', 'Video']:
                    resource_type = aria_label
                    break
            
            return {
                'subtopic_name': subtopic_name,
                'resource_name': resource_name,
                'resource_url': resource_url,
                'resource_type': resource_type
            }
            
        except Exception as e:
            logger.warning(f"Error extracting resource data: {e}")
            return None

    def process_all_files(self) -> None:
        """Process all HTML files in the input directory."""
        if not self.input_dir.exists():
            logger.error(f"Input directory {self.input_dir} does not exist")
            return
        
        # Find all HTML files matching the pattern
        html_files = list(self.input_dir.glob('resourcehtml_*.txt'))
        
        if not html_files:
            logger.warning(f"No HTML files found in {self.input_dir}")
            return
        
        logger.info(f"Found {len(html_files)} HTML files to process")
        
        for html_file in html_files:
            try:
                # Extract foundation number
                foundation_num = self._extract_foundation_number(html_file.name)
                
                # Get foundation info from mappings
                foundation_info = self.foundation_mappings.get(foundation_num, {
                    'foundation_name': f'Foundation {foundation_num}',
                    'foundation_url': ''
                })
                
                # Parse HTML and extract resources
                resources = self._parse_html_file(html_file)
                
                # Add foundation info to each resource
                for resource in resources:
                    resource['foundation_name'] = foundation_info['foundation_name']
                    resource['foundation_url'] = foundation_info['foundation_url']
                
                # Generate output JSON file
                output_filename = f'foundation_{foundation_num}_resources.json'
                output_path = self.output_dir / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(resources, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved {len(resources)} resources to {output_filename}")
                
            except Exception as e:
                logger.error(f"Error processing file {html_file.name}: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Extract Khan Academy resource data from HTML files')
    parser.add_argument('--input-dir', default='./Input', help='Input directory containing HTML files')
    parser.add_argument('--output-dir', default='./output', help='Output directory for JSON files')
    parser.add_argument('--csv-file', default='foundation_unit_urls.csv', help='CSV file with foundation mappings')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create extractor and process files
    extractor = KhanAcademyExtractor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        csv_file=args.csv_file
    )
    
    extractor.process_all_files()


if __name__ == '__main__':
    main()
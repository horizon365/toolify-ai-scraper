# config.py
import argparse
from typing import Dict

# Default configuration
DEFAULT_BASE_URL = "https://www.toolify.ai/ai-tools"
DEFAULT_OUTPUT_FILE = "toolify_scraped.json"

# CSS Selectors for Toolify.ai
SELECTORS = {
    'tool_card': 'div[class*="tool-item"]',
    'name': '.text-base.font-medium, .text-lg.font-medium, h1, h2, h3, h4, div[class*="title"]',
    'description': '.text-sm.text-gray-500, .text-base.text-gray-500, p[class*="description"]',
    'category': '.text-xs.text-gray-400',
    'monthly_traffic': '.text-sm span',
    'rating': '.rating-value',
    'image_url': 'img[src]',
    'pricing_link': 'a[href*="pricing"]',
    'twitter_link': 'a[href*="twitter.com"]',
    'facebook_link': 'a[href*="facebook.com"]',
    'linkedin_link': 'a[href*="linkedin.com"]',
    'features': '.features-list li',
    'pricing_model': '.pricing-model',
    'api_info': '.api-info'
}

# XPath fallbacks for complex selections
XPATH_SELECTORS = {
    "name": "//h2|//h3|//h4",
    "description": "//p",
    "category": "//a[contains(@href, '/category/')]",
    "monthly_traffic": "//span[contains(text(), 'Monthly Visits')]/following-sibling::span",
    "rating": "//span[contains(@class, 'group-hover:text-purple-1300')]",
    "image_url": "//img[@src]",
    "pricing_link": "//a[contains(text(), 'Pricing')]",
    "social_links": {
        "twitter": "//a[contains(@href, 'twitter.com')]",
        "linkedin": "//a[contains(@href, 'linkedin.com')]"
    },
    "support_email": "//a[starts-with(@href, 'mailto:')]",
    "features": "//ul[contains(@class, 'features')]/li",
}

# Required and optional fields for AI tools
REQUIRED_KEYS = [
    "name",
    "description",
    "category",
]

OPTIONAL_KEYS = [
    "features",
    "monthly_traffic",
    "rating",
    "image_url",
    "twitter_link",
    "linkedin_link",
    "support_email",
    "pricing_link",
    "pricing_model",
    "api_available",
    "last_updated",
]

def get_config():
    """Get configuration from command line arguments or use defaults."""
    parser = argparse.ArgumentParser(description='AI Tools Web Crawler')
    parser.add_argument('--url', type=str, default=DEFAULT_BASE_URL,
                      help='Base URL to crawl (default: %(default)s)')
    parser.add_argument('--output', type=str, default=DEFAULT_OUTPUT_FILE,
                      help='Output filename (default: %(default)s)')
    args = parser.parse_args()
    return args

# Initialize configuration
config = get_config()
BASE_URL = config.url
OUTPUT_FILE = config.output

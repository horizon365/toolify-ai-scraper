import asyncio
import json
import os
import logging
from typing import List, Dict, Set
from playwright.async_api import async_playwright
from urllib.parse import urljoin
from utils.category_utils import categorize_tool
from utils.data_utils import get_llm_category, save_to_json, json_to_csv
import argparse

# Configuration
BASE_URL = "https://www.toolify.ai"
CATEGORY_URL = f"{BASE_URL}/category/advertising-assistant"
OUTPUT_FILE = "toolify_ai_tools.json"
CHECKPOINT_FILE = "scrape_checkpoint.json"
SCREENSHOT_DIR = "screenshots"
MAX_RETRIES = 3
DELAY_BETWEEN_TOOLS = 2
PAGE_LOAD_TIMEOUT = 60000
SELECTOR_TIMEOUT = 10000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs('logs', exist_ok=True)


async def get_image_dimensions(img):
    """Get the dimensions of an image element."""
    try:
        dimensions = await img.evaluate('''(el) => {
            const rect = el.getBoundingClientRect();
            const width = rect.width || el.naturalWidth || el.width || 0;
            const height = rect.height || el.naturalHeight || el.height || 0;
            return [Math.max(width, 1), Math.max(height, 1)];  // Ensure non-zero
        }''')
        return dimensions
    except Exception as e:
        print(f"Error getting image dimensions: {e}")
        return [1, 1]  # Default to 1x1 to avoid division by zero


async def take_tool_screenshot(page, tool_name: str) -> Dict[str, str]:
    """Take multiple screenshots of the tool's interface."""
    screenshots = {}
    try:
        # Clean tool name for filename
        clean_name = "".join(c for c in tool_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_').lower()

        # Take full page screenshot
        full_path = os.path.join(SCREENSHOT_DIR, f"{clean_name}_full.png")
        await page.screenshot(
            path=full_path,
            full_page=True
        )
        screenshots['full'] = full_path
        print(f"Saved full page screenshot to {full_path}")

        # Take main content screenshot
        try:
            main_content = await page.query_selector('.tool-detail-information')
            if main_content:
                content_path = os.path.join(SCREENSHOT_DIR, f"{clean_name}_content.png")
                await main_content.screenshot(path=content_path)
                screenshots['content'] = content_path
                print(f"Saved main content screenshot to {content_path}")
        except Exception as e:
            print(f"Error taking content screenshot: {e}")

        # Take features screenshot
        try:
            features_section = await page.query_selector('.features-list')
            if features_section:
                features_path = os.path.join(SCREENSHOT_DIR, f"{clean_name}_features.png")
                await features_section.screenshot(path=features_path)
                screenshots['features'] = features_path
                print(f"Saved features screenshot to {features_path}")
        except Exception as e:
            print(f"Error taking features screenshot: {e}")

        # Take header/hero screenshot
        try:
            hero_section = await page.query_selector('.tool-header')
            if hero_section:
                hero_path = os.path.join(SCREENSHOT_DIR, f"{clean_name}_hero.png")
                await hero_section.screenshot(path=hero_path)
                screenshots['hero'] = hero_path
                print(f"Saved hero screenshot to {hero_path}")
        except Exception as e:
            print(f"Error taking hero screenshot: {e}")

        return screenshots

    except Exception as e:
        print(f"Error taking screenshots: {e}")
        return screenshots


async def retry_with_timeout(func, max_retries=MAX_RETRIES, timeout=PAGE_LOAD_TIMEOUT):
    """Retry an async function with timeout and exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await asyncio.wait_for(func(), timeout=timeout / 1000)
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed after {max_retries} attempts due to timeout")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(f"Error on attempt {attempt + 1}: {e}, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise


async def extract_tool_details(page, url, browser):
    """Extract detailed information about a tool."""
    try:
        # Navigate to tool page with retry
        await retry_with_timeout(
            lambda: page.goto(url, wait_until='networkidle')
        )
        await retry_with_timeout(
            lambda: page.wait_for_selector('.tool-detail-information', timeout=SELECTOR_TIMEOUT)
        )

        tool_data = {}

        # Get name
        name_el = await page.query_selector('h1')
        if name_el:
            tool_data['name'] = (await name_el.text_content()).strip()
            logger.info(f"Extracting details for: {tool_data['name']}")

            # Take screenshots
            screenshots = await take_tool_screenshot(page, tool_data['name'])

            # Convert screenshot paths to URLs
            for screenshot_type, path in screenshots.items():
                if path:
                    url_key = f"{screenshot_type}_screenshot_url"
                    url = f"https://cdn-images.toolify.ai/screenshots/{os.path.basename(path)}"
                    tool_data[url_key] = url
                    logger.info(f"Added {screenshot_type} screenshot URL: {url}")

            # Set main image URL
            if screenshots.get('content'):
                tool_data['img_url'] = tool_data['content_screenshot_url']
            elif screenshots.get('full'):
                tool_data['img_url'] = tool_data['full_screenshot_url']

        # Get meta description and keywords with retry
        meta_desc = await retry_with_timeout(
            lambda: page.query_selector('meta[name="description"]')
        )
        if meta_desc:
            tool_data['meta_description'] = await meta_desc.get_attribute('content')

        # Get description with retry
        description_el = await retry_with_timeout(
            lambda: page.query_selector('.tool-detail-information')
        )
        if description_el:
            description = await description_el.text_content()
            tool_data['full_description'] = description.replace('\n', ' ').replace('  ', ' ').strip()
            logger.info(f"Got description: {len(tool_data['full_description'])} chars")

        # Get features with retry
        features = []
        feature_els = await retry_with_timeout(
            lambda: page.query_selector_all('.features-list li')
        )
        for feature_el in feature_els:
            feature_text = (await feature_el.text_content()).strip()
            if feature_text:
                features.append(feature_text)
        tool_data['features'] = features
        logger.info(f"Got {len(features)} features")

        # Get social links
        social_links = []
        social_els = await page.query_selector_all(
            'a[href*="twitter.com"], a[href*="linkedin.com"], a[href*="facebook.com"], a[href*="instagram.com"]')
        for social_el in social_els:
            href = await social_el.get_attribute('href')
            if href and not 'intent/tweet' in href:
                social_links.append(href)
        tool_data['social_links'] = list(set(social_links))
        logger.info(f"Got {len(social_links)} social links")

        # Get pricing link
        pricing_el = await page.query_selector('a[href*="pricing"]')
        if pricing_el:
            tool_data['pricing_link'] = await pricing_el.get_attribute('href')

        # Try to get the tool website URL for logo
        logger.info(f"Trying to find logo for tool at {url}")
        try:
            website_link = await retry_with_timeout(
                lambda: page.query_selector('a[href^="http"]:has(div.visitWebsite)')
            )
            if website_link:
                tool_website = await website_link.get_attribute('href')
                logger.info(f"Found tool website: {tool_website}")

                if tool_website:
                    # Create a new context for the tool's website
                    context = await browser.new_context(
                        viewport={'width': 1280, 'height': 800},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    )
                    tool_page = await context.new_page()
                    try:
                        await retry_with_timeout(
                            lambda: tool_page.goto(tool_website, wait_until='networkidle')
                        )
                        await tool_page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)

                        # Find logo candidates
                        logo_candidates = []
                        images = await tool_page.query_selector_all('img')
                        for img in images:
                            try:
                                src = await img.get_attribute('src')
                                alt = await img.get_attribute('alt') or ''

                                if not src or src.startswith('data:image/'):
                                    continue

                                # Make URL absolute
                                if src.startswith('//'):
                                    src = f"https:{src}"
                                elif src.startswith('/'):
                                    src = urljoin(tool_website, src)

                                # Calculate logo score
                                logo_score = 0

                                # Check for logo indicators
                                if any(term in src.lower() or term in alt.lower() for term in
                                       ['logo', 'brand', 'icon']):
                                    logo_score += 5

                                # Check for tool name
                                if tool_data['name'].lower() in alt.lower() or tool_data['name'].lower() in src.lower():
                                    logo_score += 8

                                # Get dimensions
                                dimensions = await get_image_dimensions(img)

                                # Logos are usually square-ish
                                if 0.8 <= dimensions[0] / dimensions[1] <= 1.2:
                                    logo_score += 3

                                # Prefer reasonably sized logos
                                if 32 <= min(dimensions) <= 200:
                                    logo_score += 2

                                if logo_score > 5:
                                    logo_candidates.append({
                                        'url': src,
                                        'score': logo_score,
                                        'dimensions': dimensions
                                    })

                            except Exception as e:
                                logger.error(f"Error processing logo image: {e}")
                                continue

                        # Close the context
                        await context.close()

                        # Select best logo
                        if logo_candidates:
                            logo_candidates.sort(
                                key=lambda x: (x['score'], -abs(x['dimensions'][0] - x['dimensions'][1])), reverse=True)
                            best_logo = logo_candidates[0]
                            logger.info(f"Selected best logo: {best_logo['url']} (score: {best_logo['score']})")
                            tool_data['logo_url'] = best_logo['url']

                    except Exception as e:
                        logger.error(f"Error accessing tool website: {e}")
                        if 'context' in locals():
                            await context.close()

        except Exception as e:
            logger.error(f"Error getting tool website: {e}")

        # Only look for fallback logo if we didn't find one from the website
        if not tool_data.get('logo_url'):
            logger.info("Looking for logo on toolify.ai...")

            # Track logo candidates
            logo_candidates = []

            # First try to find logo in the main content area
            try:
                content_area = await page.query_selector('.tool-detail-information')
                if content_area:
                    content_images = await content_area.query_selector_all('img')
                    for img in content_images:
                        try:
                            src = await img.get_attribute('src')
                            alt = await img.get_attribute('alt') or ''

                            if not src or src.startswith('data:image/'):
                                logger.debug(f"Skipping data URL image")
                                continue

                            # Make URL absolute
                            if src.startswith('/'):
                                src = f"https://www.toolify.ai{src}"
                            elif src.startswith('./'):
                                src = f"https://www.toolify.ai{src[1:]}"

                            # Get dimensions
                            dimensions = await get_image_dimensions(img)

                            # Skip tiny images
                            if max(dimensions) < 32:
                                continue

                            # Calculate logo score
                            logo_score = 0
                            if tool_data['name'].lower() in alt.lower() and 'cdn-images.toolify.ai' in src:
                                logo_score = 8
                            if any(term in src.lower() or term in alt.lower() for term in ['logo', 'brand', 'icon']):
                                logo_score += 5
                            if 32 <= min(dimensions) <= 200 and 0.8 <= dimensions[0] / dimensions[1] <= 1.2:
                                logo_score += 3

                            if logo_score > 5:
                                logo_candidates.append({
                                    'url': src,
                                    'score': logo_score,
                                    'dimensions': dimensions
                                })
                                logger.info(f"Added logo candidate: {src} (score: {logo_score})")

                        except Exception as e:
                            logger.error(f"Error processing content image: {e}")
                            continue

            except Exception as e:
                logger.error(f"Error processing content area images: {e}")

            # Select best logo if found
            if logo_candidates:
                logo_candidates.sort(key=lambda x: (x['score'], -abs(x['dimensions'][0] - x['dimensions'][1])),
                                     reverse=True)
                best_logo = logo_candidates[0]
                logger.info(f"Selected best logo: {best_logo['url']} (score: {best_logo['score']})")
                tool_data['logo_url'] = best_logo['url']

        # Categorize the tool
        if tool_data.get('full_description'):
            tool_data['category'] = categorize_tool(tool_data['full_description'])
            logger.info(f"Categorized as: {tool_data['category']}")

        return tool_data

    except Exception as e:
        logger.error(f"Error extracting details: {e}")
        return {}


async def extract_tool_cards(page) -> List[Dict]:
    """Extract basic information from tool cards on the list page."""
    try:
        cards = await page.query_selector_all('.tool-item')
        print(f"\nFound {len(cards)} potential tool cards")

        tools = []
        for i, card in enumerate(cards, 1):
            try:
                print(f"\nProcessing card {i}/{len(cards)}...")

                # Get card HTML for debugging
                card_html = await page.evaluate('(element) => element.outerHTML', card)
                print(f"\nCard HTML structure:\n{card_html}")

                # Extract name
                name_el = await card.query_selector('.go-tool-detail-name')
                if not name_el:
                    continue

                name = await page.evaluate('(el) => el.textContent', name_el)
                name = name.strip() if name else None
                print(f"Found name: {name}")

                # Get tool URL
                link_el = await card.query_selector('a[href^="/tool/"]')
                if not link_el:
                    continue

                tool_url = await page.evaluate('(el) => el.getAttribute("href")', link_el)
                if not tool_url:
                    continue

                # Make URL absolute
                if tool_url.startswith('/'):
                    tool_url = urljoin(BASE_URL, tool_url)

                # Get full details from tool page
                tool_data = await extract_tool_details(page, tool_url, browser)
                if tool_data:
                    tools.append(tool_data)

                # Add delay between requests
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error processing card: {str(e)}")
                continue

        return tools

    except Exception as e:
        print(f"Error extracting tool cards: {str(e)}")
        return []


async def load_all_tools(page) -> List[str]:
    """Load all tools by clicking the 'Load More' button until all content is loaded."""
    tool_urls = set()
    page_num = 1
    total_pages = 23  # Approximate number of pages

    logger.info(f"Loading all tools (approximately {total_pages} pages)...")

    while page_num <= total_pages:
        try:
            logger.info(f"Loading page {page_num}/{total_pages}...")

            # Wait for tool cards with retry
            await retry_with_timeout(
                lambda: page.wait_for_selector('.tool-item', timeout=SELECTOR_TIMEOUT)
            )

            # Get current tool URLs
            cards = await page.query_selector_all('.tool-item')
            for card in cards:
                try:
                    url_el = await card.query_selector('a.go-tool-detail-name')
                    if url_el:
                        href = await url_el.get_attribute('href')
                        if href:
                            full_url = f"https://www.toolify.ai{href}"
                            tool_urls.add(full_url)
                except Exception as e:
                    logger.error(f"Error getting URL from card: {e}")
                    continue

            # Click "Load More" if not on last page
            if page_num < total_pages:
                try:
                    load_more = await page.wait_for_selector(
                        'button.el-button.el-button--default',
                        timeout=SELECTOR_TIMEOUT
                    )
                    if load_more:
                        await load_more.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                    else:
                        logger.warning("Load More button not found")
                        break
                except Exception as e:
                    logger.error(f"Error clicking Load More: {e}")
                    break

            page_num += 1
            logger.info(f"Found {len(tool_urls)} unique tools so far")

        except Exception as e:
            logger.error(f"Error loading page {page_num}: {e}")
            await asyncio.sleep(5)
            continue

    return list(tool_urls)


def save_checkpoint(tools: List[Dict], processed_urls: Set[str]) -> None:
    """Save progress to checkpoint file."""
    checkpoint = {
        'tools': tools,
        'processed_urls': list(processed_urls)
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    logger.info(f"Checkpoint saved: {len(tools)} tools, {len(processed_urls)} processed URLs")


def load_checkpoint() -> tuple[List[Dict], Set[str]]:
    """Load progress from checkpoint file if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
            return checkpoint['tools'], set(checkpoint['processed_urls'])
    return [], set()


async def scrape_tools():
    """Scrape tools from the website and save them to a JSON file."""
    # Load checkpoint if exists
    tools, processed_urls = load_checkpoint()
    if tools:
        logger.info(f"Resuming from checkpoint: {len(tools)} tools already scraped")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Run headless for stability
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        page.set_default_timeout(PAGE_LOAD_TIMEOUT)

        try:
            # Navigate to category page with retry
            await retry_with_timeout(
                lambda: page.goto(CATEGORY_URL, wait_until='networkidle')
            )

            # Collect all tool URLs
            tool_urls = await load_all_tools(page)
            logger.info(f"Collected {len(tool_urls)} unique tool URLs")

            # Filter out already processed URLs
            remaining_urls = [url for url in tool_urls if url not in processed_urls]
            logger.info(f"{len(remaining_urls)} tools remaining to process")

            # Process each URL
            for i, tool_url in enumerate(remaining_urls, 1):
                try:
                    logger.info(f"Processing tool {i}/{len(remaining_urls)}: {tool_url}")

                    # Get tool details with retry
                    details = await retry_with_timeout(
                        lambda: extract_tool_details(page, tool_url, browser)
                    )

                    if details:
                        tools.append(details)
                        processed_urls.add(tool_url)

                        # Save progress
                        logger.info(f"Saving progress to {OUTPUT_FILE}")
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump(tools, f, indent=2)

                        # Save checkpoint every 10 tools
                        if i % 10 == 0:
                            save_checkpoint(tools, processed_urls)

                    # Rate limiting
                    await asyncio.sleep(DELAY_BETWEEN_TOOLS)

                except Exception as e:
                    logger.error(f"Error processing tool: {e}")
                    continue

            logger.info(f"Scraping complete. Saved {len(tools)} tools to {OUTPUT_FILE}")

            # Clean up checkpoint file after successful completion
            if os.path.exists(CHECKPOINT_FILE):
                os.remove(CHECKPOINT_FILE)

            # Convert to CSV
            csv_file_path = OUTPUT_FILE.replace('.json', '.csv')
            json_to_csv(OUTPUT_FILE, csv_file_path)
            logger.info(f"Data has been saved to {OUTPUT_FILE} and {csv_file_path}")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            logger.info("Saving checkpoint before exit...")
            save_checkpoint(tools, processed_urls)

        finally:
            await context.close()
            await browser.close()


async def test_scrape_first_page():
    """Test function to scrape only the first page of tools."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Set viewport and timeout
        await page.set_viewport_size({'width': 1280, 'height': 800})
        page.set_default_timeout(60000)

        # Navigate to the category page
        url = "https://www.toolify.ai/category/advertising-assistant"
        await page.goto(url)

        # Wait for tool cards to be visible
        await page.wait_for_selector('.tool-item', timeout=10000)

        # Get current tool URLs from first page only
        cards = await page.query_selector_all('.tool-item')
        tools = []

        print(f"\nFound {len(cards)} tools on first page")

        # Process first 5 tools only for testing
        for i, card in enumerate(cards[:5]):
            try:
                url_el = await card.query_selector('a.go-tool-detail-name')
                if url_el:
                    href = await url_el.get_attribute('href')
                    if href:
                        full_url = f"https://www.toolify.ai{href}"
                        print(f"\nProcessing tool {i + 1}/5: {full_url}")

                        # Get detailed information
                        details = await extract_tool_details(page, full_url, browser)
                        if details:
                            tools.append(details)
                            print(f"Successfully scraped tool: {details.get('name', 'Unknown')}")
                            print(f"Logo URL: {details.get('logo_url', 'No logo found')}")

            except Exception as e:
                print(f"Error processing tool: {str(e)}")
                continue

        # Save test results
        test_output = 'test_scrape_results.json'
        with open(test_output, 'w') as f:
            json.dump(tools, f, indent=2)
        print(f"\nTest scraping complete. Saved {len(tools)} tools to {test_output}")

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description='Scrape and process AI tools data')
    parser.add_argument('--test', action='store_true', help='Run test scrape of first page only')
    parser.add_argument('--url', type=str, help='URL to scrape', default=CATEGORY_URL)
    parser.add_argument('--output', type=str, help='Output file name', default=OUTPUT_FILE)
    parser.add_argument('--convert', nargs=2, metavar=('JSON_FILE', 'CSV_FILE'),
                        help='Convert JSON file to CSV')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')

    args = parser.parse_args()

    if args.test:
        logger.info("Running test scrape of first page...")
        asyncio.run(test_scrape_first_page())
    elif args.convert:
        json_file, csv_file = args.convert
        logger.info(f"Converting {json_file} to {csv_file}...")
        json_to_csv(json_file, csv_file)
    else:
        logger.info("Starting full scrape...")
        asyncio.run(scrape_tools())


if __name__ == "__main__":
    main()

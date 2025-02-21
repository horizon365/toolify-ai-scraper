import asyncio
import json
import os
from typing import List, Dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin
from utils.category_utils import categorize_tool
from utils.data_utils import get_llm_category

# Configuration
BASE_URL = "https://www.toolify.ai"
CATEGORY_URL = f"{BASE_URL}/category/advertising-assistant"
OUTPUT_FILE = "toolify_ai_tools.json"
CHECKPOINT_FILE = "scrape_checkpoint.json"

async def extract_tool_details(page, url):
    try:
        # Navigate to the detail page and wait for content to load
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_selector('.tool-detail-information', timeout=10000)
        
        # Extract detailed information
        tool_data = {}
        
        # Get name
        name_el = await page.query_selector('h1')
        if name_el:
            tool_data['name'] = await name_el.text_content()
            
        # Get full description
        description_el = await page.query_selector('.tool-detail-information')
        if description_el:
            tool_data['full_description'] = await description_el.text_content()
            
        # Get features
        features = []
        feature_els = await page.query_selector_all('.features-list li')
        for feature_el in feature_els:
            feature_text = await feature_el.text_content()
            features.append(feature_text.strip())
        tool_data['features'] = features
            
        # Get monthly traffic
        traffic_el = await page.query_selector('span[title="Monthly Visits"] + span')
        if traffic_el:
            tool_data['monthly_traffic'] = await traffic_el.text_content()
            
        # Get rating
        rating_el = await page.query_selector('.rating-value')
        if rating_el:
            tool_data['rating'] = await rating_el.text_content()
            
        # Get social links
        social_links = []
        social_els = await page.query_selector_all('a[href*="twitter.com"], a[href*="linkedin.com"]')
        for social_el in social_els:
            href = await social_el.get_attribute('href')
            if href:
                social_links.append(href)
        tool_data['social_links'] = social_links
            
        # Get support email
        email_el = await page.query_selector('a[href^="mailto:"]')
        if email_el:
            href = await email_el.get_attribute('href')
            if href:
                tool_data['support_email'] = href.replace('mailto:', '')
                
        # Get pricing link
        pricing_el = await page.query_selector('a:text("Pricing")')
        if pricing_el:
            href = await pricing_el.get_attribute('href')
            if href:
                tool_data['pricing_link'] = href
                
        # Get image URL
        img_el = await page.query_selector('img[src]')
        if img_el:
            src = await img_el.get_attribute('src')
            if src:
                tool_data['image_url'] = src
                
        # Add default category to be updated by format_tool_data
        if 'name' in tool_data and 'full_description' in tool_data:
            from utils.category_utils import categorize_tool
            tool_data['category'] = categorize_tool(tool_data['name'], tool_data['full_description'])
                
        return tool_data
        
    except Exception as e:
        print(f"Error extracting details: {str(e)}")
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
                tool_data = await extract_tool_details(page, tool_url)
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
    """
    Load all tools by clicking the 'Load More' button until all content is loaded.
    Returns list of tool URLs.
    """
    tool_urls = set()  # Use set to avoid duplicates
    page_num = 1
    total_pages = 2  # Reduced from 23 to 2 for testing
    
    print(f"\nLoading all tools (testing with {total_pages} pages)...")
    
    while page_num <= total_pages:
        try:
            print(f"\nLoading page {page_num}/{total_pages}...")
            
            # Wait for tool cards to be visible
            await page.wait_for_selector('.tool-item', timeout=10000)
            
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
                    print(f"Error getting URL from card: {str(e)}")
                    continue
            
            # Click "Load More" if not on last page
            if page_num < total_pages:
                # Wait for button to be clickable
                load_more = await page.wait_for_selector('button.el-button.el-button--default', timeout=10000)
                if load_more:
                    await load_more.click()
                    # Wait for new content to load
                    await page.wait_for_load_state('networkidle')
                    # Additional delay to ensure content renders
                    await asyncio.sleep(2)
                else:
                    print("Load More button not found")
                    break
            
            page_num += 1
            print(f"Found {len(tool_urls)} unique tools so far")
            
        except Exception as e:
            print(f"Error loading page {page_num}: {str(e)}")
            # Retry current page
            await asyncio.sleep(5)
            continue
    
    return list(tool_urls)

def save_checkpoint(tools: List[Dict], processed_urls: set) -> None:
    """Save progress to checkpoint file."""
    checkpoint = {
        'tools': tools,
        'processed_urls': list(processed_urls)
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"\nCheckpoint saved: {len(tools)} tools, {len(processed_urls)} processed URLs")

def load_checkpoint() -> tuple[List[Dict], set]:
    """Load progress from checkpoint file if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
            return checkpoint['tools'], set(checkpoint['processed_urls'])
    return [], set()

async def scrape_tools():
    """
    Scrape tools from the website and save them to a JSON file.
    """
    # Load checkpoint if exists
    tools, processed_urls = load_checkpoint()
    if tools:
        print(f"\nResuming from checkpoint: {len(tools)} tools already scraped")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Set viewport and timeout
        await page.set_viewport_size({'width': 1280, 'height': 800})
        page.set_default_timeout(60000)
        
        # Navigate to the category page
        url = "https://www.toolify.ai/category/advertising-assistant"
        await page.goto(url)
        
        # First collect all tool URLs
        tool_urls = await load_all_tools(page)
        print(f"\nCollected {len(tool_urls)} unique tool URLs")
        
        # Take only first 10 URLs for testing
        tool_urls = tool_urls[:10]
        print(f"Processing {len(tool_urls)} test URLs")
        
        # Process each URL independently
        try:
            for i, tool_url in enumerate(tool_urls, 1):
                try:
                    print(f"\nProcessing tool {i}/{len(tool_urls)}...")
                    print(f"URL: {tool_url}")
                    
                    # Get detailed information
                    details = await extract_tool_details(page, tool_url)
                    
                    if details:
                        tools.append(details)
                        processed_urls.add(tool_url)
                        
                        # Save after each tool
                        print(f"\nSaving progress to {OUTPUT_FILE}")
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump(tools, f, indent=2)
                        
                    # Add delay between requests
                    await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"Error processing tool: {str(e)}")
                    continue
                    
            print(f"\nScraping complete. Saved {len(tools)} tools to {OUTPUT_FILE}")
                
            # Clean up checkpoint file after successful completion
            if os.path.exists(CHECKPOINT_FILE):
                os.remove(CHECKPOINT_FILE)
                
        except Exception as e:
            print(f"\nError during scraping: {str(e)}")
            print("Saving checkpoint before exit...")
            save_checkpoint(tools, processed_urls)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tools())

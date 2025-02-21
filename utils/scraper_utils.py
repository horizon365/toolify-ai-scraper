import json
import os
import asyncio
from typing import List, Set, Tuple, Dict, Optional

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.venue import Tool
from utils.data_utils import is_complete_tool, is_duplicate_tool
from config import SELECTORS, XPATH_SELECTORS


def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    return BrowserConfig(
        browser_type="chromium",
        headless=False,  # Show browser for debugging
        verbose=True,
    )


def extract_with_fallback(html_element, css_selector: str, xpath_selector: Optional[str] = None) -> str:
    """
    Attempts to extract content using CSS selector with XPath fallback.
    Returns 'N/A' if both methods fail.
    """
    try:
        # Try CSS selector first
        content = html_element.select_one(css_selector)
        if content:
            return content.get_text(strip=True) or 'N/A'
        
        # Try XPath if CSS fails and XPath is provided
        if xpath_selector:
            content = html_element.xpath(xpath_selector)
            if content:
                return ' '.join(content).strip() or 'N/A'
        
        return 'N/A'
    except Exception as e:
        print(f"Extraction error with selector {css_selector}: {str(e)}")
        return 'N/A'


def extract_social_links(html_element, social_selectors: Dict) -> Dict[str, str]:
    """
    Extracts social media links using provided selectors.
    Returns a dictionary with 'N/A' for missing links.
    """
    links = {}
    try:
        container = html_element.select_one(social_selectors['container'])
        
        if container:
            for platform in ['twitter', 'linkedin']:
                link = container.select_one(social_selectors[platform])
                links[f"{platform}_link"] = link.get('href') if link else 'N/A'
        else:
            links = {
                'twitter_link': 'N/A',
                'linkedin_link': 'N/A'
            }
    except Exception as e:
        print(f"Social links extraction error: {str(e)}")
        links = {
            'twitter_link': 'N/A',
            'linkedin_link': 'N/A'
        }
    
    return links


def extract_features(html_element) -> List[str]:
    """
    Extracts features list using CSS selector with XPath fallback.
    Returns empty list if no features found.
    """
    features = []
    try:
        # Try CSS selector first
        elements = html_element.select(SELECTORS['features'])
        if elements:
            features = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
        else:
            # Try XPath fallback
            features = html_element.xpath(XPATH_SELECTORS['features'])
    except Exception as e:
        print(f"Features extraction error: {str(e)}")
    
    return features or []


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Returns the LLM strategy configured for AI tool extraction.
    """
    return LLMExtractionStrategy(
        provider="groq/mixtral-8x7b-32768",  # Using Mixtral model with higher context window
        api_token=os.getenv("GROQ_API_KEY"),
        schema=Tool.model_json_schema(),
        extraction_type="schema",
        instruction=(
            "Extract information about a single AI tool from the provided HTML card. "
            "Focus on extracting these key fields:\n\n"
            "1. name: The tool's name (from the heading)\n"
            "2. description: A brief description of what the tool does\n"
            "3. category: The tool's primary category\n"
            "4. features: List of key features (if present)\n"
            "5. monthly_traffic: Traffic statistics (if shown)\n"
            "6. rating: Numeric rating between 0-5\n"
            "7. image_url: URL to the tool's logo\n"
            "8. social_links: Twitter and LinkedIn URLs\n"
            "9. support_email: Contact email\n"
            "10. pricing_link: Link to pricing page\n"
            "11. pricing_model: Type of pricing\n"
            "12. api_available: Whether an API is available\n"
            "13. last_updated: Last update date\n\n"
            "Rules:\n"
            "- Extract ONLY from the provided card HTML\n"
            "- Use 'N/A' for missing text fields\n"
            "- Use 0.0 for missing numeric fields\n"
            "- Use false for missing boolean fields\n"
            "- Return complete URLs (not relative paths)\n"
            "- Keep descriptions concise\n"
            "- Validate all URLs start with http:// or https://\n"
        ),
        input_format="html",
        verbose=True,
    )


async def extract_tool_data(page, card, selectors):
    try:
        # Get card HTML for debugging
        card_html = await page.evaluate('(element) => element.outerHTML', card)
        print(f"\nCard HTML structure:\n{card_html}")
        
        # Extract name with multiple attempts
        name = None
        name_elements = await card.query_selector_all(selectors['name'])
        for el in name_elements:
            name_text = await page.evaluate('(element) => element.textContent', el)
            if name_text and name_text.strip():
                name = name_text.strip()
                break
                
        print(f"Found name: {name}")

        # Extract description with multiple attempts
        description = None
        desc_elements = await card.query_selector_all(selectors['description'])
        for el in desc_elements:
            desc_text = await page.evaluate('(element) => element.textContent', el)
            if desc_text and desc_text.strip():
                description = desc_text.strip()
                break
                
        print(f"Found description: {description}")

        # Extract link - try both direct href and nested a tags
        link = None
        link_element = await card.query_selector('a[href]')
        if link_element:
            link = await page.evaluate('(element) => element.getAttribute("href")', link_element)
            if link and not link.startswith('http'):
                link = link.strip()
                
        print(f"Found link: {link}")

        # Extract image URL
        image_url = None
        img_element = await card.query_selector('img[src]')
        if img_element:
            image_url = await page.evaluate('(element) => element.getAttribute("src")', img_element)
            if image_url:
                image_url = image_url.strip()
                
        print(f"Found image: {image_url}")

        # Skip if missing essential info
        if not name or not description:
            print("Skipping card - missing name or description\n")
            return None

        # Construct tool data
        tool_data = {
            'name': name,
            'description': description,
            'link': link,
            'image_url': image_url
        }

        print(f"Successfully extracted: {name}\n")
        return tool_data

    except Exception as e:
        print(f"Error extracting tool data: {str(e)}\n")
        return None


async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    """
    Checks if the page has no results.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        url (str): The URL to check.
        session_id (str): The session identifier.

    Returns:
        bool: True if no results found, False otherwise.
    """
    try:
        # Create a new page with longer timeout
        page = await crawler.browser.new_page()
        await page.set_default_timeout(30000)
        
        # Navigate and wait for content
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector("div.grid", timeout=20000)
        
        # Check for tool cards
        cards = await page.query_selector_all("div.grid > div")
        if not cards:
            print("No tool cards found on the page")
            return True
            
        # Check for specific no results message
        no_results = await page.query_selector("text='No Results Found'")
        return bool(no_results)
        
    except Exception as e:
        print(f"Error checking for no results: {str(e)}")
        return True
        
    finally:
        if page:
            await page.close()


async def process_tool_card(
    crawler: AsyncWebCrawler,
    card_html: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
) -> Optional[Dict]:
    """Process a single tool card with rate limit handling."""
    try:
        # Clean up the HTML to reduce size
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(card_html, 'html.parser')
        
        # Remove unnecessary elements that might bloat the content
        for element in soup.find_all(['script', 'style', 'iframe', 'noscript']):
            element.decompose()
        
        # Get just the essential card content
        cleaned_html = str(soup)
        
        # Extract data using LLM with the cleaned HTML
        result = await crawler.arun(
            html_content=cleaned_html,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                session_id=session_id,
            ),
        )

        if not result.success:
            print("Failed to process card")
            return None

        if not result.extracted_content:
            print("No content extracted from card")
            return None

        # Parse the extracted content
        try:
            tool_data = json.loads(result.extracted_content)
            if isinstance(tool_data, list) and len(tool_data) > 0:
                tool_data = tool_data[0]  # Take first item if list returned
            return tool_data
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {str(e)}")
            return None

    except Exception as e:
        print(f"Error processing tool card: {str(e)}")
        return None


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of AI tools.
    """
    url = f"{base_url}/page/{page_number}" if page_number > 1 else base_url
    print(f"Loading page {page_number}...")

    page = None
    try:
        # Create a new page with longer timeout
        page = await crawler.browser.new_page()
        await page.set_default_timeout(30000)
        
        # Navigate and wait for content
        await page.goto(url, wait_until="networkidle")
        
        # Wait for the grid to load
        try:
            await page.wait_for_selector("div.grid", timeout=20000)
        except Exception as e:
            print(f"Grid not found, trying alternative selectors: {str(e)}")
        
        # Get page content after JavaScript execution
        content = await page.content()
        
        # Parse HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        print("\nPage HTML structure:")
        print(soup.prettify()[:2000])
        
        # Try different approaches to find tool cards
        print("\nTrying different selectors...")
        
        # Method 1: Look for tool links
        tool_links = soup.find_all('a', href=lambda x: x and '/ai-tools/' in x)
        if tool_links:
            print(f"Found {len(tool_links)} tool links")
            
        # Method 2: Look for grid items
        grid_items = soup.select("div.grid > div")
        if grid_items:
            print(f"Found {len(grid_items)} grid items")
            
        # Method 3: Look for headings
        headings = soup.find_all(['h2', 'h3', 'h4'])
        if headings:
            print(f"Found {len(headings)} headings")
        
        # Process tools from the most promising source
        tools = []
        processed = set()
        
        # Try processing grid items first
        if grid_items:
            for item in grid_items:
                try:
                    # Extract basic info
                    name_el = item.find(['h2', 'h3', 'h4'])
                    name = name_el.get_text(strip=True) if name_el else None
                    
                    if not name or name in processed:
                        continue
                        
                    desc_el = item.find('p')
                    description = desc_el.get_text(strip=True) if desc_el else 'N/A'
                    
                    link_el = item.find('a', href=lambda x: x and '/ai-tools/' in x)
                    tool_link = link_el.get('href', '') if link_el else ''
                    
                    if not tool_link:
                        continue
                    
                    # Build basic tool data
                    tool_data = {
                        'name': name,
                        'description': description,
                        'category': 'Advertising Assistant',
                        'monthly_traffic': 'N/A',
                        'rating': 0.0,
                        'image_url': 'N/A',
                        'pricing_link': f"https://www.toolify.ai{tool_link}",
                        'social_links': [],
                        'support_email': 'N/A'
                    }
                    
                    # Try to enhance with LLM
                    try:
                        llm_data = await process_tool_card(
                            crawler=crawler,
                            card_html=str(item),
                            llm_strategy=llm_strategy,
                            session_id=session_id
                        )
                        if llm_data:
                            tool_data.update(llm_data)
                    except Exception as e:
                        print(f"Error enhancing with LLM: {str(e)}")
                    
                    # Add if complete
                    if is_complete_tool(tool_data, required_keys):
                        tools.append(tool_data)
                        processed.add(name)
                        print(f"\nExtracted tool: {name}")
                    
                except Exception as e:
                    print(f"Error processing grid item: {str(e)}")
                    continue
                    
                await asyncio.sleep(1)  # Rate limiting
        
        # If no tools found from grid items, try tool links
        if not tools and tool_links:
            for link in tool_links:
                try:
                    name = link.get_text(strip=True)
                    if not name or name in processed:
                        continue
                        
                    parent = link.find_parent(['div', 'article'])
                    if not parent:
                        continue
                        
                    desc_el = parent.find('p')
                    description = desc_el.get_text(strip=True) if desc_el else 'N/A'
                    
                    tool_data = {
                        'name': name,
                        'description': description,
                        'category': 'Advertising Assistant',
                        'monthly_traffic': 'N/A',
                        'rating': 0.0,
                        'image_url': 'N/A',
                        'pricing_link': f"https://www.toolify.ai{link.get('href')}",
                        'social_links': [],
                        'support_email': 'N/A'
                    }
                    
                    # Try to enhance with LLM
                    try:
                        llm_data = await process_tool_card(
                            crawler=crawler,
                            card_html=str(parent),
                            llm_strategy=llm_strategy,
                            session_id=session_id
                        )
                        if llm_data:
                            tool_data.update(llm_data)
                    except Exception as e:
                        print(f"Error enhancing with LLM: {str(e)}")
                    
                    # Add if complete
                    if is_complete_tool(tool_data, required_keys):
                        tools.append(tool_data)
                        processed.add(name)
                        print(f"\nExtracted tool: {name}")
                    
                except Exception as e:
                    print(f"Error processing tool link: {str(e)}")
                    continue
                    
                await asyncio.sleep(1)  # Rate limiting
        
        return tools, len(tools) == 0
        
    except Exception as e:
        print(f"Error processing page {page_number}: {str(e)}")
        return [], False
        
    finally:
        if page:
            await page.close()

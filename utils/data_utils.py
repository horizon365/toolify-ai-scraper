import json
from typing import List, Dict, Any
import os
from crawl4ai import LLMExtractionStrategy
import re
import pandas as pd

from config import OUTPUT_FILE
from utils.category_utils import categorize_tool, get_all_categories

DEFAULT_VALUES = {
    "image_url": "/2.9.4/img/logo.f3a91ce.png",
    "support_email": "business@toolify.ai"
}

# Initialize LLM strategy for categorization
CATEGORIZATION_PROMPT = """
You are an expert at categorizing AI marketing tools. Analyze the AI tool's name and detailed description, then categorize it into exactly ONE of these categories. Focus on the tool's primary function and core value proposition:

Marketing & Advertising
- Ad campaign management, PPC, media buying, display ads
- Examples: Ad campaign managers, PPC optimization tools, ad creative tools
- Core functions: Campaign management, ad optimization, targeting

Social Media Marketing
- Social media management, scheduling, analytics, engagement
- Examples: Social media managers, scheduling tools, analytics platforms
- Core functions: Content scheduling, engagement tracking, social analytics

Content Marketing
- Content creation, blog writing, copywriting, content strategy
- Examples: AI writers, content generators, blog post creators
- Core functions: Content generation, writing assistance, content planning

Email Marketing
- Email automation, newsletters, campaign management
- Examples: Email automation tools, newsletter platforms, sequence builders
- Core functions: Email campaigns, automation, deliverability

SEO Tools
- Keyword research, rank tracking, backlink analysis
- Examples: SEO analyzers, rank trackers, site auditors
- Core functions: SEO optimization, keyword tracking, site analysis

Analytics & Insights
- Marketing analytics, performance tracking, ROI measurement
- Examples: Analytics dashboards, attribution tools, reporting platforms
- Core functions: Data analysis, reporting, performance tracking

Marketing Automation
- Workflow automation, CRM integration, lead nurturing
- Examples: Marketing automation platforms, CRM tools, workflow builders
- Core functions: Process automation, lead management, integration

Visual Marketing
- Marketing video/image creation, ad creative design
- Examples: Video creators, image generators, design tools
- Core functions: Visual content creation, ad creative design

Tool to categorize:
Name: {name}
Full Description: {description}

Respond with ONLY the category name from the list above that best matches the tool's PRIMARY function. Choose the category that aligns with the tool's main value proposition, not secondary features."""

def is_duplicate_tool(tool_name: str, seen_names: set) -> bool:
    """Check if a tool has already been processed."""
    return tool_name in seen_names


def is_complete_tool(tool: dict, required_keys: list) -> bool:
    """Check if a tool has all required fields."""
    return all(key in tool for key in required_keys)


def is_default_value(field: str, value: str) -> bool:
    """Check if a field contains a default/placeholder value."""
    return value == DEFAULT_VALUES.get(field, "")


def clean_tool_data(tool_data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate tool data to remove/handle default values."""
    cleaned_data = {}  # Start with empty dict instead of copying
    
    # Copy only the fields we want to keep
    fields_to_keep = [
        "name", "full_description", "description", "features",
        "social_links", "support_email", "pricing_link", "image_url",
        "category"  # Ensure category is in fields to keep
    ]
    
    for field in fields_to_keep:
        if field in tool_data:
            value = tool_data[field]
            # Clean description fields
            if field in ["full_description", "description"] and value:
                # Remove Q1 A1 Q2 A2 placeholders
                value = re.sub(r'\s+Q\d+\s+A\d+\s+', ' ', value)
                # Clean up FAQ section
                value = re.sub(r'FAQ from.*?\n', '\nFrequently Asked Questions:\n', value)
            
            # Don't copy default values except for category
            if field in DEFAULT_VALUES and field != "category" and value == DEFAULT_VALUES[field]:
                cleaned_data[field] = ""
            else:
                cleaned_data[field] = value
    
    # Ensure features and social_links are lists
    if "features" not in cleaned_data:
        cleaned_data["features"] = []
    if "social_links" not in cleaned_data:
        cleaned_data["social_links"] = []
        
    # Clean up social links if they exist
    if cleaned_data["social_links"]:
        cleaned_data["social_links"] = [
            link for link in cleaned_data["social_links"] 
            if isinstance(link, str) and (link.startswith("http://") or link.startswith("https://"))
        ]
    
    # Ensure category is present
    if "category" not in cleaned_data:
        if "name" in cleaned_data and ("full_description" in cleaned_data or "description" in cleaned_data):
            from utils.category_utils import categorize_tool
            description = cleaned_data.get("full_description", "") or cleaned_data.get("description", "")
            cleaned_data["category"] = categorize_tool(cleaned_data["name"], description)
        else:
            cleaned_data["category"] = "Other"
    
    return cleaned_data


def consolidate_categories(categories: List[str]) -> List[str]:
    """
    Clean and consolidate categories by removing duplicates and mapping to standardized categories.
    """
    # Our standardized categories
    VALID_CATEGORIES = {
        "Marketing & Advertising",
        "Social Media Marketing",
        "Content Marketing",
        "Email Marketing",
        "SEO Tools",
        "Analytics & Insights",
        "Marketing Automation",
        "Visual Marketing",
        "Other"
    }
    
    # Category mapping to consolidate similar/overlapping categories
    CATEGORY_MAPPING = {
        # Marketing & Advertising
        "Digital Advertising": "Marketing & Advertising",
        "PPC Tools": "Marketing & Advertising",
        "Ad Management": "Marketing & Advertising",
        "Display Advertising": "Marketing & Advertising",
        
        # Social Media Marketing
        "Social Media Management": "Social Media Marketing",
        "Social Media Analytics": "Social Media Marketing",
        "Social Media Automation": "Social Media Marketing",
        "Social Media Scheduling": "Social Media Marketing",
        
        # Content Marketing
        "Content Creation": "Content Marketing",
        "Content Writing": "Content Marketing",
        "Blog Writing": "Content Marketing",
        "Copywriting": "Content Marketing",
        "Content Strategy": "Content Marketing",
        
        # Email Marketing
        "Email Automation": "Email Marketing",
        "Newsletter Tools": "Email Marketing",
        "Email Campaign": "Email Marketing",
        "Email Marketing Platform": "Email Marketing",
        
        # SEO Tools
        "SEO Software": "SEO Tools",
        "Keyword Research": "SEO Tools",
        "Rank Tracking": "SEO Tools",
        "SEO Analytics": "SEO Tools",
        
        # Analytics & Insights
        "Marketing Analytics": "Analytics & Insights",
        "Performance Analytics": "Analytics & Insights",
        "Marketing Metrics": "Analytics & Insights",
        "Data Analytics": "Analytics & Insights",
        
        # Marketing Automation
        "Workflow Automation": "Marketing Automation",
        "CRM Tools": "Marketing Automation",
        "Lead Management": "Marketing Automation",
        "Marketing Workflow": "Marketing Automation",
        
        # Visual Marketing
        "Video Marketing": "Visual Marketing",
        "Image Creation": "Visual Marketing",
        "Design Tools": "Visual Marketing",
        "Visual Content": "Visual Marketing"
    }
    
    # Clean categories
    cleaned = set()  # Use set to automatically remove duplicates
    
    for category in categories:
        # First check if it's already a valid category
        if category in VALID_CATEGORIES:
            cleaned.add(category)
            continue
            
        # Try to map to a standardized category
        mapped_category = CATEGORY_MAPPING.get(category, "Other")
        if mapped_category in VALID_CATEGORIES:
            cleaned.add(mapped_category)
    
    return sorted(list(cleaned))  # Convert back to sorted list


def get_llm_category(name: str, description: str) -> str:
    """Use LLM to categorize a tool based on name and description."""
    VALID_CATEGORIES = {
        "Marketing & Advertising",
        "Social Media Marketing",
        "Content Marketing",
        "Email Marketing",
        "SEO Tools",
        "Analytics & Insights",
        "Marketing Automation",
        "Visual Marketing",
        "Other"
    }
    
    print(f"\nCategorizing tool: {name}")
    print(f"Description: {description[:200]}...")
    
    try:
        # First try keyword-based categorization
        keyword_category = categorize_tool(name, description)
        print(f"Keyword-based category: {keyword_category}")
        
        if keyword_category != "Other":
            print("Using keyword-based category")
            return keyword_category
            
        print("No strong keyword matches, trying LLM categorization...")
        
        # Format the input for the LLM
        input_text = f"""Tool Name: {name}
Description: {description[:1000]}

Based on the above information, categorize this tool into exactly ONE of these categories:
- Marketing & Advertising (ad campaigns, PPC, media buying)
- Social Media Marketing (social media management, scheduling)
- Content Marketing (content creation, blog writing, copywriting)
- Email Marketing (email automation, newsletters)
- SEO Tools (keyword research, rank tracking)
- Analytics & Insights (marketing analytics, performance tracking)
- Marketing Automation (workflow automation, CRM)
- Visual Marketing (video/image creation, ad creative design)

Respond with ONLY the category name, nothing else."""

        # Initialize LLM
        llm_strategy = LLMExtractionStrategy(
            provider="groq/mixtral-8x7b-32768",
            api_token=os.getenv("GROQ_API_KEY"),
            instruction=input_text,
            extraction_type="text",
            verbose=True
        )
        
        # Get LLM response
        print("Sending request to LLM...")
        result = llm_strategy.extract(
            text=input_text,
            html=None,
            ix=0
        )
        
        print(f"LLM response: {result}")
        
        # Clean and validate the result
        if result:
            result = result.strip()
            
            # First check if it's already a valid category
            if result in VALID_CATEGORIES:
                print(f"Using LLM category: {result}")
                return result
                
            # Handle common variations
            result = result.replace("Marketing and Advertising", "Marketing & Advertising")
            result = result.replace("Content and Media", "Content & Media")
            result = result.replace("Analytics and Scheduling", "Analytics & Scheduling")
            result = result.replace("Image and Graphics", "Image & Graphics")
            
            # Ensure AI prefix if missing
            if not result.startswith("AI ") and result != "Development Tools" and result != "Other":
                result = "AI " + result
            
            # Final validation
            if result in VALID_CATEGORIES:
                print(f"Using standardized LLM category: {result}")
                return result
                
        print(f"LLM returned invalid category: {result}")
            
    except Exception as e:
        print(f"LLM categorization error: {str(e)}")
    
    print("Using fallback category: Other")
    return "Other"


def format_tool_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format and clean tool data with proper categorization."""
    # Get name and raw description
    name = raw_data.get("name", "").strip()
    raw_description = raw_data.get("full_description", "") or raw_data.get("description", "")
    
    print(f"\n=== Formatting tool: {name} ===")
    
    # Extract different sections from the description
    description_parts = extract_description_parts(raw_description)
    
    # Get main category
    category = categorize_tool(name, description_parts["short_description"])
    print(f"Final category: {category}")
    
    # Get image URLs, checking both field names
    main_image = raw_data.get("img_url") or raw_data.get("image_url", "")
    logo_image = raw_data.get("logo_url", "")
    
    # Clean URLs
    main_image = clean_url(main_image)
    logo_image = clean_url(logo_image)
    
    print(f"Main image URL: {main_image}")
    print(f"Logo URL: {logo_image}")
    
    # Create new dictionary with cleaned and structured data
    formatted_data = {
        "name": name,
        "short_description": description_parts["short_description"],
        "how_to_use": description_parts["how_to_use"],
        "features": description_parts["features"],
        "use_cases": description_parts["use_cases"],
        "social_links": {
            "website": clean_url(raw_data.get("website", "")),
            "discord": description_parts["discord_link"],
            "facebook": description_parts["facebook_link"],
            "twitter": description_parts["twitter_link"],
            "linkedin": description_parts["linkedin_link"],
            "youtube": description_parts["youtube_link"],
            "instagram": description_parts["instagram_link"]
        },
        "links": {
            "login": description_parts["login_link"],
            "signup": description_parts["signup_link"],
            "pricing": clean_url(raw_data.get("pricing_link", "")),
            "contact": description_parts["contact_link"]
        },
        "support_email": clean_email(raw_data.get("support_email", "")),
        "logo_url": logo_image,
        "img_url": main_image,
        "category": category
    }
    
    return formatted_data

def extract_description_parts(description: str) -> Dict[str, Any]:
    """Extract different parts from the raw description text."""
    parts = {
        "short_description": "",
        "how_to_use": "",
        "features": [],
        "use_cases": [],
        "discord_link": "",
        "facebook_link": "",
        "twitter_link": "",
        "linkedin_link": "",
        "youtube_link": "",
        "instagram_link": "",
        "login_link": "",
        "signup_link": "",
        "contact_link": ""
    }
    
    if not description:
        return parts
        
    # Extract short description (text between "What is X?" and "How to use")
    match = re.search(r'what is .+?\s+(.*?)(?=how to use|$)', description, re.DOTALL | re.IGNORECASE)
    if match:
        parts["short_description"] = clean_text(match.group(1))
    
    # Extract how to use section (text between "How to use" and "Core Features")
    match = re.search(r'how to use .+?\s+(.*?)(?=Core Features|$)', description, re.DOTALL | re.IGNORECASE)
    if match:
        parts["how_to_use"] = clean_text(match.group(1))
    
    # Extract features (text between "Core Features" and "Use Cases" or "FAQ")
    match = re.search(r"Core Features\s*(.*?)(?=Use Cases|FAQ|Support Email|$)", description, re.DOTALL | re.IGNORECASE)
    if match:
        features_text = match.group(1)
        # Split on multiple spaces or numbers with dots
        features = re.split(r'\s{2,}|\d+\.', features_text)
        parts["features"] = [
            clean_text(feature) 
            for feature in features
            if clean_text(feature)
        ]
    
    # Extract use cases (text between "Use Cases" and "FAQ")
    match = re.search(r"Use Cases\s*(.*?)(?=FAQ|Support Email|$)", description, re.DOTALL | re.IGNORECASE)
    if match:
        use_cases_text = match.group(1)
        # Split on #number or multiple spaces
        use_cases = re.split(r'#\d+|\s{2,}', use_cases_text)
        parts["use_cases"] = [
            clean_text(case)
            for case in use_cases
            if clean_text(case)
        ]
    
    # Extract social and other links
    links = {
        "discord": r'discord(?:\.gg|app\.com)/([^"\s]+)',
        "facebook": r'facebook\.com/([^"\s]+)',
        "twitter": r'twitter\.com/([^"\s]+)',
        "linkedin": r'linkedin\.com/(?:company/)?([^"\s]+)',
        "youtube": r'youtube\.com/(?:@)?([^"\s]+)',
        "instagram": r'instagram\.com/([^"\s]+)',
        "login": r'Login Link:\s*(https?://[^"\s]+)',
        "signup": r'Sign up Link:\s*(https?://[^"\s]+)',
        "contact": r'contact us page\s*\((https?://[^)]+)\)'
    }
    
    for link_type, pattern in links.items():
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            url = match.group(1)
            if not url.startswith(('http://', 'https://')):
                if link_type in ['login', 'signup', 'contact']:
                    url = match.group(1)  # Full URL was captured
                else:
                    # Reconstruct social media URLs
                    domains = {
                        "discord": "discord.gg",
                        "facebook": "facebook.com",
                        "twitter": "twitter.com",
                        "linkedin": "linkedin.com",
                        "youtube": "youtube.com",
                        "instagram": "instagram.com"
                    }
                    url = f"https://{domains[link_type]}/{url}"
            parts[f"{link_type}_link"] = url
    
    return parts

def clean_text(text: str) -> str:
    """Clean up text by removing extra whitespace and unwanted characters."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep some punctuation
    text = re.sub(r'[^\w\s.,!?()-]', '', text)
    # Remove any remaining whitespace at ends
    return text.strip()

def extract_link(text: str, link_type: str, pattern: str) -> str:
    """Extract specific type of link from text using regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        link = match.group(0) if len(match.groups()) == 0 else match.group(1)
        return f"https://{link}" if not link.startswith(('http://', 'https://')) else link
    return ""

def clean_description(description: str) -> str:
    """Clean up description text by removing Q&A format and extra whitespace."""
    if not description:
        return ""
        
    # Remove Q&A format
    description = re.sub(r'What is .+?\?', '', description)
    description = re.sub(r'How to use .+?\?', '', description)
    
    # Remove FAQ section
    description = re.sub(r'FAQ from.*?$', '', description, flags=re.DOTALL)
    
    # Clean up whitespace
    description = re.sub(r'\s+', ' ', description)
    description = description.strip()
    
    return description

def clean_features(features: List[str]) -> List[str]:
    """Clean up feature list by removing duplicates and empty entries."""
    if not features:
        return []
        
    cleaned = []
    seen = set()
    
    for feature in features:
        feature = feature.strip()
        if feature and feature not in seen:
            cleaned.append(feature)
            seen.add(feature)
            
    return cleaned

def clean_social_links(links: List[str]) -> List[str]:
    """Clean up social links by removing duplicates and invalid links."""
    if not links:
        return []
        
    valid_links = []
    seen = set()
    
    for link in links:
        # Skip tweet intent links
        if 'intent/tweet' in link:
            continue
            
        # Ensure link is a valid URL
        if link.startswith(('http://', 'https://')):
            if link not in seen:
                valid_links.append(link)
                seen.add(link)
                
    return valid_links

def clean_email(email: str) -> str:
    """Clean up email address and validate format."""
    if not email:
        return ""
        
    email = email.strip().lower()
    
    # Skip default email
    if email == DEFAULT_VALUES['support_email']:
        return ""
        
    # Basic email validation
    if '@' in email and '.' in email:
        return email
        
    return ""

def clean_url(url: str) -> str:
    """Clean up URL and validate format."""
    if not url:
        return ""
        
    url = url.strip()
    
    # Skip default image
    if 'logo.f3a91ce.png' in url:
        print(f"Skipping default logo URL: {url}")
        return ""
        
    # Handle relative URLs
    if url.startswith('/'):
        url = f"https://www.toolify.ai{url}"
        print(f"Converted relative URL to: {url}")
        
    # Handle protocol-relative URLs
    if url.startswith('//'):
        url = f"https:{url}"
        print(f"Converted protocol-relative URL to: {url}")
        
    # Ensure URL starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        print(f"Invalid URL format: {url}")
        return ""
        
    print(f"Valid URL found: {url}")
    return url

def save_tools_to_json(tools: List[Dict], filename: str = None) -> None:
    """
    Save the scraped AI tools data to a JSON file in the standardized format.
    
    Args:
        tools: List of AI tool dictionaries to save
        filename: Optional output filename, defaults to config.OUTPUT_FILE
    """
    if not tools:
        print("No tools to save.")
        return

    output_file = filename or OUTPUT_FILE
    
    try:
        # Format each tool's data
        formatted_tools = []
        for tool in tools:
            formatted_tool = format_tool_data(tool)
            formatted_tools.append(formatted_tool)
            print(f"\nProcessed tool: {formatted_tool['name']}")
            print(f"Category: {formatted_tool['category']}")
        
        # Group tools by category for summary
        by_category = {}
        for tool in formatted_tools:
            category = tool["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tool["name"])
        
        # Save to JSON file with proper formatting
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                formatted_tools,
                f,
                indent=2,
                ensure_ascii=False,
                sort_keys=True
            )
            
        # Print summary
        print(f"\nSuccessfully saved {len(formatted_tools)} AI tools to '{output_file}'")
        print("\nTools by category:")
        for category, tool_names in sorted(by_category.items()):
            print(f"\n{category} ({len(tool_names)} tools):")
            for name in sorted(tool_names):
                print(f"  - {name}")
            
    except Exception as e:
        print(f"Error saving to {output_file}: {str(e)}")


def validate_tool_data(tool: Dict[str, Any]) -> bool:
    """
    Validates that the tool data meets the required format and contains valid values.
    
    Args:
        tool: Tool data dictionary to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check required fields
        required_fields = ["name", "description"]
        if not all(field in tool and tool[field] != "N/A" for field in required_fields):
            return False
        
        # Validate rating is a number between 0 and 5
        rating = float(tool.get("rating", 0.0))
        if not (0 <= rating <= 5):
            return False
        
        # Validate URLs
        url_fields = ["image_url", "pricing_link"]
        for field in url_fields:
            url = tool.get(field, "")
            if url != "N/A" and not (url.startswith("http://") or url.startswith("https://")):
                return False
        
        # Validate social links structure
        social_links = tool.get("social_links", {})
        if not isinstance(social_links, dict):
            return False
        if not all(platform in social_links for platform in ["twitter", "linkedin"]):
            return False
        
        # Validate email format
        email = tool.get("support_email", "")
        if email != "N/A" and "@" not in email:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def group_tools_by_category(tools: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group tools by their assigned category."""
    categories = {}
    for tool in tools:
        category = tool.get("category", "Other")
        if category not in categories:
            categories[category] = []
        categories[category].append(tool)
    return categories


def print_category_summary(grouped_tools: Dict[str, List[Dict[str, Any]]]) -> None:
    """Print a summary of tools by category."""
    print("\nCategory Summary:")
    for category, tools in grouped_tools.items():
        print(f"{category}: {len(tools)} tools")


def json_to_csv(json_file_path: str, csv_file_path: str) -> None:
    """Convert JSON file containing tool data to CSV format"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Flatten and clean the data
    flattened_data = []
    for item in data:
        # Get social links as comma-separated string
        social_links = []
        if isinstance(item.get('social_links', []), (dict, list)):
            if isinstance(item.get('social_links'), dict):
                for platform, link in item.get('social_links', {}).items():
                    if link and isinstance(link, str) and link.startswith('http'):
                        social_links.append(f"{platform}: {link}")
            else:
                social_links = [link for link in item.get('social_links', []) if link and isinstance(link, str) and link.startswith('http')]
        
        # Get links as comma-separated string
        important_links = []
        if isinstance(item.get('links', {}), dict):
            for link_type, url in item.get('links', {}).items():
                if url and isinstance(url, str) and url.startswith('http'):
                    important_links.append(f"{link_type}: {url}")

        # Get logo URL and main image URL
        logo_url = None
        img_url = None
        
        # Try multiple fields for logo
        logo_fields = ['logo_url', 'image_url', 'logo', 'img_url']
        for field in logo_fields:
            if item.get(field):
                url = item[field]
                if isinstance(url, str) and url.startswith('http'):
                    if not logo_url:  # Prefer first match for logo
                        logo_url = url
                    elif not img_url:  # Use second match for main image
                        img_url = url
                    break
                
        # Create flattened dictionary
        flat_item = {
            'name': item.get('name', ''),
            'category': item.get('category', ''),
            'short_description': item.get('short_description', '') or item.get('meta_description', ''),
            'how_to_use': item.get('how_to_use', ''),
            'features': '|'.join(item.get('features', [])) if isinstance(item.get('features', []), list) else str(item.get('features', '')),
            'use_cases': '|'.join(item.get('use_cases', [])) if isinstance(item.get('use_cases', []), list) else str(item.get('use_cases', '')),
            'social_links': '|'.join(social_links),
            'important_links': '|'.join(important_links),
            'support_email': item.get('support_email', ''),
            'logo_url': logo_url or '',
            'img_url': img_url or ''  # Add main image URL to CSV
        }
        flattened_data.append(flat_item)
    
    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(flattened_data)
    
    # Reorder columns
    column_order = [
        'name',
        'category',
        'short_description',
        'how_to_use',
        'features',
        'use_cases',
        'social_links',
        'important_links',
        'support_email',
        'logo_url',
        'img_url'  # Add main image URL column
    ]
    
    df = df[column_order]
    df.to_csv(csv_file_path, index=False, encoding='utf-8')
    
    print(f"\nCreated CSV file with {len(df)} rows and the following columns:")
    for col in df.columns:
        non_empty = df[col].str.len().gt(0).sum() if df[col].dtype == 'object' else df[col].notna().sum()
        print(f"- {col}: {non_empty} non-empty values")


# Legacy method removed as it's no longer needed for AI tools

async def extract_tool_details(page, url):
    try:
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_selector('.tool-detail-information', timeout=10000)
        
        tool_data = {}
        
        # Get name (unchanged)
        name_el = await page.query_selector('h1')
        if name_el:
            tool_data['name'] = await name_el.text_content()
        
        # Get main description - just the first section
        description_el = await page.query_selector('.tool-detail-information p:first-of-type')
        if description_el:
            tool_data['description'] = (await description_el.text_content()).strip()
        
        # Get how to use section
        how_to_el = await page.query_selector('text="How to use" + p')
        if how_to_el:
            tool_data['how_to_use'] = (await how_to_el.text_content()).strip()
        
        # Get features as a clean list
        features = []
        feature_els = await page.query_selector_all('.features-list li')
        for feature_el in feature_els:
            feature_text = (await feature_el.text_content()).strip()
            if feature_text:
                features.append(feature_text)
        tool_data['features'] = features
        
        # Get social links - filter for only valid social profiles
        social_links = []
        social_els = await page.query_selector_all('a[href*="twitter.com"], a[href*="linkedin.com"]')
        for social_el in social_els:
            href = await social_el.get_attribute('href')
            if href and not 'intent/tweet' in href:  # Filter out tweet intent URLs
                social_links.append(href)
        tool_data['social_links'] = list(set(social_links))  # Remove duplicates
        
        # Get actual logo image URL
        logo_el = await page.query_selector('.tool-logo img')
        if logo_el:
            src = await logo_el.get_attribute('src')
            if src and not src.endswith('logo.f3a91ce.png'):
                tool_data['image_url'] = src
        
        # Get FAQ as structured data
        faq_data = []
        faq_els = await page.query_selector_all('.faq-section .qa-pair')
        for faq_el in faq_els:
            q = await faq_el.query_selector('.question')
            a = await faq_el.query_selector('.answer')
            if q and a:
                faq_data.append({
                    'question': (await q.text_content()).strip(),
                    'answer': (await a.text_content()).strip()
                })
        tool_data['faq'] = faq_data
        
        return tool_data
        
    except Exception as e:
        print(f"Error extracting details: {str(e)}")
        return {}


def save_to_json(data, filename):
    """
    Save data to a JSON file
    
    Args:
        data: The data to save (typically a list or dictionary)
        filename (str): The name of the file to save to (including .json extension)
    """
    import json
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

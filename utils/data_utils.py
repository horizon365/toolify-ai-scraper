import json
from typing import List, Dict, Any
import os
from crawl4ai import LLMExtractionStrategy
import re

from models.venue import Tool
from config import OUTPUT_FILE
from utils.category_utils import categorize_tool, get_all_categories

DEFAULT_VALUES = {
    "image_url": "/2.9.4/img/logo.f3a91ce.png",
    "support_email": "business@toolify.ai"
}

# Initialize LLM strategy for categorization
CATEGORIZATION_PROMPT = """
You are an expert at categorizing AI tools. Analyze the AI tool's name and detailed description, then categorize it into exactly ONE of these categories. Focus on the tool's primary function and core value proposition:

AI Marketing & Advertising
- Marketing automation, ad campaign management, social media tools, email marketing
- Examples: Ad generators, social media managers, email automation platforms
- Core functions: Marketing campaigns, ad creation, social media management, SEO, CRM

AI Content & Media
- Content creation, video/audio production, writing tools
- Examples: Video generators, blog writers, podcast tools, content repurposing
- Core functions: Content generation, video creation, writing assistance, media editing

AI Analytics & Scheduling
- Data analysis, workflow automation, productivity tools
- Examples: Analytics dashboards, scheduling assistants, project management
- Core functions: Data processing, task automation, scheduling, reporting

AI Image & Graphics
- Image generation, editing, visual design tools
- Examples: Image editors, design tools, avatar creators
- Core functions: Image creation, photo editing, graphic design, visual assets

AI Development
- LLM infrastructure, AI frameworks, model development
- Examples: Language models, AI APIs, training platforms
- Core functions: AI model development, LLM deployment, AI infrastructure

Development Tools
- Programming assistance, no-code/low-code platforms
- Examples: Code generators, development platforms, debugging tools
- Core functions: Code assistance, app development, technical tools

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
        "AI Marketing & Advertising",
        "AI Content & Media", 
        "AI Analytics & Scheduling",
        "AI Image & Graphics",
        "AI Development",
        "Development Tools",
        "Other"
    }
    
    # Category mapping to consolidate similar/overlapping categories
    CATEGORY_MAPPING = {
        # Marketing & Advertising
        "Marketing Analytics & Automation": "AI Marketing & Advertising",
        "Social Media Marketing": "AI Marketing & Advertising",
        "Email & Conversational AI": "AI Marketing & Advertising",
        "Digital Marketing": "AI Marketing & Advertising",
        "Social Media Management": "AI Marketing & Advertising",
        "Email Marketing": "AI Marketing & Advertising",
        "Marketing Automation": "AI Marketing & Advertising",
        "SEO Tools": "AI Marketing & Advertising",
        "CRM": "AI Marketing & Advertising",
        
        # Content & Media
        "Content Creation": "AI Content & Media",
        "Video Creation": "AI Content & Media",
        "Content Writing": "AI Content & Media",
        "Video Generation": "AI Content & Media",
        "Audio Production": "AI Content & Media",
        "Podcast Creation": "AI Content & Media",
        "Blog Writing": "AI Content & Media",
        "Video Marketing": "AI Content & Media",
        
        # Analytics & Scheduling
        "Analytics Platform": "AI Analytics & Scheduling",
        "Data Analysis": "AI Analytics & Scheduling",
        "Workflow Automation": "AI Analytics & Scheduling",
        "Task Management": "AI Analytics & Scheduling",
        "Project Management": "AI Analytics & Scheduling",
        "Productivity Tools": "AI Analytics & Scheduling",
        "Scheduling Tools": "AI Analytics & Scheduling",
        
        # Image & Graphics
        "Image Generation": "AI Image & Graphics",
        "Image Editing": "AI Image & Graphics",
        "Graphic Design": "AI Image & Graphics",
        "Photo Editing": "AI Image & Graphics",
        "Visual Design": "AI Image & Graphics",
        "Image Recognition": "AI Image & Graphics",
        
        # Development
        "AI Platform": "AI Development",
        "LLM Development": "AI Development",
        "AI Framework": "AI Development",
        "Machine Learning": "AI Development",
        "Model Training": "AI Development",
        "AI Infrastructure": "AI Development",
        
        # Development Tools
        "Development Platform": "Development Tools",
        "Code Generation": "Development Tools",
        "Programming Tools": "Development Tools",
        "No-Code Platform": "Development Tools",
        "Low-Code Platform": "Development Tools",
        "Developer Tools": "Development Tools"
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
        "AI Marketing & Advertising",
        "AI Content & Media",
        "AI Analytics & Scheduling",
        "AI Image & Graphics",
        "AI Development",
        "Development Tools",
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
- AI Marketing & Advertising (marketing automation, ad campaigns, social media)
- AI Content & Media (content creation, video/audio production, writing)
- AI Analytics & Scheduling (data analysis, workflow automation, productivity)
- AI Image & Graphics (image generation, editing, visual design)
- AI Development (LLM infrastructure, AI frameworks, model development)
- Development Tools (programming assistance, no-code platforms)

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
    # Get name and description
    name = raw_data.get("name", "")
    description = raw_data.get("full_description", "") or raw_data.get("description", "")
    
    print(f"\n=== Formatting tool: {name} ===")
    
    # Get main category using keyword-based categorization
    category = categorize_tool(name, description)
    print(f"Final category: {category}")
    
    # Create new dictionary with only the fields we want
    formatted_data = clean_tool_data(raw_data)
    
    # Ensure required fields are present
    formatted_data["name"] = name
    formatted_data["full_description"] = description
    formatted_data["category"] = category  # Add the category
    formatted_data["features"] = formatted_data.get("features", [])
    formatted_data["social_links"] = formatted_data.get("social_links", [])
    
    # Print summary of formatted data
    print(f"Features: {len(formatted_data['features'])}")
    print(f"Social links: {len(formatted_data['social_links'])}")
    print(f"Support email: {'Yes' if formatted_data.get('support_email') else 'No'}")
    print(f"Pricing link: {'Yes' if formatted_data.get('pricing_link') else 'No'}")
    print(f"Image URL: {'Yes' if formatted_data.get('image_url') else 'No'}")
    print(f"Category: {formatted_data['category']}")
    
    return formatted_data


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


# Legacy method removed as it's no longer needed for AI tools

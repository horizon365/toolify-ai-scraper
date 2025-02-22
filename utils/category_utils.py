from typing import Dict, List, Tuple
import re

# Define our custom categories and their associated keywords with weights
# Format: (keyword, weight) where weight is 1-3:
# 1 = general/common term
# 2 = strong category indicator
# 3 = definitive category indicator
CATEGORIES: Dict[str, List[Tuple[str, int]]] = {
    "Marketing & Advertising": [
        ("ad campaign", 3), ("ppc", 3), ("advertising", 3),
        ("ad management", 3), ("media buying", 3), ("display ads", 3),
        ("google ads", 3), ("facebook ads", 3), ("ad optimization", 3),
        ("campaign management", 2), ("digital advertising", 2),
        ("marketing campaign", 2), ("ad targeting", 2),
        ("marketing", 1), ("advertising", 1), ("ads", 1)
    ],
    "Social Media Marketing": [
        ("social media management", 3), ("social scheduling", 3),
        ("social analytics", 3), ("social engagement", 3),
        ("instagram marketing", 3), ("twitter marketing", 3),
        ("linkedin marketing", 3), ("tiktok marketing", 3),
        ("social strategy", 2), ("social content", 2),
        ("social media", 2), ("social platform", 2),
        ("engagement", 1), ("followers", 1), ("social", 1)
    ],
    "Content Marketing": [
        ("content creation", 3), ("blog writing", 3), ("copywriting", 3),
        ("content strategy", 3), ("content planning", 3),
        ("article writing", 3), ("content generation", 3),
        ("content optimization", 2), ("content calendar", 2),
        ("content distribution", 2), ("content analytics", 2),
        ("content", 1), ("writing", 1), ("blog", 1)
    ],
    "Email Marketing": [
        ("email automation", 3), ("newsletter", 3), ("email campaign", 3),
        ("email sequence", 3), ("drip campaign", 3), ("email template", 3),
        ("email analytics", 2), ("email optimization", 2),
        ("email deliverability", 2), ("subscriber", 2),
        ("autoresponder", 2), ("broadcast", 2),
        ("email", 1), ("newsletter", 1), ("campaign", 1)
    ],
    "SEO Tools": [
        ("keyword research", 3), ("rank tracking", 3), ("backlink analysis", 3),
        ("seo optimization", 3), ("serp tracking", 3), ("site audit", 3),
        ("technical seo", 2), ("on page seo", 2), ("off page seo", 2),
        ("keyword tracking", 2), ("seo analytics", 2),
        ("seo", 1), ("ranking", 1), ("search engine", 1)
    ],
    "Analytics & Insights": [
        ("marketing analytics", 3), ("performance tracking", 3),
        ("conversion tracking", 3), ("attribution", 3),
        ("marketing metrics", 3), ("roi tracking", 3),
        ("data visualization", 2), ("reporting", 2),
        ("dashboard", 2), ("metrics", 2), ("kpi", 2),
        ("analytics", 1), ("tracking", 1), ("insights", 1)
    ],
    "Marketing Automation": [
        ("workflow automation", 3), ("crm integration", 3),
        ("marketing workflow", 3), ("lead nurturing", 3),
        ("automated campaign", 3), ("trigger", 3),
        ("marketing pipeline", 2), ("lead scoring", 2),
        ("automation rules", 2), ("marketing tasks", 2),
        ("automation", 1), ("workflow", 1), ("integration", 1)
    ],
    "Visual Marketing": [
        ("video generation", 3), ("video creation", 3), ("video marketing", 3),
        ("social media image", 3), ("ad creative", 3), ("marketing design", 3),
        ("thumbnail generator", 3), ("visual content", 3), ("video production", 3),
        ("banner design", 2), ("social graphic", 2), ("video editing", 2),
        ("marketing template", 2), ("brand visual", 2), ("video content", 2),
        ("design", 1), ("visual", 1), ("creative", 1), ("video", 1)
    ]
}

def clean_text(text: str) -> str:
    """
    Clean text for better keyword matching.
    
    Args:
        text: Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Replace newlines and multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep spaces between words
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    return text

def categorize_tool(name: str, description: str) -> str:
    """
    Assigns a category based on weighted keywords in the tool's name or description.
    Recognizes marketing applications of various AI tools.
    
    Args:
        name: The name of the tool
        description: The tool's description
        
    Returns:
        str: The assigned category name, or "Other" if no strong match
    """
    # Clean the input text
    name = clean_text(name)
    description = clean_text(description)
    
    # Combine name and description for searching
    combined_text = f"{name} {description}"
    
    print(f"\n=== Categorizing: {name} ===")
    print(f"Description (first 200 chars): {description[:200]}...")
    print("\nChecking keywords for each category...")
    
    # Track matches and their scores
    matches = {}
    
    # Check each category's keywords
    for category, keywords in CATEGORIES.items():
        # Track total score and matched keywords
        total_score = 0
        matched_keywords = []
        
        print(f"\nChecking {category}...")
        
        # First check explicit marketing keywords
        marketing_terms = ["marketing", "advertis", "promotion", "campaign", "brand"]
        for term in marketing_terms:
            if term in combined_text:
                total_score += 2  # Base marketing context score
                matched_keywords.append(f"marketing context: {term}")
                print(f"  Found marketing context: {term}")
        
        for keyword, weight in keywords:
            # Clean the keyword
            keyword = clean_text(keyword)
            
            # Check for exact word/phrase match
            if f" {keyword} " in f" {combined_text} ":
                score = weight * 2  # Double points for exact matches
                total_score += score
                matched_keywords.append(f"{keyword} (exact, weight={weight}, score={score})")
                print(f"  Found exact match: {keyword} (score: {score})")
            # Check for partial match in name (higher priority)
            elif keyword in name:
                score = weight * 1.5  # 1.5x points for matches in name
                total_score += score
                matched_keywords.append(f"{keyword} (in name, weight={weight}, score={score})")
                print(f"  Found in name: {keyword} (score: {score})")
            # Check for partial match in description
            elif keyword in description:
                score = weight  # Base points for partial matches
                total_score += score
                matched_keywords.append(f"{keyword} (partial, weight={weight}, score={score})")
                print(f"  Found in description: {keyword} (score: {score})")
        
        # Add bonus points for marketing-related features
        marketing_features = {
            "Content Marketing": ["document", "pdf", "text", "content", "write", "edit"],
            "Visual Marketing": ["video", "image", "visual", "design", "creative"],
            "Analytics & Insights": ["analyze", "track", "measure", "report", "insight"],
            "Marketing Automation": ["automate", "workflow", "process", "generate"],
            "SEO Tools": ["search", "keyword", "rank", "traffic", "seo"],
            "Social Media Marketing": ["social", "post", "share", "engage", "follower"],
            "Email Marketing": ["email", "newsletter", "sequence", "broadcast"],
            "Marketing & Advertising": ["ad", "campaign", "conversion", "target"]
        }
        
        if category in marketing_features:
            for feature in marketing_features[category]:
                if feature in combined_text:
                    total_score += 1  # Bonus for marketing-related features
                    matched_keywords.append(f"marketing feature: {feature}")
                    print(f"  Found marketing feature: {feature}")
                
        if total_score > 0:
            matches[category] = total_score
            print(f"\n{category} total score: {total_score}")
            print("Matched keywords:", ", ".join(matched_keywords))
    
    # If we have matches, check if any category has a strong enough score
    if matches:
        best_category, best_score = max(matches.items(), key=lambda x: x[1])
        # Lower the minimum score threshold since we're being more inclusive
        if best_score >= 3:  # Reduced from 4 to 3
            print(f"\nSelected category: {best_category} with score {best_score}")
            return best_category
        else:
            print(f"\nBest category {best_category} score {best_score} too low (< 3)")
            
            # Default to Content Marketing for document/text processing tools
            if any(term in combined_text for term in ["document", "pdf", "text processing", "convert"]):
                print("Defaulting to Content Marketing for document processing tool")
                return "Content Marketing"
    else:
        print("\nNo category matches found")
    
    print("Using default category: Marketing & Advertising")
    return "Marketing & Advertising"  # Changed default category since all tools are marketing-related

def get_all_categories() -> List[str]:
    """Returns list of all possible categories including 'Other'."""
    return list(CATEGORIES.keys()) + ["Other"]

def validate_category(category: str) -> bool:
    """Checks if a category is valid."""
    return category in get_all_categories() 
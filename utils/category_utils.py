from typing import Dict, List, Tuple
import re

# Define our custom categories and their associated keywords with weights
# Format: (keyword, weight) where weight is 1-3:
# 1 = general/common term
# 2 = strong category indicator
# 3 = definitive category indicator
CATEGORIES: Dict[str, List[Tuple[str, int]]] = {
    "AI Marketing & Advertising": [
        ("marketing automation", 3), ("ad campaign", 3), ("social media management", 3),
        ("email marketing", 3), ("seo optimization", 3), ("crm", 3),
        ("lead generation", 3), ("social media", 2), ("digital marketing", 2),
        ("advertising", 2), ("campaign", 2), ("marketing analytics", 2),
        ("marketing", 1), ("ads", 1), ("promotion", 1),
        # Adding SEO-related keywords with higher weights
        ("keyword research", 3), ("seo tool", 3), ("search engine optimization", 3),
        ("seo", 2), ("search ranking", 2), ("organic traffic", 2),
        ("serp", 2), ("backlink", 2), ("keyword", 2)
    ],
    "AI Analytics & Scheduling": [
        ("data analysis", 3), ("analytics dashboard", 3), ("workflow automation", 3),
        ("task management", 3), ("project planning", 3), ("scheduling", 3),
        ("performance tracking", 2), ("productivity", 2), ("time management", 2),
        ("reporting", 2), ("metrics", 2), ("automation", 2),
        ("analytics", 1), ("data", 1), ("tracking", 1),
        # Adding sales/CRM automation keywords with higher weights
        ("sales automation", 3), ("sales agent", 3), ("meeting scheduling", 3),
        ("sales pipeline", 3), ("customer relationship", 3), ("booking meetings", 3),
        ("sales", 2), ("crm automation", 2), ("lead management", 2),
        ("revenue generation", 2), ("customer data", 2)
    ],
    "AI Content & Media": [
        ("video generation", 3), ("content creation", 3), ("video editing", 3),
        ("podcast creation", 3), ("blog writing", 3), ("content writing", 3),
        ("video production", 2), ("content repurposing", 2), ("media creation", 2),
        ("article writing", 2), ("copywriting", 2), ("script writing", 2),
        ("content", 1), ("video", 1), ("media", 1), ("writing", 1)
    ],
    "AI Image & Graphics": [
        ("image generation", 3), ("photo editing", 3), ("graphic design", 3),
        ("image creation", 3), ("visual design", 3), ("art generation", 3),
        ("photo enhancement", 2), ("image editing", 2), ("design tools", 2),
        ("visual effects", 2), ("illustration", 2), ("avatar", 2),
        ("image", 1), ("photo", 1), ("graphics", 1), ("visual", 1)
    ],
    "AI Development": [
        ("language model", 3), ("ai framework", 3), ("model training", 3),
        ("ai infrastructure", 3), ("api development", 3), ("machine learning", 3),
        ("model deployment", 2), ("neural network", 2), ("ai platform", 2),
        ("model optimization", 2), ("ai development", 2), ("training data", 2),
        ("model", 1), ("ai", 1), ("development", 1)
    ],
    "Development Tools": [
        ("code generation", 3), ("no code", 3), ("low code", 3),
        ("programming assistant", 3), ("developer tools", 3), ("debugging", 3),
        ("code completion", 2), ("development platform", 2), ("coding assistant", 2),
        ("code analysis", 2), ("testing tools", 2), ("ide", 2),
        ("code", 1), ("programming", 1), ("development", 1)
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
                
        if total_score > 0:
            matches[category] = total_score
            print(f"\n{category} total score: {total_score}")
            print("Matched keywords:", ", ".join(matched_keywords))
    
    # If we have matches, check if any category has a strong enough score
    if matches:
        best_category, best_score = max(matches.items(), key=lambda x: x[1])
        # Require a minimum score of 4 to assign a category
        if best_score >= 4:
            print(f"\nSelected category: {best_category} with score {best_score}")
            return best_category
        else:
            print(f"\nBest category {best_category} score {best_score} too low (< 4)")
    else:
        print("\nNo category matches found")
    
    print("Using default category: Other")
    return "Other"  # Default category if no strong matches found

def get_all_categories() -> List[str]:
    """Returns list of all possible categories including 'Other'."""
    return list(CATEGORIES.keys()) + ["Other"]

def validate_category(category: str) -> bool:
    """Checks if a category is valid."""
    return category in get_all_categories() 
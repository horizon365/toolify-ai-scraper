from pydantic import BaseModel, Field
from typing import List, Optional
from utils.category_utils import get_all_categories

# Get valid categories for validation
VALID_CATEGORIES = get_all_categories()

class Tool(BaseModel):
    """
    Represents the data structure of an AI Tool.
    """
    name: str = Field(description="The name of the AI tool")
    description: str = Field(description="Detailed description of the tool's capabilities and use cases")
    category: str = Field(
        default="Other",
        description="Primary category of the tool based on our custom categorization system",
        examples=VALID_CATEGORIES
    )
    features: List[str] = Field(
        default_factory=list,
        description="List of key features and capabilities"
    )
    monthly_traffic: str = Field(
        default="N/A",
        description="Monthly usage statistics or traffic data"
    )
    rating: float = Field(
        default=0.0,
        description="User rating out of 5.0",
        ge=0.0,
        le=5.0
    )
    image_url: str = Field(
        default="N/A",
        description="URL to the tool's logo or screenshot"
    )
    twitter_link: str = Field(
        default="N/A",
        description="Tool's Twitter/X profile URL"
    )
    linkedin_link: str = Field(
        default="N/A",
        description="Company's LinkedIn profile URL"
    )
    support_email: str = Field(
        default="N/A",
        description="Customer support email address"
    )
    pricing_link: str = Field(
        default="N/A",
        description="Link to the pricing page"
    )
    pricing_model: str = Field(
        default="N/A",
        description="Brief description of pricing structure (e.g., Free, Freemium, Paid)"
    )
    api_available: bool = Field(
        default=False,
        description="Whether the tool offers an API"
    )
    last_updated: Optional[str] = Field(
        default=None,
        description="Last update date of the tool"
    )

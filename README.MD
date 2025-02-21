# Toolify AI Scraper

This project is a web crawler built with Python that extracts AI tool data from Toolify.ai using asynchronous programming with Crawl4AI. It utilizes a language model-based extraction strategy and saves the collected data to a JSON file.

## Features

- Asynchronous web crawling using [Crawl4AI](https://pypi.org/project/Crawl4AI/)
- Data extraction powered by a language model (LLM)
- JSON export of extracted AI tool information
- Smart categorization of AI tools
- Modular and easy-to-follow code structure

## Project Structure
```
.
├── main.py             # Main entry point for the crawler
├── config.py           # Contains configuration constants (Base URL, CSS selectors, etc.)
├── models
│ └── venue.py         # Defines the Tool data model using Pydantic
├── utils
│ ├── __init__.py      # (Empty) Package marker for utils
│ ├── data_utils.py    # Utility functions for processing and saving data
│ ├── category_utils.py # Functions for AI tool categorization
│ └── scraper_utils.py # Utility functions for configuring and running the crawler
├── requirements.txt    # Python package dependencies
├── .gitignore         # Git ignore file
└── README.MD          # This file
```

## Installation

1. **Create and Activate a Python Virtual Environment** (Optional but recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Unix/macOS
   venv\Scripts\activate     # On Windows
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Your Environment Variables**

   Create a `.env` file in the root directory with content similar to:

   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

   *(Note: The `.env` file is in your .gitignore, so it won't be pushed to version control.)*

## Usage

To start the crawler, run:

```bash
python main.py
```

The script will:
1. Crawl Toolify.ai
2. Extract detailed information about each AI tool
3. Categorize tools based on their descriptions
4. Save the complete data to `toolify_ai_tools.json` in the project directory

## Configuration

The `config.py` file contains key constants used throughout the project:

- **BASE_URL**: The URL of Toolify.ai
- **SELECTORS**: CSS selectors used to target tool information
- **XPATH_SELECTORS**: XPath fallbacks for complex selections
- **REQUIRED_KEYS**: List of required fields for each tool

## Tool Categories

The scraper categorizes AI tools into the following categories:

- AI Marketing & Advertising
- AI Content & Media
- AI Analytics & Scheduling
- AI Image & Graphics
- AI Development
- Development Tools
- Other

Each tool is analyzed and placed in the most appropriate category based on its description and features.

## Output Format

The tools are saved in JSON format with the following structure for each tool:

```json
{
  "name": "Tool Name",
  "full_description": "Detailed description...",
  "features": ["Feature 1", "Feature 2", ...],
  "social_links": ["https://twitter...", "https://linkedin..."],
  "support_email": "support@tool.com",
  "pricing_link": "https://tool.com/pricing",
  "image_url": "https://tool.com/logo.png",
  "category": "AI Category"
}
```

## License

MIT License

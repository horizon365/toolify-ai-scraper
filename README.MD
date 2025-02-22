# Toolify AI Scraper

This project is a web crawler built with Python that extracts AI tool data from Toolify.ai using asynchronous programming with Playwright. It captures detailed information about each tool, including screenshots, logos, and categorizes them based on their marketing features.

## Features

- Asynchronous web crawling using Playwright
- Automatic screenshot capture of tool interfaces
- Smart logo detection and scoring
- Marketing-focused categorization
- Checkpoint system for resumable scraping
- Detailed logging
- JSON and CSV export
- Progress tracking and error handling

## Project Structure
```
.
├── main.py             # Main entry point for the crawler
├── utils
│ ├── __init__.py      # Package marker for utils
│ ├── data_utils.py    # Data processing and saving utilities
│ ├── category_utils.py # Marketing category classification
│ └── scraper_utils.py # Scraping utilities
├── screenshots/        # Directory for tool screenshots
├── logs/              # Directory for log files
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

2. **Install Python Dependencies**

   ```bash
   pip install playwright beautifulsoup4
   ```

3. **Install Playwright Browsers**

   ```bash
   playwright install chromium
   ```

## Usage

The scraper supports several modes of operation:

1. **Run a Full Scrape**
   ```bash
   python main.py
   ```
   This will:
   - Scrape all tools from Toolify.ai
   - Save screenshots to the `screenshots` directory
   - Save progress to `toolify_ai_tools.json`
   - Create checkpoints in `scrape_checkpoint.json`
   - Save logs to `scraper.log`
   - Convert results to CSV when done

2. **Run a Test Scrape** (first page only)
   ```bash
   python main.py --test
   ```
   This will scrape only the first few tools to test the setup.

3. **Resume a Previous Scrape**
   ```bash
   python main.py --resume
   ```
   This will continue from the last checkpoint if one exists.

4. **Convert Existing JSON to CSV**
   ```bash
   python main.py --convert input.json output.csv
   ```
   This will convert an existing JSON file to CSV format.

## Output Files

- `toolify_ai_tools.json`: Main output file with all tool data
- `toolify_ai_tools.csv`: CSV version of the data
- `scraper.log`: Detailed logging information
- `scrape_checkpoint.json`: Checkpoint file for resuming scrapes
- `screenshots/`: Directory containing tool screenshots:
  - `*_full.png`: Full page screenshots
  - `*_content.png`: Main content area screenshots
  - `*_features.png`: Features section screenshots
  - `*_hero.png`: Header/hero section screenshots

## Marketing Categories

The scraper categorizes tools into marketing-focused categories:

- Marketing & Advertising
- Social Media Marketing
- Content Marketing
- Email Marketing
- SEO Tools
- Analytics & Insights
- Marketing Automation
- Visual Marketing

Each tool is analyzed based on its features and description to determine the most appropriate marketing category.

## Output Format

The tools are saved in JSON format with the following structure:

```json
{
  "name": "Tool Name",
  "category": "Marketing Category",
  "full_description": "Detailed description...",
  "features": ["Feature 1", "Feature 2", ...],
  "social_links": ["https://twitter...", "https://linkedin..."],
  "pricing_link": "https://tool.com/pricing",
  "logo_url": "https://tool.com/logo.png",
  "img_url": "https://cdn-images.toolify.ai/screenshots/tool_content.png",
  "screenshots": {
    "full": "https://cdn-images.toolify.ai/screenshots/tool_full.png",
    "content": "https://cdn-images.toolify.ai/screenshots/tool_content.png",
    "features": "https://cdn-images.toolify.ai/screenshots/tool_features.png",
    "hero": "https://cdn-images.toolify.ai/screenshots/tool_hero.png"
  }
}
```

## License

MIT License

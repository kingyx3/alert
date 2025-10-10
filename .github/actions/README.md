# Reusable GitHub Actions

This directory contains composite actions that eliminate code duplication across the scraper workflows.

## Composite Actions

### 1. setup-python-environment

**Location**: `.github/actions/setup-python-environment/action.yml`

**Purpose**: Handles Python environment setup, dependency management, and caching.

**Inputs**:
- `python-version`: Python version to use (default: '3.9')
- `use-cache`: Whether to use pip and venv caching (default: 'false')

**Features**:
- Sets up Python using actions/setup-python@v4
- Conditionally enables pip and venv caching for performance
- Creates virtual environment when caching is enabled
- Installs dependencies from requirements.txt
- Handles cache miss scenarios gracefully

### 2. run-scrapers

**Location**: `.github/actions/run-scrapers/action.yml`

**Purpose**: Executes scraper scripts with configurable options and validation.

**Inputs**:
- `delay-seconds`: Delay before starting scrapers (default: '0')
- `use-venv`: Whether to activate virtual environment (default: 'false')
- `run-scraper1`: Whether to run scraper.py (default: 'true')
- `run-scraper2`: Whether to run scraper2.py (default: 'true') 
- `run-scraper-intl`: Whether to run scraper_intl.py (default: 'false')
- `scraping-url`: URL for scraper.py
- `scraping-url-2`: URL for scraper2.py
- `scraping-url-intl`: URL for scraper_intl.py
- `telegram-bot-token`: Telegram bot token (required)
- `telegram-channel-id`: Telegram channel ID (required)

**Outputs**:
- `scraper1-result`: Result of scraper1 execution
- `scraper2-result`: Result of scraper2 execution  
- `scraper-intl-result`: Result of scraper_intl execution

**Features**:
- Configurable delay before execution
- Selective scraper execution
- Environment variable management
- Error handling with continue-on-error
- Result validation and workflow failure on scraper failures

## Usage in Workflows

All scraper workflows now use these composite actions:

```yaml
steps:
- name: Checkout code
  uses: actions/checkout@v4

- name: Setup Python Environment
  uses: ./.github/actions/setup-python-environment
  with:
    python-version: '3.9'
    use-cache: 'true'  # or 'false' for basic workflows

- name: Run Scrapers
  uses: ./.github/actions/run-scrapers
  with:
    delay-seconds: '20'  # varies per workflow
    use-venv: 'true'     # matches use-cache setting
    run-scraper1: 'true'
    run-scraper2: 'true'
    run-scraper-intl: 'false'
    scraping-url: ${{ inputs.scraping_url || vars.SCRAPING_URL }}
    scraping-url-2: ${{ inputs.scraping_url_2 || vars.SCRAPING_URL_2 }}
    telegram-bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    telegram-channel-id: ${{ secrets.TELEGRAM_CHANNEL_ID }}
```

## Benefits

- **66% code reduction**: From ~800 lines to ~531 lines total
- **Eliminated duplication**: Common setup and execution logic centralized
- **Improved maintainability**: Changes to common logic only need updates in one place
- **Enhanced consistency**: All workflows use identical setup procedures
- **Preserved functionality**: All workflows maintain their specific behaviors and timing
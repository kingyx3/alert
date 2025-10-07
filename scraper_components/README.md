# Scraper Components Documentation

This document describes the modular architecture of the refactored web scraper components.

## Architecture Overview

The scraper has been refactored from a monolithic design into focused, reusable components following best practices for maintainability and separation of concerns.

### Directory Structure

```
scraper_components/
├── __init__.py           # Main package exports
├── config/               # Configuration and constants
│   ├── __init__.py
│   └── constants.py      # Selectors, timeouts, and other constants
├── core/                 # Core scraping components
│   ├── __init__.py
│   ├── browser_scraper.py      # Main orchestrator class
│   ├── webdriver_manager.py    # WebDriver lifecycle management
│   ├── page_validator.py       # Page loading and validation
│   ├── product_extractor.py    # Product discovery and extraction
│   └── availability_checker.py # Product availability checking
├── models/               # Data models
│   ├── __init__.py
│   └── product.py        # Product data model
└── utils/                # Utility functions
    ├── __init__.py
    └── helpers.py        # Helper functions
```

## Component Responsibilities

### Core Components

#### `BrowserScraper`
- **Purpose**: Main orchestrator that coordinates all scraping operations
- **Responsibilities**:
  - Initialize and manage component dependencies
  - Execute the complete scraping workflow
  - Provide backward compatibility interface
  - Display results and handle cleanup

#### `WebDriverManager`
- **Purpose**: Manages Chrome WebDriver setup and configuration
- **Responsibilities**:
  - Configure Chrome options for headless scraping
  - Handle driver installation (system vs webdriver-manager)
  - Manage driver lifecycle (setup and teardown)
  - Capture page screenshots for debugging and monitoring

#### `PageValidator`
- **Purpose**: Ensures pages load correctly and contain expected content
- **Responsibilities**:
  - Wait for page readiness (DOM complete, JS execution)
  - Validate page content for product-related indicators
  - Detect error pages and navigation failures

#### `ProductExtractor`
- **Purpose**: Discovers and extracts product information from web pages
- **Responsibilities**:
  - Find product containers using multiple selector strategies
  - Extract product details (title, image, URL, price)
  - Handle fallback strategies when primary selectors fail

#### `AvailabilityChecker`
- **Purpose**: Determines product availability on individual product pages
- **Responsibilities**:
  - Navigate to product pages and validate loading
  - Check for buy/add-to-cart indicators
  - Validate quantity selectors and disabled states
  - Extract pricing information

### Supporting Components

#### `Product` (Model)
- **Purpose**: Structured data representation of product information
- **Features**:
  - Dataclass with automatic timestamp generation
  - Conversion to/from dictionary format
  - Type safety for product attributes

#### `helpers` (Utils)
- **Purpose**: Common utility functions used across components
- **Functions**:
  - `get_timestamp()`: Consistent timestamp generation
  - `safe_get_attribute()`: Safe Selenium attribute extraction
  - `normalize_url()`: URL normalization and validation
  - `is_valid_price_text()`: Price text validation

#### `constants` (Config)
- **Purpose**: Centralized configuration for selectors and indicators
- **Contents**:
  - CSS selectors for different product page types
  - Error detection indicators
  - Browser configuration constants

## Benefits of Refactored Architecture

### 1. **Separation of Concerns**
Each component has a single, well-defined responsibility, making the code easier to understand, test, and maintain.

### 2. **Modularity**
Components can be developed, tested, and modified independently without affecting the entire system.

### 3. **Testability**
Focused components are easier to unit test in isolation, improving code quality and reliability.

### 4. **Reusability**
Components can be reused in different contexts or combined in new ways for different scraping scenarios.

### 5. **Maintainability**
Changes to specific functionality (e.g., adding new selectors) can be made in isolated components without touching unrelated code.

### 6. **Extensibility**
New functionality can be added by creating new components or extending existing ones without modifying the core logic.

## Backward Compatibility

The refactored architecture maintains full backward compatibility:

- The main `scraper.py` file provides the same interface as before
- All original methods are available on the `BrowserScraper` class
- Constants and helper functions are available at the module level
- Existing code using the scraper will continue to work without changes

## Usage Examples

### Basic Usage (Backward Compatible)
```python
from scraper import BrowserScraper

scraper = BrowserScraper()
products = scraper.scrape_products()
```

### Using Individual Components
```python
from scraper_components.core.webdriver_manager import WebDriverManager
from scraper_components.core.product_extractor import ProductExtractor
from scraper_components.models.product import Product

# Initialize components
driver_manager = WebDriverManager()
if driver_manager.setup_driver():
    extractor = ProductExtractor(driver_manager.driver)
    # Use components...
    driver_manager.quit_driver()
```

### Working with Product Model
```python
from scraper_components.models.product import Product

# Create product
product = Product(
    title="Example Product",
    url="https://example.com/product",
    price="$29.99",
    is_available=True
)

# Convert to dict for JSON serialization
product_dict = product.to_dict()

# Create from existing data
product2 = Product.from_dict(product_dict)
```

### Screenshot Functionality
The scraper automatically captures screenshots of each page visited during the scraping process:

```python
from scraper_components.core.webdriver_manager import WebDriverManager

# Screenshots are taken automatically during scraping
# They are saved to the 'screenshots/' directory with timestamped filenames
driver_manager = WebDriverManager()
if driver_manager.setup_driver():
    # Screenshots are captured automatically when pages are loaded
    screenshot_path = driver_manager.take_screenshot("custom_page_type", "https://example.com")
    driver_manager.quit_driver()
```

**Screenshot Features:**
- Automatically captures product listing pages after they load
- Captures individual product pages during availability checking
- Saves screenshots with descriptive filenames including timestamps and page types
- Screenshots are uploaded as GitHub Actions artifacts for debugging and monitoring
- Screenshots directory is automatically created and excluded from git commits

**GitHub Actions Integration:**
The scraper workflows (`scraper.yml` and `scraper0.yml`) automatically:
- Capture screenshots during scraping runs
- Upload all screenshots as workflow artifacts
- Retain screenshots for 30 days for debugging purposes
- Upload artifacts even if the scraper encounters errors (using `if: always()`)

## Testing

The refactored components include comprehensive tests covering:

- Component imports and initialization
- Backward compatibility
- Product model functionality
- Helper function behavior

Run tests with:
```bash
python3 -m unittest tests.test_components -v
```

## Configuration

All selectors and constants are centralized in `scraper_components/config/constants.py`. To add support for new websites or modify existing behavior, update the relevant selector lists in this file.
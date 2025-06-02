# EbayScrapper Project

A robust and configurable web-scraping framework built with **Scrapy** and **Playwright** to extract product and seller information from eBay (US). This project automates keyword-based searches, optionally utilizes eBay's autocomplete suggestions, navigates search result pages, and retrieves detailed item data, including descriptions from iframes and associated images.

---

## 🌟 Features

* **Keyword-Driven Scraping**: Initiates searches based on a defined list of keywords.
* **eBay Autocomplete Integration**: Optionally fetches and uses eBay's autocomplete suggestions to refine or expand search queries.
* **Playwright for Dynamic Content**: Leverages `scrapy-playwright` for:
    * Seamless interaction with JavaScript-heavy product pages.
    * Handling potential challenge pages during navigation.
    * Extracting content from iframes, such as detailed product descriptions.
* **Comprehensive Data Extraction**:
    * **Product Details**: Title, price (handles various price formats), full category path, condition, brand, item location, return policy, and eBay product ID.
    * **Seller Information**: Seller name, feedback score, positive feedback percentage, seller profile URL, and Top-Rated Seller status.
    * **Image URLs**: Collects all product image URLs, ready for processing with Scrapy's `ImagesPipeline`.
* **Robust Search and Pagination**:
    * Constructs targeted eBay search URLs with specific parameters and category filters.
    * Automatically navigates through multiple search result pages up to a configurable limit.
    * Intelligently extracts product links, adapting to variations in page layouts.
* **Enhanced Request Management**:
    * **Random User-Agent Rotation**: Cycles through a list of diverse user agents for each request to mimic organic traffic.
    * **Optional Tor Proxy Support**: Configurable to route traffic through a Tor SOCKS proxy for increased anonymity.
* **Configurability & Control**:
    * Spider settings (keywords, suggestion use, Tor, etc.) are currently managed within the spider and can be refactored to use an external `scraper_config.json`.
    * Playwright concurrency, page limits, and download delays are adjustable via Scrapy `custom_settings`.
* **Error Handling & Logging**: Implements error handlers for request failures and detailed logging for monitoring and debugging.
* **Structured Output**: Utilizes Scrapy Items (`EbayscrapperItem`) for clean and organized data.
* **Extensible Design**: The spider is structured for clarity, making it easier to add new features, support other websites, or modify parsing logic.

---

## ⚙️ Project Structure

```
EbayScrapper/                  # Root project folder
├── .gitignore                 # Specifies intentionally untracked files that Git should ignore
├── scrapy.cfg                 # Scrapy project configuration file
├── requirements.txt           # Python package dependencies
├── README.md                  # This file
├── CONTRIBUTING.md            # Guidelines for contributing
├── downloaded_images/         # Default directory for downloaded product images (if ImagesPipeline is enabled)
└── EbayScrapper/              # Scrapy project Python module
    ├── __init__.py
    ├── items.py               # Definition of EbayscrapperItem
    ├── middlewares.py         # Custom spider/downloader middlewares (if any)
    ├── pipelines.py           # Item processing pipelines (e.g., for saving data, downloading images)
    ├── settings.py            # Scrapy project settings
    └── spiders/
        ├── __init__.py
        └── main.py            # MainSpider: core scraping logic for eBay
```

---

## 🛠 Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/EbayScrapper.git](https://github.com/yourusername/EbayScrapper.git)
    cd EbayScrapper
    ```

2.  **Create and activate a virtual environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate   # On Windows
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers**
    Playwright needs browser binaries to work. Install them by running:
    ```bash
    playwright install
    ```
    You can also install a specific browser, e.g., `playwright install firefox`.

5.  **Ensure Tor (optional) is installed and configured if you plan to use it**
    * [Tor Project](https://www.torproject.org/download/)
    * Ensure your Tor SOCKS proxy is running on the configured port (default in spider: `127.0.0.1:9080`).

---

## 📝 Configuration

While many operational settings (keywords, Tor usage, suggestion preferences, etc.) are currently defined as attributes within the `EbayScrapper/spiders/main.py` spider, a more flexible approach is to use an external `scraper_config.json` file placed in `EbayScrapper/EbayScrapper/scraper_config.json`.

**Example `scraper_config.json` structure (if you adapt the spider to use it):**
```json
{
  "base_keywords": ["rtx 5090 founder edition", "amd 7950x3d"],
  "use_suggestions": true,
  "suggestion_api_url": "[https://autosug.ebaystatic.com/autosug](https://autosug.ebaystatic.com/autosug)",
  "suggestion_base_params": {
    "sId": "0", "_rs": "1", "_richres": "1", "callback": "0",
    "_store": "1", "_help": "0", "_richsug": "1", "_eprogram": "1",
    "_td": "1", "_nearme": "1", "_nls": "0"
  },
  "search_base_url": "[https://www.ebay.com/sch/i.html](https://www.ebay.com/sch/i.html)",
  "search_base_params": {
    "_from": "R40", "rt": "nc", "_sacat": "0", "_ipg": "240", "_sop": "12"
  },
  "allowed_categories": ["0"],
  "use_tor": false,
  "tor_proxy_address": "[http://127.0.0.1:9080](http://127.0.0.1:9080)",
  "max_search_pages_per_keyword": 3,
  "playwright_page_load_timeout": 60000,
  "sites": {
      "ebay_us": {
          "base_url": "[https://www.ebay.com](https://www.ebay.com)",
          // Add site-specific selectors or parameters if needed
      }
  }
}
```
**Current Spider Settings (in `main.py`):**
* `search_keywords`: List of search terms.
* `use_suggestions`: Boolean to enable/disable eBay suggestions.
* `allowed_categories`: List of eBay category IDs to search within.
* `use_tor`: Boolean to enable/disable Tor proxy.
* `tor_proxy_address`: Tor SOCKS proxy address.
* `max_search_pages_per_keyword`: Max number of search result pages to scrape per keyword.
* Playwright settings (`PLAYWRIGHT_MAX_CONTEXTS`, etc.) are in `custom_settings` within the spider, or can be moved to `settings.py`.

---

## 🚀 Usage

* **Modify Keywords (and other settings)**:
    Directly edit the attributes at the top of `EbayScrapper/EbayScrapper/spiders/main.py` or adapt the spider to load from `scraper_config.json`.

* **Run the Spider**:
    Navigate to the root `EbayScrapper` directory (the one containing `scrapy.cfg`) and run:
    ```bash
    scrapy crawl main -O output.json --logfile=scrapy_log.txt
    ```
    * This will start the `main` spider.
    * Scraped items will be saved to `output.json` (or other formats like CSV, XML).
    * A detailed log will be written to `scrapy_log.txt`.
    * Downloaded images (if `ImagesPipeline` is configured in `settings.py` and `pipelines.py`) will be stored in `downloaded_images/` (or the path specified in `IMAGES_STORE`).

---

## 📦 Extending the Project

1.  **New Parser Logic**:
    * Adjust CSS/XPath selectors in `MainSpider` if eBay's layout changes or to extract new fields.
2.  **Data Storage**:
    * Enable and configure pipelines in `pipelines.py` and `settings.py` for storing data in databases (e.g., PostgreSQL, MongoDB), cloud storage, etc.
3.  **Middleware Enhancements**:
    * Implement custom middlewares in `middlewares.py` for advanced request/response manipulation, enhanced proxy rotation, or handling specific anti-scraping measures.

---

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 🤝 Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project.

---

### Tor Configuration on Windows (Example)

If you're using Tor on Windows and want to set a specific HTTP tunnel port for applications like this scraper (when `use_tor` is true and `tor_proxy_address` points to an HTTP proxy for Tor, though the code uses a SOCKS proxy by default with `http://` prefix which might be a typo for `socks5://` or it relies on an HTTP to SOCKS bridge like Privoxy):

1.  Locate your Tor Browser's `torrc` file. For Tor Browser Bundle, it's typically in `Tor Browser\Data\Tor\torrc`. If you installed Tor as a service, find its `torrc`.
2.  Add or modify the line for `SocksPort` (for SOCKS proxy, which the spider seems more geared towards) or `HTTPTunnelPort` (if you specifically need an HTTP tunnel *to* the Tor network).
    * For SOCKS (recommended for the spider's current `tor_proxy_address` if it's `http://localhost:9080` but meant for SOCKS, ensure Tor actually listens on 9080 for SOCKS):
        ```
        SocksPort 127.0.0.1:9050
        ```
        (Then update `tor_proxy_address` in spider to `socks5://127.0.0.1:9050`)
    * If you have a setup where an HTTP proxy is fronting Tor's SOCKS proxy (e.g. Privoxy) or if Tor itself is configured to offer an HTTP port:
        ```
        HTTPTunnelPort 127.0.0.1:9080
        ```
3.  Restart Tor for the changes to take effect.
4.  Ensure the spider's `tor_proxy_address` in `main.py` (e.g., `"http://127.0.0.1:9080"` or preferably `socks5://127.0.0.1:9050` if Tor is providing a SOCKS5 proxy) matches your Tor configuration. *Note: The `http://` prefix for a SOCKS port in Scrapy usually implies an HTTP proxy. For direct SOCKS5, it should be `socks5://`.*

---

*Happy scraping!*
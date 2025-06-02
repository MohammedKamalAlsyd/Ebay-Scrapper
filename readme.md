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
* **Error Handling & Logging**: Implements error handlers for request failures and detailed logging for monitoring and debugging.
* **Structured Output**: Utilizes Scrapy Items (`EbayscrapperItem`) for clean and organized data.

---

## ⚙️ Project Structure


📁 EbayScrapper/                      # Root project folder
├── .gitignore                       # Specifies untracked files for Git to ignore
├── scrapy.cfg                       # Scrapy project configuration file
├── requirements.txt                 # Python package dependencies
├── README.md                        # Project documentation
├── CONTRIBUTING.md                  # Contribution guidelines
└── 📁 EbayScrapper/                 # Main Scrapy module (same name as project root)
    ├── __init__.py                  # Makes this directory a Python package
    ├── items.py                     # Defines item classes (e.g., `EbayScrapperItem`)
    ├── middlewares.py               # Custom middlewares (if implemented)
    ├── pipelines.py                 # Defines item pipelines for post-processing
    ├── settings.py                  # Scrapy settings (user agent, pipelines, etc.)
    └── 📁 spiders/                  # Contains spider classes (scraping logic)
        ├── __init__.py              # Marks the spiders directory as a Python package
        └── main.py                  # Main spider implementation (e.g., `MainSpider`)

---

## 🛠 Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/EbayScrapper.git](https://github.com/yourusername/EbayScrapper.git) # Replace with your repo URL
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

The primary configuration for the `MainSpider` is managed through attributes defined directly within the `EbayScrapper/EbayScrapper/spiders/main.py` file.

### Spider Parameters (`EbayScrapper/spiders/main.py`):

* `name = "main"`: The unique name used to identify and run the spider (e.g., `scrapy crawl main`).
* `search_keywords = ["rtx 5090 founder edition"]`: A list of strings, where each string is a keyword phrase to be searched on eBay.
* `use_suggestions = False`: A boolean value. If `True`, the spider will first fetch autocomplete suggestions from eBay for each `search_keyword` and then perform searches for each suggestion. If `False`, it will search directly for the `search_keywords`.
* `suggestion_api_url = "https://autosug.ebaystatic.com/autosug"`: The base URL for eBay's autosuggestion API.
* `suggestion_base_params = {...}`: A dictionary of base parameters sent with each request to the suggestion API.
* `suggestion_url_template = "..."`: A string template used to format the full URL for fetching suggestions, incorporating the `kwd` (keyword) and other `suggestion_base_params`.
* `search_base_url = "https://www.ebay.com/sch/i.html"`: The base URL for eBay's search results page.
* `search_base_params = {...}`: A dictionary of base parameters sent with each search request (e.g., items per page `_ipg`, sort order `_sop`).
* `search_base_url_template = "..."`: A string template used to format the full URL for eBay searches, incorporating `_nkw` (keyword), `_sacat` (category), and other `search_base_params`.
* `allowed_categories = ["0"]`: A list of eBay category IDs. The spider will perform searches within each of these categories for every keyword (or suggestion). "0" typically means "All Categories".
* `use_tor = False`: A boolean value. If `True`, all requests made by the spider will be routed through the Tor proxy specified by `tor_proxy_address`.
* `tor_proxy_address = "http://127.0.0.1:9080"`: The address of the Tor SOCKS proxy. *Note: For Scrapy, if Tor provides a SOCKS5 proxy, the scheme should ideally be `socks5://` (e.g., `socks5://127.0.0.1:9050`). Using `http://` implies an HTTP proxy; ensure your Tor setup matches this or adjust the scheme accordingly.*
* `max_search_pages_per_keyword = 3`: An integer defining the maximum number of search result pages to scrape for each keyword/category combination.
* `custom_settings = {...}`: A dictionary for Scrapy settings specific to this spider, overriding global settings in `settings.py`. This includes Playwright concurrency limits and download delays.
    * `'PLAYWRIGHT_MAX_CONTEXTS': 2`: Limits Playwright to 2 concurrent browser contexts.
    * `'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 2`: Limits to 2 pages per Playwright context.
    * `'CONCURRENT_REQUESTS': 2`: Global Scrapy concurrency, matched to Playwright limits here.
    * `'DOWNLOAD_DELAY': 1`: Adds a 1-second delay between requests.
* `USER_AGENTS = [...]`: A list of user-agent strings. The spider randomly selects one for each request to help mimic diverse organic traffic.

To modify the scraper's behavior, edit these attributes directly in the `main.py` file.

---

## 🚀 Usage

1.  **Configure the Spider**:
    Open `EbayScrapper/EbayScrapper/spiders/main.py` and adjust the parameters (e.g., `search_keywords`, `use_tor`, `max_search_pages_per_keyword`) as needed.

2.  **Run the Spider**:
    Navigate to the root `EbayScrapper` directory (the one containing `scrapy.cfg`) in your terminal and execute:
    ```bash
    scrapy crawl main -O output.json --logfile=scrapy_log.txt
    ```
    * This command starts the `main` spider.
    * Scraped items will be saved to `output.json` in JSON format (other formats like CSV, XML are also supported by Scrapy's feed exports).
    * A detailed log of the scraping process will be written to `scrapy_log.txt`.
    * If the `ImagesPipeline` is enabled and configured in `settings.py` and `pipelines.py`, downloaded images will be stored in the `downloaded_images/` directory (or the path specified by `IMAGES_STORE` in `settings.py`).

---

## 📦 Extending the Project

1.  **Modify Parsing Logic**:
    Adjust CSS/XPath selectors within the `parse_search_results` and `parse_product_page` methods in `MainSpider` if eBay's website structure changes or to extract additional data fields.
2.  **Data Storage**:
    Enable and configure Scrapy pipelines in `pipelines.py` and `settings.py` to store scraped data in databases (e.g., PostgreSQL, MongoDB), cloud storage, or other formats.
3.  **Middleware Enhancements**:
    Implement custom Scrapy middlewares in `middlewares.py` for advanced request/response manipulation, sophisticated proxy rotation strategies, or to handle specific anti-scraping mechanisms.

---

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details (Create a `LICENSE` file with MIT License text if one does not exist).

---

## 🤝 Contributing

Contributions are welcome. Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project.

---

### Tor Configuration on Windows (Example)

If `use_tor` is set to `True`:

1.  Ensure Tor is installed and running.
2.  Locate your Tor Browser's `torrc` file (typically in `Tor Browser\Data\Tor\torrc`) or the `torrc` file for your Tor service.
3.  Confirm or set the `SocksPort`. For example:
    ```
    SocksPort 127.0.0.1:9050
    ```
    If using port `9050`, update `tor_proxy_address` in `main.py` to `socks5://127.0.0.1:9050`. If your Tor setup exposes an HTTP interface on `9080` that tunnels to SOCKS, then `http://127.0.0.1:9080` might be correct, but direct SOCKS is more common for Scrapy.
4.  Restart Tor for changes to take effect.

---

*Happy scraping!*

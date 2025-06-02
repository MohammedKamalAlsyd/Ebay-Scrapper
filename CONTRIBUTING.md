# Contributing to EbayScrapper

First off, thank you for considering contributing to EbayScrapper! Your help is appreciated, and every contribution makes this project better.

This document provides guidelines for contributing to the project. Please read it carefully to ensure a smooth and effective contribution process.

## Ways to Contribute

There are many ways to contribute, including:

* **Reporting Bugs**: If you find a bug, please open an issue in the GitHub repository. Include detailed steps to reproduce the bug, expected behavior, and actual behavior.
* **Suggesting Enhancements**: If you have an idea for a new feature or an improvement to an existing one, open an issue to discuss it.
* **Writing Code**: You can contribute by fixing bugs, implementing new features, or improving existing code.
* **Improving Documentation**: If you find parts of the documentation unclear or incomplete, feel free to suggest changes or submit a pull request.

## Getting Started

1.  **Fork the Repository**:
    Click the "Fork" button at the top right of the [EbayScrapper GitHub page](https://github.com/yourusername/EbayScrapper) to create a copy of the repository under your own GitHub account. (Replace `yourusername/EbayScrapper` with the actual repository URL).

2.  **Clone Your Fork**:
    Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/YOUR_GITHUB_USERNAME/EbayScrapper.git
    cd EbayScrapper
    ```

3.  **Create a Virtual Environment**:
    It's highly recommended to use a virtual environment for development.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate   # On Windows
    ```

4.  **Install Dependencies**:
    Install the project dependencies, including development tools if any.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Install Playwright Browsers**:
    Ensure you have the necessary Playwright browser binaries:
    ```bash
    playwright install
    ```

## Making Changes

1.  **Create a New Branch**:
    Create a new branch for your feature or bugfix. Use a descriptive name (e.g., `feature/new-data-field` or `bugfix/price-parsing-issue`).
    ```bash
    git checkout -b your-branch-name
    ```

2.  **Write Code**:
    * Follow the existing code style. For Python, this generally means adhering to [PEP 8](https://www.python.org/dev/peps/pep-0008/).
    * Ensure your code is well-commented, especially for complex logic.
    * If adding new settings or configurable parameters, consider how they will be managed (e.g., in `settings.py`, `scraper_config.json`, or as spider arguments).
    * Keep your changes focused on the specific feature or bug you are addressing.

3.  **Test Your Changes**:
    * Run the spider locally to ensure your changes work as expected and do not introduce regressions.
    * Test with different keywords or scenarios if applicable.
    * Check the output data and logs for any errors or unexpected behavior.

4.  **Commit Your Changes**:
    Write clear and concise commit messages. A good commit message explains *what* the change is and *why* it was made.
    ```bash
    git add .
    git commit -m "feat: Add extraction for X field"
    # or
    git commit -m "fix: Correct parsing of Y under Z condition"
    ```
    Consider using [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages.

## Submitting Pull Requests

1.  **Push to Your Fork**:
    Push your changes to your forked repository on GitHub:
    ```bash
    git push origin your-branch-name
    ```

2.  **Open a Pull Request (PR)**:
    * Go to the original EbayScrapper repository on GitHub.
    * You should see a prompt to create a Pull Request from your recently pushed branch. Click on it.
    * Ensure the base repository is the original project and the head repository is your fork and branch.
    * Provide a clear title and a detailed description for your PR. Explain the changes you've made and why.
    * If your PR addresses an existing issue, link to it in the description (e.g., "Closes #123").

3.  **Code Review**:
    * Maintainers will review your PR. Be prepared to discuss your changes and make further modifications if requested.
    * Once your PR is approved and passes any checks, it will be merged into the main project.

Thank you for contributing!
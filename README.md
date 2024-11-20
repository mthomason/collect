
# Hobby Report

**Hobby Report** is an example Python project that demonstrates how to create a _Drudge Report_-style website for collectors, called **Hobby Report**, using APIs and automation.

This project is designed as an **example of using OpenAI's Function Calling API**, showcasing its ability to clean up and extract structured data from eBay headlines and parse auction details programmatically. It integrates eBay data, RSS feeds, and other APIs to generate and refresh a fully functional website.

---

## Features

- **OpenAI Function Calling API**: Extract and clean auction data from eBay headlines, showcasing advanced AI capabilities.
- **eBay Integration**: Retrieves and processes eBay auction data.
- **RSS Feed Integration**: Aggregates content from RSS feeds.
- **Site Automation**: Designed to run periodically to keep the site updated with the latest data.
- **Developer Example**: A template for building automated aggregation sites.

---

## Getting Started

### Prerequisites

1. Python **3.12** or higher.
2. A Python virtual environment is strongly recommended.
3. API keys for:
   - **OpenAI** Function Call API
   - **eBay** API (including eBay Partner Network)
   - Optional: AWS or Reddit API keys for additional enhancements.

---

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/hobby-report.git
   cd hobby-report
   ```

2. Create and activate a Python virtual environment:

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

### Configuration

Create a `.env` file in the root directory and populate it with the following variables. Replace the placeholders with your actual API credentials:

```plaintext
################################################################################
#AWS Keys
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

#CloudFront Keys
AWS_CF_DISTRIBUTION_ID = ''

################################################################################
#eBay API Keys
EBAY_APPID = ''
EBAY_DEVID = ''
EBAY_CERTID = ''

################################################################################
#eBay Partner Network Keys
EPN_TRACKING_ID = ''

################################################################################
#OpenAI API Keys
OPENAI_API_KEY = ''

################################################################################
#Reddit API Keys
REDDIT_CLIENT_ID = ''
REDDIT_CLIENT_SECRET = ''
REDDIT_USER_AGENT = ''
```

Edit the configuration files in the `config/` directory to customize sources and settings:

- `rss-feeds.json`: List of RSS feeds to aggregate.
- `auctions-ebay.json`: Filters and categories for eBay auctions.
- `config.json`: General application settings.

---

### Running the Application

Run the project from the command line with the following command:

```bash
cd /path/to/hobby-report/collect
/usr/bin/env /path/to/hobby-report/venv/bin/python -m collect
```

The application will fetch eBay data, read RSS feeds, and generate the website. To automate updates, schedule this command to run periodically (e.g., using `cron` or Task Scheduler).

---

### Debugging in Visual Studio Code

This project includes a preconfigured `launch.json` file for debugging with Visual Studio Code.

1. Open the project in Visual Studio Code.
2. Ensure you have the Python extension installed.
3. Select one of the provided configurations:
   - **Debug Main Module**: Runs and debugs the `collect` module to generate the site.
   - **Run Specific Tests**: Allows debugging of test modules like `test_caching_robot_file_parser`.

Example `launch.json` entry:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Python: __main__.py",
            "type": "python",
            "request": "launch",
            "module": "collect",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "stopOnEntry": false,
            "justMyCode": false
        },
        {
            "name": "Python: Unittest",
            "type": "python",
            "request": "launch",
            "module": "collect.tests.test_caching_robot_file_parser",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

Use the integrated terminal in Visual Studio Code to view debug output and logs.

---

## Screenshot Placeholder

<img src="assets/hobbyrptscreenshot.png" alt="Screenshot Hobby Report" width="320">

---

## Example Use Case: OpenAI Function Calling API

This project is a practical example of leveraging the **OpenAI Function Calling API** for structured data extraction. By processing raw eBay headlines, it demonstrates:

- Cleaning up auction titles for better readability.
- Parsing specific values, like item names or prices, programmatically.
- Automating content aggregation tasks that traditionally required manual effort.

---

## Directory Structure

- **`collect/`**: Core project files.
  - `utility/`: Helper modules for caching, logging, API interaction, and data processing.
  - `tests/`: Unit tests for the application.
  - `core/`: Core functionality like RSS handling, HTML generation, and file management.
- **`config/`**: Configuration files for API settings and RSS feeds.
- **`templates/`**: HTML templates used to render the website.
- **`logs/`**: Application logs for debugging.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

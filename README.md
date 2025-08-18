# QTO Bidirectional Swap Analyzer

!

A Python script to analyze the bidirectional trading volume of a specific ERC-20 token (QTO) across both decentralized (DEX) and centralized (CEX) exchanges over the last 7 days.

---

## Features

-   **📊 Bidirectional Analysis**: Tracks volume for both buying (`Token → QTO`) and selling (`QTO → Token`).
-   **🔗 Multi-Source Aggregation**: Pulls data from DexScreener, Etherscan, and CryptoCompare for comprehensive coverage.
-   **🏢 DEX & CEX Support**: Identifies and aggregates volume from known decentralized and centralized platforms.
-   **📈 Detailed Reporting**: Generates a clean, readable report in the console, breaking down volume by token pair and platform.
-   **🔧 Easy Configuration**: Simply set the token address and your Etherscan API key to get started.

---

## How It Works

The analyzer fetches data through a multi-step process:

1.  **DEX Analysis**:
    -   It queries the **DexScreener API** to find all active trading pairs for the token and their 24-hour volume, which is then extrapolated to 7 days.
    -   It uses the **Etherscan API** to fetch recent on-chain transactions, identifying potential swaps made through known DEX router contracts.
2.  **CEX Analysis**:
    -   It queries the **CryptoCompare API** to find trading volume on major centralized exchanges that list the token.
3.  **Consolidation**:
    -   All data is merged, categorized, and displayed in a final report that summarizes total volume, buy/sell pressure, and the most active trading platforms.

---

## Setup and Usage

Follow these steps to run the analyzer on your local machine.

### Prerequisites

-   Python 3.6+
-   `pip` (Python package installer)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/your-username/qto-swap-analyzer.git](https://github.com/your-username/qto-swap-analyzer.git)
    cd qto-swap-analyzer
    ```

2.  **Install dependencies:**
    The script requires the `requests` library to make API calls.
    ```sh
    pip install requests
    ```

### Configuration

Open the Python script (`analyzer.py`) and update the following variables with your own information:

-   `self.token_address`: The ERC-20 contract address of the token you want to analyze.
-   `self.etherscan_api_key`: Your personal Etherscan API key. You can get one for free from the [Etherscan website](https://etherscan.io/myapikey).

### Running the Script

Execute the script from your terminal:
```sh
python analyzer.py

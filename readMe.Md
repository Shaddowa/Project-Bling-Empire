# Project Bling Empire 

> **⚡ v2 lives in [`v2/`](v2/README.md)** — modern data layer (the pinned yahooquery/yfinance
> below no longer work), Rule #1 valuation with buy-below prices, BUY/HOLD/SELL timing
> signals, and a backtester. Start there; everything below documents the v1 engine.

[Read more about the project vision](/documentation/vision.md)

[Project planning documentation](https://relieved-walker-58b.notion.site/Project-Bling-Empire-dbee9a3b0f1a41febc0098a6e901188c?pvs=4)

## Possible CSV Generation

### Single Ticker CSV
![Untitled (1)](https://github.com/HannaTronsen/Project-Bling-Empire/assets/85925436/a0a22d16-9782-4e14-a3f3-e06bae6c3af6)

### Comparable Ticker CSV
![Untitled (1)](https://github.com/HannaTronsen/Project-Bling-Empire/assets/85925436/c771bbc8-78cf-4141-94e7-b933e9884724)

## Setup

1. python3 -m venv env
2. source env/bin/activate
3. pip3 install -r requirements.txt


## Documentation

### YahooQuery calls and responses that are used in the repository
[Relevant YahooQuery documentation](https://yahooquery.dpguthrie.com/)

We are using YahooQuery python module in this repo. In order to understand what calls are being made and the response that are given back, we document it here. Integration tests against YahooQuery module should be based on what calls we would like our repo to call.

### Linting and Formating
In order to ensure quality of code, it's important to also have a codebase that throughout the project always ensures that all files follow the same coding practices and standards. In this specific project, we are following the PEP8 practices, and currently only utilizes AUTOPEP in combination with a bash script to reinforce clean code. If the source code will be publically available in the future, a more rigid process of ensuring PEP8 code syntax should be put in place.

You can use the commands:
- sh scripts/format.sh runAutoPep #Fixes PEP8 violations

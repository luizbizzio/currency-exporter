# Currency Exporter 💱📈

## Overview 📊

This script collects and exports currency exchange rates to Prometheus. It retrieves the latest exchange rates for various currency pairs, allowing you to monitor currency values and track changes over time.

<div align="center">
   <img src="metrics.png" alt="Metrics" width="500"/>
</div>

## Features 🌟

- **Exchange Rate Collection:** Fetches real-time exchange rates from the AwesomeAPI for a configurable list of currency pairs.

- **Prometheus Integration:** Provides metrics in a format compatible with Prometheus scraping.

- **Flexible Configuration:** Easily configurable to include the currency pairs you are interested in via a config.yaml file.

- **Efficient Performance:** Designed to handle multiple currency pairs with minimal resource usage.

## Configuration ⚙️

### API Configuration:

Update the `config.yaml` file with the currency pairs you want to monitor. The format used is `BASE_CURRENCY-TARGET_CURRENCY`, where:

- **BASE_CURRENCY** is the currency you are converting from.
- **TARGET_CURRENCY** is the currency you are converting to.

Each currency pair should be separated by an underscore. For example, to get the exchange rate from US Dollars (USD) to Brazilian Reais (BRL), you would use `USD_BRL`.

Example `config.yaml`:

   ```yaml
currencies:
  - USD-BRL
  - EUR-BRL
  - GBP-BRL
   ```

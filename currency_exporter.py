import requests
from prometheus_client import start_http_server, Gauge, CollectorRegistry, generate_latest, REGISTRY
import yaml

# Exporter Port
PORT = 7575
URL_TEMPLATE = "https://economia.awesomeapi.com.br/json/last/{}"

class CurrencyCollector:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.gauges = {}
        self.config = self.load_config()
        self.url = URL_TEMPLATE.format(','.join(pair.replace('_', '-') for pair in self.config.get('currencies', [])))

    def load_config(self):
        with open('config.yaml') as file:
            return yaml.safe_load(file)

    def fetch_data(self):
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return response.json()

    def update_gauges(self):
        data = self.fetch_data()
        for key, value in data.items():
            metric_name = f"{value['code']}_{value['codein']}".upper()
            if metric_name not in self.gauges:
                self.gauges[metric_name] = Gauge(metric_name, 'Exchange rate of currencies', ['base_currency', 'currency'], registry=self.registry)
            self.gauges[metric_name].labels(base_currency=value['code'], currency=value['codein']).set(float(value['bid']))

    def collect(self):
        self.update_gauges()
        return self.registry.collect()

def main():
    collector = CurrencyCollector()
    REGISTRY.register(collector)

    start_http_server(PORT)
    print(f'Running on http://localhost:{PORT}')

    import time
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()

import requests
from prometheus_client import start_http_server, Gauge
import yaml

# Exporter Port
PORT = 7575

URL_TEMPLATE = "https://economia.awesomeapi.com.br/json/last/{}"

def load_config():
    with open('config.yaml') as file:
        return yaml.safe_load(file)

def update_gauges(data):
    for key, value in data.items():
        metric_name = f"{value['code']}_{value['codein']}".upper()
        if metric_name not in gauges:
            gauges[metric_name] = Gauge(metric_name, 'Exchange rate of currencies', ['base_currency', 'currency'])
        gauges[metric_name].labels(base_currency=value['code'], currency=value['codein']).set(float(value['bid']))

def main():
    config = load_config()
    url = URL_TEMPLATE.format(','.join(config.get('currencies', [])))
    
    global gauges
    gauges = {}
    
    start_http_server(PORT)
    print(f'Running on http://localhost:{PORT}')
    
    while True:
        update_gauges(requests.get(url, timeout=30).json())

if __name__ == '__main__':
    main()

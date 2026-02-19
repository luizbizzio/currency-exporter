# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Luiz Bizzio
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import logging
import time
import threading
import argparse
from collections import Counter
from typing import Dict, List, Tuple

import requests
import yaml
from prometheus_client import CollectorRegistry
from prometheus_client import Counter as PromCounter
from prometheus_client import Gauge, Info, start_http_server


API_URL_TEMPLATE = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_pair(s: str) -> Tuple[str, str]:
    s = str(s).strip().upper().replace("_", "-")
    parts = s.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(s)
    return parts[0], parts[1]


def pick_pivot(pairs: List[Tuple[str, str]]) -> str:
    counts: Counter[str] = Counter()
    for a, b in pairs:
        counts[a] += 1
        counts[b] += 1
    if "USD" in counts:
        return "USD"
    if not counts:
        return "USD"
    return counts.most_common(1)[0][0]


def setup_logging(level: str) -> None:
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


class CurrencyExporter:
    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config = load_config(config_path)

        server = self.config.get("server") or {}
        self.port = int(server.get("port", 7575))
        self.timeout_seconds = int(server.get("timeout_seconds", 10))
        self.update_interval_seconds = int(server.get("update_interval_seconds", 21600))
        self.retries = int(server.get("retries", 3))
        self.retry_backoff_seconds = float(server.get("retry_backoff_seconds", 1))
        self.expose_default_metrics = bool(server.get("expose_default_metrics", True))
        self.log_level = str(server.get("log_level", "INFO"))

        setup_logging(self.log_level)

        raw_pairs = self.config.get("pairs") or self.config.get("currencies") or []
        valid_pairs: List[Tuple[str, str]] = []
        invalid_pairs: List[str] = []

        seen = set()
        for item in raw_pairs:
            try:
                p = normalize_pair(item)
                if p not in seen:
                    valid_pairs.append(p)
                    seen.add(p)
            except Exception:
                invalid_pairs.append(str(item))

        self.pairs = valid_pairs

        if invalid_pairs:
            logging.warning("Invalid pair format ignored: %s", ", ".join(invalid_pairs))

        if not self.pairs:
            logging.error("No valid pairs found in config.yaml. Exiting.")
            raise SystemExit(2)

        self.pivot = pick_pivot(self.pairs)
        self.api_url = API_URL_TEMPLATE.format(base=self.pivot.lower())

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._last_rates: Dict[str, float] = {}
        self._last_date: str = ""

        self.registry = CollectorRegistry() if not self.expose_default_metrics else None

        metric_kwargs = {} if self.registry is None else {"registry": self.registry}

        self.metric_up = Gauge("currency_exporter_up", "1 if last update succeeded, else 0", **metric_kwargs)
        self.metric_last_update_ts = Gauge("currency_exporter_last_update_timestamp", "Unix timestamp of last update attempt", **metric_kwargs)
        self.metric_last_success_ts = Gauge("currency_exporter_last_success_timestamp", "Unix timestamp of last successful update", **metric_kwargs)
        self.metric_update_duration = Gauge("currency_exporter_update_duration_seconds", "Duration of the last update in seconds", **metric_kwargs)
        self.metric_errors_total = PromCounter("currency_exporter_errors_total", "Total number of update errors", **metric_kwargs)

        self.metric_config_invalid_pairs = Gauge("currency_exporter_config_invalid_pairs", "Number of config pairs that are invalid/missing in current snapshot", **metric_kwargs)
        self.metric_invalid_pairs_total = PromCounter("currency_exporter_invalid_pairs_total", "Total times a config pair was found invalid/missing in snapshot", **metric_kwargs)

        self.metric_snapshot_info = Info("currency_exporter_snapshot", "Snapshot info", **metric_kwargs)
        self.metric_rate = Gauge("currency_exchange_rate", "Exchange rate from base to quote", ["base", "quote"], **metric_kwargs)
        self.metric_pair_supported = Gauge("currency_pair_supported", "1 if pair can be calculated from current snapshot, else 0", ["base", "quote"], **metric_kwargs)

        logging.info("Exporter port=%s pivot=%s url=%s pairs=%s default_metrics=%s", self.port, self.pivot, self.api_url, len(self.pairs), self.expose_default_metrics)

    def fetch_snapshot(self) -> Tuple[str, Dict[str, float]]:
        last_exc = None
        attempts = max(1, self.retries)

        for i in range(attempts):
            try:
                r = requests.get(self.api_url, timeout=self.timeout_seconds)
                r.raise_for_status()
                data = r.json()

                date = str(data.get("date") or "").strip()
                block = data.get(self.pivot.lower())
                if not isinstance(block, dict):
                    raise ValueError("invalid_payload")

                rates: Dict[str, float] = {self.pivot: 1.0}
                for k, v in block.items():
                    try:
                        rates[str(k).upper()] = float(v)
                    except Exception:
                        continue

                return date, rates
            except Exception as e:
                last_exc = e
                if i < attempts - 1:
                    time.sleep(self.retry_backoff_seconds * (2 ** i))

        raise last_exc if last_exc else RuntimeError("fetch_snapshot failed")

    def recompute_metrics(self) -> None:
        with self._lock:
            rates = dict(self._last_rates)
            date = self._last_date

        if not rates:
            return

        self.metric_snapshot_info.info({"date": date or "unknown", "pivot": self.pivot})

        invalid_now = 0

        for a, b in self.pairs:
            ra = rates.get(a)
            rb = rates.get(b)
            if ra is None or rb is None or ra == 0:
                self.metric_pair_supported.labels(base=a, quote=b).set(0)
                invalid_now += 1
                continue

            self.metric_rate.labels(base=a, quote=b).set(rb / ra)
            self.metric_pair_supported.labels(base=a, quote=b).set(1)

        self.metric_config_invalid_pairs.set(invalid_now)

        if invalid_now > 0:
            self.metric_invalid_pairs_total.inc()
            logging.warning("Config has %s invalid pair(s) for current snapshot (pivot=%s)", invalid_now, self.pivot)

    def update_once(self) -> None:
        start = time.time()
        self.metric_last_update_ts.set(start)

        try:
            date, rates = self.fetch_snapshot()
            with self._lock:
                self._last_rates = rates
                self._last_date = date
            self.metric_up.set(1)
            self.metric_last_success_ts.set(time.time())
        except Exception as e:
            self.metric_up.set(0)
            self.metric_errors_total.inc()
            logging.error("Update failed pivot=%s url=%s error=%s", self.pivot, self.api_url, repr(e))
        finally:
            self.metric_update_duration.set(max(0.0, time.time() - start))

        self.recompute_metrics()

    def loop(self) -> None:
        self.update_once()
        while not self._stop.wait(self.update_interval_seconds):
            self.update_once()

    def run(self) -> None:
        if self.registry is None:
            start_http_server(self.port)
        else:
            start_http_server(self.port, registry=self.registry)

        t = threading.Thread(target=self.loop, daemon=True)
        t.start()

        while True:
            time.sleep(3600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-file",
        default="config.yaml",
        dest="config_file",
    )
    args = parser.parse_args()
    CurrencyExporter(config_path=args.config_file).run()


if __name__ == "__main__":
    main()


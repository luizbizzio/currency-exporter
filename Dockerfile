FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV CURRENCY_EXCHANGE_EXPORTER_CONFIG=/config/config.yaml

WORKDIR /app

RUN groupadd -g 10001 app && useradd -u 10001 -g 10001 -m -s /usr/sbin/nologin app
RUN mkdir -p /config && chown -R app:app /config

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY currency_exchange_exporter.py /app/currency_exchange_exporter.py

EXPOSE 9131

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,sys,yaml,urllib.request; p=9131; path=os.environ.get('CURRENCY_EXCHANGE_EXPORTER_CONFIG','/config/config.yaml'); \
  try: cfg=yaml.safe_load(open(path,'r',encoding='utf-8')) or {}; p=int(((cfg.get('server') or {}).get('port')) or p); \
  except Exception: pass; \
  u=f'http://127.0.0.1:{p}/metrics'; \
  d=urllib.request.urlopen(u,timeout=3).read().decode('utf-8','ignore'); \
  sys.exit(0 if 'currency_exchange_exporter_up' in d else 1)"

USER app

ENTRYPOINT ["python", "/app/currency_exchange_exporter.py"]
CMD ["--config-file", "/config/config.yaml"]

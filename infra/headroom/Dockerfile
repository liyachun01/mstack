FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
LABEL org.opencontainers.image.title="mstack shared Headroom" \
      org.opencontainers.image.version="0.34.0" \
      org.opencontainers.image.source="https://github.com/headroomlabs-ai/headroom"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    TIKTOKEN_CACHE_DIR=/opt/tokenizer-cache DO_NOT_TRACK=1 HEADROOM_BEACON=off
COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --only-binary=:all: --require-hashes -r /tmp/requirements.lock \
    && python -m pip check \
    && python -c 'import tiktoken; tiktoken.get_encoding("cl100k_base"); tiktoken.get_encoding("o200k_base")' \
    && chmod -R a+rX /opt/tokenizer-cache
ENV HEADROOM_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True HEADROOM_MCP_READ=off
WORKDIR /runtime
USER 501:501
ENTRYPOINT ["python"]
CMD ["-c", "import time; time.sleep(2147483647)"]

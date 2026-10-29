FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS builder
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
WORKDIR /build
ADD --checksum=sha256:ccf9fe88fee925a26c181b5e1f1582d1aaac1430c2be1e3779c45f0c434e138d https://raw.githubusercontent.com/Graphify-Labs/graphify/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/uv.lock /build/uv.lock
ADD --checksum=sha256:51ea326f1dad916e838164612210a00291f8c3180ba79bf1cdebc8a874a9f1e2 https://raw.githubusercontent.com/Graphify-Labs/graphify/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/pyproject.toml /build/pyproject.toml
ADD --checksum=sha256:fcd28fd87972f677f0e12d577842deb5d445adf36bcd4cd1ebaaec4c67788d7f https://files.pythonhosted.org/packages/c2/5a/09c78f5864c33958cd6d2682f71cd03d44265669a5c3cd426abecc369000/uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl /tmp/uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl
ADD --checksum=sha256:d193dcc43b07c9534826277fc92c8e54dc22aba102d58aaf424494a0906216c5 https://files.pythonhosted.org/packages/2d/4b/1b96b22bd263447cfaa326a029543891369f4b5b484ec59f963b6cfb02fe/graphifyy-0.9.72-py3-none-any.whl /tmp/graphifyy-0.9.72-py3-none-any.whl
RUN python -m pip install --no-cache-dir --no-deps /tmp/uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl \
    && uv sync --frozen --no-dev --extra mcp --no-install-project --no-build \
    && uv pip install --python /opt/venv/bin/python --no-deps --no-build /tmp/graphifyy-0.9.72-py3-none-any.whl \
    && uv pip check --python /opt/venv/bin/python

FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
LABEL org.opencontainers.image.title="mcp-stack Graphify" \
      org.opencontainers.image.version="0.9.72" \
      org.opencontainers.image.source="https://github.com/Graphify-Labs/graphify" \
      org.opencontainers.image.revision="1cd9a36c0c57a661d2d2234bc3207e887e1ba104"
COPY --from=builder /opt/venv /opt/venv
RUN mkdir -p /home/developer/workspace/mcp-stack/scripts \
    /home/developer/workspace/mcp-stack/infra/graphify/fixtures /state
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /home/developer/workspace/mcp-stack
USER 501:501
ENTRYPOINT ["/opt/venv/bin/python"]
CMD ["-c", "import importlib.metadata as m; print(m.version('graphifyy'))"]

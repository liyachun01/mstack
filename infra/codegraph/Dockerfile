FROM node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203 AS bundle

# BuildKit verifies the approved release asset before extraction.
ADD --checksum=sha256:3e31bfd645416ab4e34516a9fe444a907132b3527b18889c877148219cdcc966 https://github.com/colbymchenry/codegraph/releases/download/v1.6.1/codegraph-linux-arm64.tar.gz /tmp/codegraph.tar.gz
RUN mkdir -p /opt/codegraph \
    && tar -xzf /tmp/codegraph.tar.gz --strip-components=1 -C /opt/codegraph

FROM node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203
LABEL org.opencontainers.image.title="mcp-stack CodeGraph" \
      org.opencontainers.image.version="1.6.1" \
      org.opencontainers.image.source="https://github.com/colbymchenry/codegraph" \
      org.opencontainers.image.revision="f4ddf508516332419ea3c95702810765936cf679"
COPY --from=bundle /opt/codegraph /opt/codegraph
RUN mkdir -p /home/developer/workspace/mcp-stack/scripts \
    /home/developer/workspace/mcp-stack/infra/codegraph/fixtures \
    /home/developer/workspace/mcp-stack/.codegraph /state
WORKDIR /home/developer/workspace/mcp-stack
USER 501:501
ENTRYPOINT ["/opt/codegraph/bin/codegraph"]
CMD ["--version"]

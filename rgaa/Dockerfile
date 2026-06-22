FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx beautifulsoup4 lxml

COPY core/mcp_ref_core/ ./mcp_ref_core/
COPY rgaa/files/ ./files/
COPY rgaa/tokens/.gitkeep ./tokens/.gitkeep

VOLUME ["/app/tokens"]

ENV PYTHONPATH=/app
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python files/rgaa_mcp.py --health || exit 1

ENTRYPOINT ["python", "files/rgaa_mcp.py"]

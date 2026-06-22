FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx

COPY core/mcp_ref_core/ ./mcp_ref_core/
COPY greenit/files/greenit_mcp.py .
COPY greenit/files/data.py .
COPY greenit/files/greenit_cache.json .
COPY greenit/files/greenit_metadata.json .

ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python greenit_mcp.py --health

ENTRYPOINT ["python", "greenit_mcp.py"]

FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set npm global prefix explicitly so we know exactly where packages go
RUN npm config set prefix /usr/local

# Install Playwright + Chromium
RUN npx -y playwright install --with-deps chromium

# Pre-install Playwright MCP at pinned version
RUN npm install -g @playwright/mcp@0.0.74

# Verify installation and print path
RUN echo "=== NPM Global Root ===" && \
    npm root -g && \
    echo "=== MCP CLI Location ===" && \
    find /usr/local -name "cli.js" -path "*playwright*mcp*" 2>/dev/null && \
    echo "=== Done ==="

# Install Python package manager
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN uv pip install --system \
    fastapi \
    uvicorn \
    openai-agents \
    boto3 \
    python-dotenv \
    httpx \
    pydantic \
    litellm \
    yfinance


    
# Copy application code
COPY *.py ./

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
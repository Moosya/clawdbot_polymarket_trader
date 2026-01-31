FROM ghcr.io/railwayapp/nixpacks:ubuntu-1745885067

WORKDIR /app/

COPY . /app/

# Set up Python virtual environment in a different location
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r requirements.txt

# Install Node.js dependencies
RUN npm install --include=dev

# Build TypeScript
RUN npx -p typescript tsc --project .

# Start the application
CMD ["node", "dist/trading.js", "gateway", "start"]
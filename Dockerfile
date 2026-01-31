FROM ghcr.io/railwayapp/nixpacks:ubuntu-1745885067

WORKDIR /app/

COPY . /app/

# Set up Python virtual environment
RUN apt-get update && \
       apt-get install -y python3 python3-pip python3-venv && \
       apt-get clean
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r requirements.txt

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
       apt-get install -y nodejs

# Install Node.js dependencies
RUN RUN npm install && npm run build

# Build TypeScript
RUN npx -p typescript tsc --project .

# Start the application
CMD ["node", "dist/trading.js", "gateway", "start"]
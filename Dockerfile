# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Stage 2: Final Python image
FROM python:3.12-slim

# Set up non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Copy built frontend from Stage 1
COPY --chown=user --from=frontend-builder /app/web/dist ./web/dist

# Expose Hugging Face Spaces default port
EXPOSE 7860

# Run the unified start script
CMD ["bash", "start.sh"]

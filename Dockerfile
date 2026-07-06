FROM python:3.12-slim

# Set up non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application (including DB files)
COPY --chown=user . .

# Expose Streamlit's port (Hugging Face Spaces default)
EXPOSE 7860

# Run the unified start script
CMD ["bash", "start.sh"]

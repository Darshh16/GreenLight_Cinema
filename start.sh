#!/bin/bash

# Start FastAPI backend in the background
uvicorn greenlight.api.main:app --host 0.0.0.0 --port 8000 &

# Wait a moment for API to initialize
sleep 2

# Start Streamlit on port 7860 (required by Hugging Face Spaces)
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0

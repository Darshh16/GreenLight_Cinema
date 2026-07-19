#!/bin/bash

# Start FastAPI backend (which now also serves the React frontend)
# We use port 7860 because it is the default required by Hugging Face Spaces.
uvicorn greenlight.api.main:app --host 0.0.0.0 --port 7860

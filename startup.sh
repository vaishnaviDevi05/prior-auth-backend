#!/bin/bash
# Entrypoint for Heroku to run both Streamlit and FastAPI backend using Honcho
pip install -r requirements.txt --quiet
honcho start

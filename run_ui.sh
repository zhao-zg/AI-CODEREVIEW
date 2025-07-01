#!/bin/bash
echo "Starting AI-CodeReview UI..."
echo "UI will automatically read configuration from .env file"
cd "$(dirname "$0")"
python ui.py

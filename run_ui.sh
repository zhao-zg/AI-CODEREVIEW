#!/bin/bash
echo "Starting AI-CodeReview UI..."
cd "$(dirname "$0")"
python -m streamlit run ui.py --server.headless false --server.port 8501

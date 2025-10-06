#!/bin/bash

echo "Updating yt-dlp to the latest version..."
pip install --upgrade yt-dlp

echo "Starting video-crawler service..."
exec python main.py "$@"
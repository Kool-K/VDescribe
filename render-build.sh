#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg (Render's Ubuntu-based environment allows this)
mkdir -p ffmpeg
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ -C ffmpeg --strip-components 1
export PATH=$PATH:$(pwd)/ffmpeg
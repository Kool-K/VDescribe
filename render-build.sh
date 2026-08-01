#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Create a local bin directory for standalone binaries
mkdir -p .local_bin

# Install FFmpeg
echo "Downloading FFmpeg..."
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ -C .local_bin --strip-components 1

# Install Deno (Required by yt-dlp as a JS runtime for YouTube bot bypass)
echo "Downloading Deno..."
curl -L https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip -o deno.zip
python3 -c "import zipfile; zipfile.ZipFile('deno.zip', 'r').extractall('.local_bin')"
rm deno.zip
chmod +x .local_bin/deno

echo "Build script completed successfully."
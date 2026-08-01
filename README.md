# VDescribe — AI-Powered Video Summarization

**VDescribe** is a brutalist-themed web application that extracts key insights from YouTube videos using multimodal AI. Paste a YouTube link, choose a language, and get a structured summary with highlights, a detailed analysis, and a quick insight — in seconds.

## Features

- **Multimodal AI Analysis** — Downloads audio via `yt-dlp` and processes it with Google Gemini for deep content understanding.
- **Multilingual Output** — Supports English, Hindi, and Marathi translations via Sarvam AI.
- **Structured Summaries** — Returns 4 key highlights, a multi-paragraph summary, and a quick 1-sentence insight.
- **Video Metadata** — Fetches video title and thumbnail via the YouTube Data API.
- **Copy to Clipboard** — One-click copy of the full analysis with proper formatting.
- **Brutalist UI** — A bold, high-contrast design built with Tailwind CSS and Space Grotesk typography.

## Tech Stack

| Layer      | Technology                                       |
|------------|--------------------------------------------------|
| Frontend   | HTML, Vanilla JS, Tailwind CSS (CDN)             |
| Backend    | Python, FastAPI, Uvicorn                         |
| AI Engine  | Google Gemini (`gemini-3-flash-preview`)         |
| Translation| Sarvam AI Translate API                          |
| Audio      | yt-dlp + FFmpeg                                  |

## Prerequisites

- **Python 3.10+**
- **FFmpeg** — Required for audio extraction. ([Install Guide](https://ffmpeg.org/download.html))
- **API Keys**:
  - `GEMINI_API_KEY` — [Get one from Google AI Studio](https://aistudio.google.com/apikey)
  - `SARVAM_API_KEY` — [Get one from Sarvam AI](https://www.sarvam.ai/)
  - `YOUTUBE_API_KEY` *(optional)* — [Google Cloud Console](https://console.cloud.google.com/) for video metadata

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/VDescribe.git
cd VDescribe

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with your API keys
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key
# Optional: comma-separated fallback order for temporary Gemini 429/503 errors
GEMINI_MODELS=gemini-3.6-flash,gemini-3.5-flash-lite
SARVAM_API_KEY=your_sarvam_api_key
YOUTUBE_API_KEY=your_youtube_api_key
EOF

# 5. Run the development server
python3 main.py
```

The app will be available at **http://localhost:8000**.

## Deployment on Render

This project is configured for deployment on [Render](https://render.com) as a **Web Service**.

### Setup

1. Push the repo to GitHub.
2. Create a new **Web Service** on Render and connect the GitHub repo.
3. Configure the service:

| Setting         | Value                                |
|-----------------|--------------------------------------|
| **Runtime**     | Python                               |
| **Build Command** | `bash render-build.sh`             |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. Add the following **Environment Variables** in the Render dashboard:

| Variable          | Description                        |
|-------------------|------------------------------------|
| `GEMINI_API_KEY`  | Your Google Gemini API key         |
| `SARVAM_API_KEY`  | Your Sarvam AI API key             |
| `YOUTUBE_API_KEY` | Your YouTube Data API key          |
| `PYTHON_VERSION`  | `3.11` (recommended)               |

5. Deploy. Render will automatically run `render-build.sh` to install dependencies and FFmpeg.

## Project Structure

```
VDescribe/
├── main.py              # FastAPI backend (API, AI, translation)
├── index.html           # Frontend UI
├── script.js            # Client-side interactivity & Tailwind config
├── styles.css           # Custom styles
├── requirements.txt     # Python dependencies
├── render-build.sh      # Render build script (installs deps + FFmpeg)
├── .env                 # API keys (not committed)
└── .gitignore
```

## API Reference

### `POST /summarize`

| Parameter  | Type   | Description                              |
|------------|--------|------------------------------------------|
| `url`      | string | YouTube video URL                        |
| `language` | string | Output language: `English`, `Hindi`, `Marathi` |

**Response:**
```json
{
  "highlights": ["...", "...", "...", "..."],
  "summary": "<p>...</p><p>...</p>",
  "quick_insight": "A 1-sentence insight (always English)",
  "title": "Video Title",
  "thumbnail_url": "https://..."
}
```

## License

This project is open source under the [MIT License](LICENSE).

---

**Built by [Ketaki Kulkarni](https://kool-k.github.io/Ketaki_Kulkarni_Portfolio/)**

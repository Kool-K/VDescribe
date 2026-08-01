# VDescribe — AI-Powered Video Summarization

**VDescribe** is a brutalist-themed web application that extracts key insights from YouTube videos using multimodal AI. Paste a YouTube link, choose a language (English, Hindi, Marathi), and get a structured summary with timestamped highlights, key takeaways, a detailed analysis, and a quick insight — in seconds.

## Features

- **True Multimodal AI Analysis** — Automatically downloads video/audio via `yt-dlp` and processes it with Google's modern `google-genai` SDK:
  - **Videos $\le$ 30 mins**: Downloads low-res MP4 for true visual + audio multimodal analysis (inspecting slides, code, diagrams, and spoken audio).
  - **Videos > 30 mins**: Automatically falls back to audio-only processing to optimize speed and bandwidth.
- **Resilient AI Model Retry & Fallback** — Uses model fallback (`gemini-3.6-flash` $\rightarrow$ `gemini-3.5-flash-lite`) with exponential backoff and jitter to seamlessly handle rate limits (429/503).
- **Multilingual Output** — Supports English, Hindi (`hi-IN`), and Marathi (`mr-IN`) translations via Sarvam AI API.
- **Structured Output (Pydantic & JSON Schema)**:
  - **Timestamped Highlights** — Exactly 4 key moments with `MM:SS` timestamps.
  - **Key Points** — 5 concise, standalone takeaways complementing the highlights.
  - **Detailed Summary** — Multi-paragraph HTML formatted summary.
  - **Quick Insight** — 1-sentence core takeaway.
- **Video Metadata & Scraping Fallback** — Fetches video title and high-res thumbnail via YouTube Data API v3 (with automatic HTML title scraping fallback if API key is not present).
- **Copy to Clipboard & Share** — One-click copy formatted output or share via Web Share API.
- **Brutalist UI** — High-contrast design built with Tailwind CSS and Space Grotesk typography.

## Tech Stack

| Layer      | Technology                                       |
|------------|--------------------------------------------------|
| Frontend   | HTML5, Vanilla JavaScript, Tailwind CSS          |
| Backend    | Python 3.11+, FastAPI, Uvicorn                   |
| AI Engine  | Google Gemini (`google-genai` SDK with fallback) |
| Translation| Sarvam AI Translate API (`sarvam-translate:v1`)  |
| Audio/Video| `yt-dlp` + static `FFmpeg`                       |

## Prerequisites

- **Python 3.10+**
- **FFmpeg** — Required for audio extraction. ([Install Guide](https://ffmpeg.org/download.html))
- **API Keys**:
  - `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey)
  - `SARVAM_API_KEY` — [Sarvam AI](https://www.sarvam.ai/)
  - `YOUTUBE_API_KEY` *(optional)* — [Google Cloud Console](https://console.cloud.google.com/)

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/Kool-K/VDescribe.git
cd VDescribe

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with your API keys
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key
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

### Render Configuration

1. Push the repository to GitHub.
2. Create a new **Web Service** on Render and connect your repository.
3. Configure the service settings:

| Setting         | Value                                |
|-----------------|--------------------------------------|
| **Runtime**     | Python                               |
| **Branch**      | `main`                               |
| **Build Command** | `bash render-build.sh`             |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. Add the following **Environment Variables** in the Render dashboard:

| Variable          | Description                        |
|-------------------|------------------------------------|
| `GEMINI_API_KEY`  | Google Gemini API key              |
| `SARVAM_API_KEY`  | Sarvam AI API key                  |
| `YOUTUBE_API_KEY` | YouTube Data API key *(optional)*  |
| `PYTHON_VERSION`  | `3.11`                             |

5. Deploy! Render executes `render-build.sh` to install dependencies and configure `FFmpeg`.

## Project Structure

```
VDescribe/
├── main.py              # FastAPI backend (multimodal AI, retries, translation)
├── index.html           # Brutalist UI frontend
├── script.js            # Client logic, rendering, copy & share handlers
├── styles.css           # Custom styles & brutalist styling
├── requirements.txt     # Python dependencies
├── render-build.sh      # Render build script (installs deps + static FFmpeg)
├── .env                 # Local API keys (ignored by git)
└── .gitignore
```

## API Reference

### `POST /summarize`

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=EXAMPLE_ID",
  "language": "English"
}
```

**Response:**
```json
{
  "highlights": [
    { "timestamp": "01:15", "text": "Intro and key concept overview" },
    { "timestamp": "04:30", "text": "Deep dive into model architecture" }
  ],
  "key_points": [
    "Takeaway 1 explaining core concept",
    "Takeaway 2 regarding practical implementation"
  ],
  "summary": "<p>Detailed first paragraph...</p><p>Second paragraph...</p>",
  "quick_insight": "A powerful 1-sentence insight.",
  "title": "Video Title",
  "thumbnail_url": "https://...",
  "video_id": "EXAMPLE_ID",
  "is_multimodal": true,
  "model_used": "gemini-3.6-flash"
}
```

## License

This project is open source under the [MIT License](LICENSE).

---

**Built by [Ketaki Kulkarni](https://github.com/Kool-K)**


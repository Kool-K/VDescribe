# VDescribe — AI-Powered Video Summarization

**VDescribe** is a brutalist-themed web application that extracts key insights from YouTube videos using multimodal AI. Paste a YouTube link, choose a language (English, Hindi, Marathi), and get a structured summary with timestamped highlights, key takeaways, a detailed analysis, and a quick insight — in seconds.

> [!IMPORTANT]
> **Local-Host Only Project:** Due to YouTube's aggressive anti-bot protections, cloud data center IPs (like Render, AWS, Heroku) are hard-blocked from downloading YouTube media. **This project must be run locally on your own machine** where your IP matches your browser cookies.

## Features

- **True Multimodal AI Analysis** — Automatically downloads video/audio via `yt-dlp` and processes it with Google's modern `google-genai` SDK:
  - **Videos $\le$ 30 mins**: Downloads low-res MP4 for true visual + audio multimodal analysis (inspecting slides, code, diagrams, and spoken audio).
  - **Videos > 30 mins**: Automatically falls back to audio-only processing to optimize speed and bandwidth.
- **Bot Bypass via Cookies** — Authenticates as a real user via a `YOUTUBE_COOKIES` environment variable to bypass YouTube's bot detection.
- **Resilient AI Model Retry & Fallback** — Uses model fallback (`gemini-3.6-flash` $\rightarrow$ `gemini-3.5-flash-lite`) with exponential backoff and jitter to seamlessly handle rate limits.
- **Multilingual Output** — Supports English, Hindi (`hi-IN`), and Marathi (`mr-IN`) translations via Sarvam AI API.
- **Structured Output (Pydantic & JSON Schema)**:
  - **Timestamped Highlights** — Exactly 4 key moments with `MM:SS` timestamps.
  - **Key Points** — 5 concise, standalone takeaways complementing the highlights.
  - **Detailed Summary** — Multi-paragraph HTML formatted summary.
  - **Quick Insight** — 1-sentence core takeaway.
- **Embedded Player** — View the summarized video directly in the app and click timestamps to seek to the exact moment.
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
- **API Keys & Cookies**:
  - `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com/apikey)
  - `SARVAM_API_KEY` — [Sarvam AI](https://www.sarvam.ai/)
  - `YOUTUBE_API_KEY` *(optional)* — [Google Cloud Console](https://console.cloud.google.com/)
  - `YOUTUBE_COOKIES` — Export your YouTube cookies using a browser extension (like *Get cookies.txt LOCALLY*) to bypass bot detection.

## Local Development (Required)

Because of YouTube's IP restrictions, **VDescribe cannot be hosted on cloud platforms like Render**. Follow these steps to run it on your own machine.

```bash
# 1. Clone the repository
git clone https://github.com/Kool-K/VDescribe.git
cd VDescribe

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with your API keys and YouTube Cookies
cat > .env << 'EOF'
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODELS=gemini-3.6-flash,gemini-3.5-flash-lite
SARVAM_API_KEY=your_sarvam_api_key
YOUTUBE_API_KEY=your_youtube_api_key

# Paste your exported YouTube cookies in Netscape format here:
YOUTUBE_COOKIES="# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	1752000000	LOGIN_INFO	AFmmF2s..."
EOF

# 5. Run the server
python main.py
```

The app will be available at **http://localhost:8000**.

## Project Structure

```
VDescribe/
├── main.py              # FastAPI backend (multimodal AI, retries, translation)
├── index.html           # Brutalist UI frontend
├── script.js            # Client logic, rendering, player & timestamp handlers
├── styles.css           # Custom styles & brutalist styling
├── requirements.txt     # Python dependencies
├── .env                 # Local API keys and cookies (ignored by git)
└── .gitignore
```

## License

This project is open source under the [MIT License](LICENSE).

---

**Built by [Ketaki Kulkarni](https://github.com/Kool-K)**

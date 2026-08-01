import os
import json
import requests
import re
import time
import random
from urllib.parse import urlparse, parse_qs
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# A higher-capability model is tried first. If Gemini is temporarily under
# heavy load, the app retries once and then falls back to a stable multimodal
# model. This order can be changed from .env without modifying code.
GEMINI_MODELS = tuple(
    model.strip()
    for model in os.getenv(
        "GEMINI_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite"
    ).split(",")
    if model.strip()
)
GEMINI_ATTEMPTS_PER_MODEL = 2

# Initialize the modern google-genai client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment.")

app = FastAPI(title="VDescribe API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Structured Output ---

class Highlight(BaseModel):
    """A single key highlight from the video with its timestamp."""
    timestamp: str = Field(description="Timestamp in MM:SS format where this highlight occurs in the video, e.g. '02:15'. Use '00:00' if uncertain.")
    text: str = Field(description="A concise, informative highlight sentence.")

class VideoAnalysis(BaseModel):
    """Structured analysis of a video."""
    highlights: list[Highlight] = Field(description="Exactly 4 key highlights from the video, each with a timestamp.")
    key_points: list[str] = Field(description="Exactly 5 concise, standalone key points that explain the most useful concepts, facts, or takeaways from the video. Do not include timestamps.")
    summary: str = Field(description="A detailed multi-paragraph summary of the video content. Use <p> tags to separate paragraphs, e.g. '<p>First paragraph...</p><p>Second paragraph...</p>'")
    quick_insight: str = Field(description="A powerful, memorable 1-sentence insight distilled from the video.")

# --- Request Model ---

class SummarizeRequest(BaseModel):
    url: str
    language: str

# --- Helper Functions ---

def get_transcript(video_id: str) -> str:
    """
    Fetch the transcript for a YouTube video using youtube-transcript-api.
    Tries English first, then any available language.
    Returns formatted transcript text with approximate timestamps.
    """
    try:
        # Try to get English transcript first, then fall back to any available
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN'])
        except NoTranscriptFound:
            # Fall back to the first available transcript (auto-generated or manual)
            transcript = transcript_list.find_generated_transcript(['en'])

        raw = transcript.fetch()

        # Format with timestamps so Gemini can generate highlights with MM:SS
        lines = []
        for entry in raw:
            secs = int(entry.get('start', 0))
            mm, ss = divmod(secs, 60)
            text = entry.get('text', '').replace('\n', ' ').strip()
            if text:
                lines.append(f"[{mm:02d}:{ss:02d}] {text}")

        return '\n'.join(lines)

    except TranscriptsDisabled:
        raise HTTPException(
            status_code=422,
            detail="This video has transcripts disabled. Please try a different video."
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not fetch transcript for this video: {str(e)}. Try a video with captions enabled."
        )

def get_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            p = parse_qs(parsed_url.query)
            return p.get('v', [None])[0]
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        if parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    return None





def get_video_metadata(video_id: str) -> dict:
    """Fetch video metadata using YouTube Data API with fallback scraping."""
    title = "Video Summary"
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    if YOUTUBE_API_KEY:
        try:
            url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("items"):
                snippet = data["items"][0]["snippet"]
                title = snippet.get("title", title)
                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = thumbnails.get("maxres", {}).get("url") or \
                                thumbnails.get("high", {}).get("url") or \
                                thumbnails.get("medium", {}).get("url") or \
                                thumbnails.get("default", {}).get("url") or thumbnail_url
                return {"title": title, "thumbnail_url": thumbnail_url}
        except Exception as e:
            print(f"YouTube API Error: {e}, falling back to scraping")

    # Fallback: scrape title
    try:
        response = requests.get(f"https://www.youtube.com/watch?v={video_id}")
        if response.status_code == 200:
            start = response.text.find("<title>")
            end = response.text.find("</title>")
            if start != -1 and end != -1:
                title_raw = response.text[start+7:end]
                title = title_raw.replace(" - YouTube", "").strip()
    except Exception as e:
        print(f"Fallback scraping error: {e}")

    return {"title": title, "thumbnail_url": thumbnail_url}


def translate_with_sarvam(text: str, target_lang_code: str) -> str:
    """Translate text using Sarvam AI API."""
    if not SARVAM_API_KEY:
        print("WARNING: SARVAM_API_KEY is not set.")
        return text

    url = "https://api.sarvam.ai/translate"
    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": target_lang_code,
        "speaker_gender": "Male",
        "mode": "formal",
        "model": "sarvam-translate:v1"
    }
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": SARVAM_API_KEY
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        translated = data.get("translated_text", text)
        return translated if isinstance(translated, str) else translated[0]
    except Exception as e:
        print(f"Sarvam translation error: {e}")
        return text  # Fallback to original text


def is_transient_gemini_error(error: Exception) -> bool:
    """Return True only for failures that are safe to retry or fail over."""
    error_text = str(error).upper()
    transient_markers = (
        "429", "408", "500", "502", "503", "504",
        "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL",
        "DEADLINE_EXCEEDED", "TIMEOUT",
    )
    return any(marker in error_text for marker in transient_markers)


def generate_with_gemini_fallback(contents, config):
    """Retry transient Gemini failures, then move to the next model."""
    errors = []

    for model in GEMINI_MODELS:
        for attempt in range(GEMINI_ATTEMPTS_PER_MODEL):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                print(f"Gemini generation succeeded with {model}.")
                return response, model
            except Exception as error:
                errors.append(f"{model}: {error}")

                # Invalid requests, keys, and permissions won't be fixed by
                # waiting or switching models.
                if not is_transient_gemini_error(error):
                    raise

                if attempt < GEMINI_ATTEMPTS_PER_MODEL - 1:
                    # Exponential backoff with jitter (per Gemini guidance).
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(
                        f"Gemini {model} failed temporarily; retrying in "
                        f"{delay:.1f}s ({attempt + 1}/{GEMINI_ATTEMPTS_PER_MODEL})."
                    )
                    time.sleep(delay)

        print(f"Gemini {model} is unavailable; trying the next fallback model.")

    raise RuntimeError(
        "All configured Gemini models are temporarily unavailable. "
        "Please try again in a minute. Details: " + " | ".join(errors)
    )


# --- Main Endpoint ---

@app.post("/summarize")
async def summarize(request: SummarizeRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key is not configured.")

    video_id = get_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

    # 1. Fetch transcript using youtube-transcript-api (no download, no bot blocking)
    transcript_text = get_transcript(video_id)

    # 2. Summarize with Gemini using structured output
    try:
        prompt = f"""You are a professional video analyst. Below is the full timestamped transcript of a YouTube video. Analyse it carefully and provide a comprehensive analysis.

For each highlight, use the timestamp format [MM:SS] already present in the transcript to identify exactly when each key topic occurs.

Provide exactly 4 key highlights with timestamps, exactly 5 concise key points (without timestamps), a detailed multi-paragraph summary using <p> HTML tags, and a powerful 1-sentence quick insight. Make the key points practical takeaways that complement, rather than repeat, the timestamped highlights.

Focus on the spoken content, arguments, and discussion points in the transcript.

--- TRANSCRIPT ---
{transcript_text}
--- END OF TRANSCRIPT ---"""

        response, model_used = generate_with_gemini_fallback(
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideoAnalysis,
            ),
        )

        result = json.loads(response.text)

        # Normalize: ensure highlights are objects with timestamp/text
        if isinstance(result.get("highlights"), list):
            normalized = []
            for h in result["highlights"]:
                if isinstance(h, dict):
                    normalized.append(h)
                elif isinstance(h, str):
                    normalized.append({"timestamp": "00:00", "text": h})
            result["highlights"] = normalized

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    result["is_multimodal"] = False

    # 3. Translate with Sarvam if needed
    lang_map = {
        "Hindi": "hi-IN",
        "Marathi": "mr-IN"
    }
    target_lang = lang_map.get(request.language)

    if target_lang:
        print(f"Translating response to {target_lang}...")

        translated_highlights = []
        for h in result.get("highlights", []):
            translated_text = translate_with_sarvam(h.get("text", ""), target_lang)
            translated_highlights.append({
                "timestamp": h.get("timestamp", "00:00"),
                "text": translated_text
            })
        result["highlights"] = translated_highlights

        if result.get("key_points"):
            result["key_points"] = [
                translate_with_sarvam(point, target_lang)
                for point in result["key_points"]
            ]

        quick_insight = result.get("quick_insight") or "Analysis complete, no additional insights available."
        result["quick_insight"] = translate_with_sarvam(quick_insight, target_lang)

        if result.get("summary"):
            summary_text = result["summary"]
            paragraphs = re.findall(r'<p>(.*?)</p>', summary_text, flags=re.IGNORECASE | re.DOTALL)

            if paragraphs:
                translated_paragraphs = []
                for p in paragraphs:
                    trans_p = translate_with_sarvam(p, target_lang)
                    translated_paragraphs.append(f"<p>{trans_p}</p>")
                result["summary"] = "".join(translated_paragraphs)
            else:
                trans_text = translate_with_sarvam(summary_text, target_lang)
                result["summary"] = f"<p>{trans_text}</p>"

    # 4. Add Video Metadata
    metadata = get_video_metadata(video_id)
    if metadata:
        result["title"] = metadata.get("title")
        result["thumbnail_url"] = metadata.get("thumbnail_url")
    else:
        result["title"] = "Video Summary"
        result["thumbnail_url"] = ""

    # 5. Add processing metadata
    result["video_id"] = video_id
    result["is_multimodal"] = is_video
    result["model_used"] = model_used

    return result


# Mount static files to serve the frontend via FastAPI
# This acts as a catch-all for any request not matching API routes
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

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
import yt_dlp
from google import genai
from google.genai import types

# Add .local_bin to PATH for Render deployment (ffmpeg and deno binaries)
local_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.local_bin')
if os.path.exists(local_bin):
    os.environ["PATH"] = f"{local_bin}{os.pathsep}{os.environ.get('PATH', '')}"

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")  # Netscape-format cookies.txt content

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
    highlights: List[dict]
    key_points: List[str]
    summary: str
    quick_insight: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_id: Optional[str] = None
    is_multimodal: Optional[bool] = None
    model_used: Optional[str] = None
    gemini_file_name: Optional[str] = None

class ChatRequest(BaseModel):
    file_name: str
    question: str
    language: str
    history: List[dict] = []

# --- Request Model ---

class SummarizeRequest(BaseModel):
    url: str
    language: str

# --- Helper Functions ---

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


def write_cookies_file() -> Optional[str]:
    """
    Write YOUTUBE_COOKIES env var content to a temp file and return its path.
    Returns None if the env var is not set.
    This allows yt-dlp to authenticate as a real user on cloud IPs.
    """
    if not YOUTUBE_COOKIES:
        return None
    cookies_path = os.path.join("temp", "yt_cookies.txt")
    os.makedirs("temp", exist_ok=True)
    with open(cookies_path, "w") as f:
        f.write(YOUTUBE_COOKIES)
    return cookies_path


def get_video_duration(video_id: str, cookies_path: Optional[str] = None) -> Optional[int]:
    """Get video duration in seconds using yt-dlp metadata extraction."""
    try:
        # Use 'web' client when cookies are present — android/mweb don't support cookies.
        # Fall back to mweb+web when no cookies (for unauthenticated cloud IP bypass).
        player_client = ['web'] if cookies_path else ['mweb', 'web']
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': player_client
                }
            }
        }
        if cookies_path:
            ydl_opts['cookiefile'] = cookies_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info.get('duration')
    except Exception as e:
        print(f"Could not get video duration: {e}")
        return None


def process_video_multimodal(video_id: str, cookies_path: Optional[str] = None):
    """
    Download video/audio using yt-dlp and upload to Gemini.
    - For videos <= 30 minutes: downloads low-res MP4 (video + audio) for true multimodal analysis.
    - For videos > 30 minutes: falls back to audio-only (MP3) to save bandwidth.
    If YOUTUBE_COOKIES is set, passes cookies to yt-dlp to authenticate and bypass bot detection.
    Returns (uploaded_file, local_path, is_video).
    """
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)

    duration = get_video_duration(video_id, cookies_path)
    use_video = duration is not None and duration <= 1800  # 30 minutes

    # Use 'web' client when cookies are present — android/mweb don't support cookies.
    # Fall back to mweb+web when no cookies (for unauthenticated cloud IP bypass).
    player_client = ['web'] if cookies_path else ['mweb', 'web']
    common_opts = {
        'nocheckcertificate': True,
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': player_client
            }
        }
    }
    if cookies_path:
        common_opts['cookiefile'] = cookies_path

    try:
        if use_video:
            ydl_opts = {
                **common_opts,
                'format': 'worst[ext=mp4]/worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst',
                'outtmpl': os.path.join(temp_dir, f"{video_id}.%(ext)s"),
                'merge_output_format': 'mp4',
            }
            expected_ext = 'mp4'
        else:
            ydl_opts = {
                **common_opts,
                'format': 'ba[ext=m4a]/ba',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '64',
                }],
                'outtmpl': os.path.join(temp_dir, f"{video_id}.%(ext)s"),
            }
            expected_ext = 'mp3'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        media_path = os.path.join(temp_dir, f"{video_id}.{expected_ext}")

        # If expected file doesn't exist, try to find any downloaded file
        if not os.path.exists(media_path):
            for f in os.listdir(temp_dir):
                if f.startswith(video_id):
                    media_path = os.path.join(temp_dir, f)
                    break

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download media: {str(e)}")

    try:
        uploaded_file = client.files.upload(file=media_path)

        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise Exception("File processing failed on Gemini servers.")

        return uploaded_file, media_path, use_video
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(media_path):
            os.remove(media_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload media to Gemini: {str(e)}")


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

    # Write cookies file from env var (if set) to authenticate yt-dlp on cloud
    cookies_path = write_cookies_file()

    # 1. Process Video (multimodal: video or audio)
    uploaded_file, media_path, is_video = process_video_multimodal(video_id, cookies_path)

    media_type_label = "video" if is_video else "audio"

    # 2. Summarize with Gemini using structured output
    try:
        prompt = f"""You are a professional video analyst. {"Watch and listen to" if is_video else "Listen to"} this {media_type_label} carefully and provide a comprehensive analysis.

For each highlight, provide the approximate timestamp (MM:SS format) where that topic or point is discussed in the {media_type_label}. If you cannot determine the exact timestamp, estimate based on the flow of the content.

Provide exactly 4 key highlights with timestamps, exactly 5 concise key points (without timestamps), a detailed multi-paragraph summary using <p> HTML tags, and a powerful 1-sentence quick insight. Make the key points practical takeaways that complement, rather than repeat, the timestamped highlights.

{"Pay attention to both visual elements (slides, diagrams, code, demonstrations) and the spoken content." if is_video else "Focus on the spoken content and discussion points."}"""

        response, model_used = generate_with_gemini_fallback(
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type,
                        ),
                        types.Part.from_text(text=prompt),
                    ],
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
    finally:
        # Cleanup local file only. We keep the remote file on Gemini for the Chat feature.
        # Gemini files automatically expire and are deleted after 48 hours.
        if os.path.exists(media_path):
            os.remove(media_path)

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
    if 'uploaded_file' in locals():
        result["gemini_file_name"] = uploaded_file.name

    return result


@app.post("/chat")
async def chat_with_video(request: ChatRequest):
    """Answers questions based strictly on the uploaded video/audio file."""
    if not request.file_name:
        raise HTTPException(status_code=400, detail="Missing file_name")

    # 1. Translate question to English if needed (Gemini performs best with English instructions)
    # Wait, Gemini natively understands Hindi/Marathi very well, especially with multimodal context.
    # But for maximum accuracy in extracting facts, we can just send the raw question.
    # Actually, to follow the translation pattern, we'll translate the user's question to English first if they selected Hindi/Marathi, OR just let Gemini handle it.
    # Gemini handles Hindi/Marathi natively, but our strict system prompt might be in English.
    # Let's pass the question directly to Gemini, and then translate the response via Sarvam if needed.
    
    target_lang = None
    lang_map = {
        "Hindi": "hi-IN",
        "Marathi": "mr-IN"
    }
    if request.language in lang_map:
        target_lang = lang_map[request.language]

    try:
        # Retrieve the file from Gemini
        file_info = client.files.get(name=request.file_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found or expired. Please re-summarize the video.")

    # Convert history format for Gemini
    contents = []
    
    # Add history
    for msg in request.history:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg.get("text", ""))])
        )

    # Add the current prompt with the file context
    # Only add the file to the current (last) user message to avoid duplicate file attachments
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(file_uri=file_info.uri, mime_type=file_info.mime_type),
                types.Part.from_text(text=request.question)
            ]
        )
    )

    system_instruction = (
        "You are a helpful AI assistant answering questions about a provided video/audio file. "
        "Answer STRICTLY based on the provided media context. "
        "If the answer is not contained in the media, say 'I cannot find the answer to this in the video.' "
        "Do NOT provide generic outside knowledge. Be concise and direct."
    )

    try:
        # We use flash because it's fast and excellent at multimodal RAG
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
        )
        answer_text = response.text

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")

    # Translate answer if needed
    if target_lang:
        answer_text = translate_with_sarvam(answer_text, target_lang)

    return {"answer": answer_text}



# Mount static files to serve the frontend via FastAPI
# This acts as a catch-all for any request not matching API routes
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

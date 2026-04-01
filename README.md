# Child Safety Checker

A web app that analyses YouTube videos, uploaded videos, images, text files, and online terminology for child-appropriateness using AI. Get an instant breakdown of language, violence, advertising, agenda-pushing, misinformation, AI-generated content, and more — with an overall safety score and parental guidance.

---

## Features

### Video Checker
- Paste a YouTube URL **or upload a video file** (MP4, WebM, MOV, AVI, MKV) to analyse content
- **YouTube URL mode** — fetches the video transcript via captions
- **Upload Video mode** — transcribes audio with Whisper and extracts 8 evenly-spaced keyframes; Claude analyses both together for a full audio + visual assessment
- **Upload Text mode** — paste or upload a transcript/script (.txt, .md, .csv, .srt, .vtt) for analysis
- **Overall safety score** (0–100) with a visual score ring
- **Age rating** — All Ages, 6+, 9+, 13+, 16+, or 18+
- **8 content categories**, each scored and flagged by severity:
  - Language (profanity, offensive terms)
  - Violence
  - Adult themes (sex, drugs, alcohol)
  - Advertising & sales (sponsors, manipulative CTAs)
  - Agenda / bias (political, ideological, religious)
  - Misinformation (false claims, pseudoscience)
  - Fear & anxiety
  - **AI / Deepfake** (signs of AI-generated voice, synthetic script, deepfake impersonation)
- **Positives list** — educational value, good role models, etc.
- **Red flags** — the most important concerns for parents
- **Parental guidance** — specific, actionable advice

### Image Analyser
- Paste a direct image URL **or upload an image file** (JPEG, PNG, GIF, WebP, max 5 MB)
- Same 8-category scoring system, adapted for visual content:
  - Visible text and language
  - Violent or disturbing imagery
  - Adult / sexual visual content
  - Commercial branding and advertising
  - Political or ideological imagery
  - Misleading or manipulated visuals
  - Fear-inducing imagery
  - **AI / Deepfake** — lighting inconsistencies, anatomical errors, synthetic media indicators

### Term Lookup
- Type any word or phrase (e.g. *blue pill*, *grooming*, *MGTOW*) to understand its meaning in the context of child internet safety
- Results include:
  - **Risk level** (None → Critical), colour-coded
  - Plain-English definition
  - Associated online communities and platforms
  - Child safety context and implications
  - Warning signs to watch for in your child's behaviour
  - Related terms (clickable — runs a new lookup instantly)
  - Parental guidance

### General
- **Demo mode** — shows realistic example results when no API key is configured
- Real-time **streaming analysis** via Server-Sent Events
- Dark-themed, responsive single-page UI

---

## Requirements

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)
- YouTube videos must have captions/transcripts enabled
- Image URLs must be publicly accessible
- Uploaded video files are processed locally (no third-party transcription service required)

---

## Setup

**1. Clone or download the project**

```bash
cd ~/Desktop/Fact_Checker
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

> `opencv-python` and `openai-whisper` are required for video upload support and will be installed automatically.
> Whisper also requires `ffmpeg` on your system PATH. On macOS: `brew install ffmpeg`.

**4. Add your API key**

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Get a key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

**5. Run the app**

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Demo Mode

If no valid API key is configured, the app runs in **demo mode** — a yellow banner is shown at the top and any submission returns a realistic example result so you can explore the interface without needing an API key.

---

## Project Structure

```
Fact_Checker/
├── app.py              # Flask backend — content fetching, Claude API calls, SSE streaming
├── requirements.txt    # Python dependencies
├── .env                # API key (not committed to version control)
└── templates/
    └── index.html      # Single-page frontend (tabbed UI with URL and upload modes)
```

---

## How It Works

### Video Checker

**YouTube URL mode**
1. Paste a YouTube URL
2. The backend extracts the video ID and fetches the transcript via `youtube-transcript-api`
3. The transcript is sent to **Claude Opus 4.6** (with adaptive thinking) for analysis
4. Claude returns a structured JSON report covering all 8 categories
5. Results stream back in real time via SSE and render as a visual dashboard

**Upload Video mode**
1. Select a video file (MP4, WebM, MOV, AVI, MKV — up to 100 MB)
2. The backend saves the file to a temporary location, then runs two parallel extractions:
   - **Frames** — `opencv-python` extracts 8 evenly-spaced keyframes, base64-encoded as JPEGs
   - **Audio** — Whisper transcribes the audio track into text; the detected language is recorded
3. If transcription succeeds, Claude receives all 8 frames **and** the full transcript in a single message, producing a combined audio + visual assessment
4. If Whisper or `ffmpeg` is unavailable the analysis falls back to frames only — no error is shown
5. The temp file is deleted immediately after extraction regardless of outcome
6. Results stream back in real time and the `source_label` confirms whether a transcript was included (e.g. `uploaded video (8 frames + transcript)` vs `uploaded video (8 frames)`)

**Upload Text mode**
1. Select a plain text file (.txt, .md, .csv, .srt, .vtt — up to 80,000 characters)
2. The file contents are sent directly to Claude using the same transcript analysis pipeline
3. Useful for analysing scripts, subtitles, chat logs, or any text-based content

### Image Analyser

**Image URL mode**
1. Paste a direct image URL
2. The image is passed to Claude's **vision API** alongside the analysis prompt
3. Claude analyses the actual visual content and returns the same structured report
4. Results stream back and render identically to video results

**Upload Image mode**
1. Select an image file (JPEG, PNG, GIF, or WebP — up to 5 MB)
2. The image is base64-encoded in the browser and sent directly to Claude's vision API
3. Analysis and rendering are identical to URL mode

### Term Lookup
1. Type a word or phrase
2. Claude uses its knowledge of online communities, grooming tactics, and radicalisation pathways to explain the term in a child safety context
3. Results include risk level, context, warning signs, and parental guidance

---

## Testing

### 1. Verify dependencies

Run these in the activated venv before starting Flask:

```bash
python -c "import cv2; print('cv2 OK:', cv2.__version__)"
python -c "import whisper; print('whisper OK')"
ffmpeg -version | head -1
```

If `ffmpeg` is missing, Whisper will fail silently and video uploads will fall back to frames-only. Install it with `brew install ffmpeg` on macOS.

### 2. Demo mode (no API key required)

Remove or rename your `.env`, restart Flask, and open [http://localhost:5000](http://localhost:5000). The yellow demo banner should appear. Verify each route returns example output without hitting the API:

| Tab | Input | Expected `source_label` |
|-----|-------|------------------------|
| Video Checker → YouTube URL | Any YouTube URL | `YouTube transcript` |
| Video Checker → Upload Video | Any `.mp4` | `uploaded video` |
| Video Checker → Upload Text | Any `.txt` | `uploaded text` |
| Image Analyser → Image URL | Any image URL | `image` |
| Image Analyser → Upload Image | Any `.jpg` | `uploaded image` |
| Term Lookup | `blue pill` | _(term hero card)_ |

### 3. Live mode — confirm Whisper is running

Restore your `.env` and restart Flask. Upload a short video file that contains speech. Check two things:

- **Terminal** — on first run, Whisper prints model download progress. On subsequent runs it loads silently in ~1–2 seconds.
- **Result `source_label`** — `uploaded video (8 frames + transcript)` confirms Whisper succeeded. `uploaded video (8 frames)` means it fell back to frames only; check the Flask terminal for the exception.

### 4. Test graceful Whisper fallback

Add this to `.env` temporarily:

```
WHISPER_MODEL=does-not-exist
```

Upload a video — you should still receive a frames-only result, not a 500 error. Remove the line afterwards.

### 5. Edge cases

- Upload a video with no speech → frames-only result, no error
- Upload an unsupported format (e.g. a `.jpg` renamed to `.mp4`) → clear error from cv2, not a 500
- Upload a text file over 80,000 characters → truncated silently, analysis still completes
- Upload an image over 5 MB → `"Image is too large"` error before the API is called

---

## Notes

- YouTube videos without captions or with disabled transcripts cannot be analysed
- Long transcripts and text files are capped at ~80,000 characters to manage token usage
- Analysis quality depends on transcript accuracy (auto-generated captions can contain errors)
- Image URLs must point directly to an image file and be publicly accessible
- Uploaded images are limited to 5 MB (Claude API limit per image)
- Uploaded video files are limited to 100 MB; audio is transcribed automatically using Whisper and combined with frame analysis. If Whisper or ffmpeg is unavailable, analysis falls back to frames only
- Whisper downloads a ~140 MB model (`base`) on first use. Override with `WHISPER_MODEL=tiny` (faster, less accurate) or `WHISPER_MODEL=small`/`medium`/`large` in `.env`. Requires `ffmpeg` on the system PATH (`brew install ffmpeg` on macOS)
- The AI/Deepfake category analyses transcript, visual, and frame patterns — it cannot perform frame-by-frame forensic video analysis
- On macOS with pyenv, SSL certificate verification uses the system Keychain via `truststore` to handle corporate proxies

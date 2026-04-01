# Child Safety Checker

A web app that analyses YouTube videos, uploaded videos, images, text files, and online terminology for child-appropriateness using AI. Get an instant breakdown of language, violence, advertising, agenda-pushing, misinformation, AI-generated content, and more — with an overall safety score and parental guidance.

---

## Features

### Video Checker
- Paste a YouTube URL **or upload a video file** (MP4, WebM, MOV, AVI, MKV) to analyse content
- **YouTube URL mode** — fetches the video transcript via captions
- **Upload Video mode** — extracts 8 evenly-spaced keyframes and analyses them visually
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

> `opencv-python` is required for uploaded video frame extraction and will be installed automatically.

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
2. The backend saves the file temporarily and uses `opencv-python` to extract 8 evenly-spaced keyframes
3. The frames are base64-encoded and sent to Claude's vision API as image content blocks
4. Claude analyses the visual content across all 8 categories
5. The temp file is deleted immediately after frame extraction

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

## Notes

- YouTube videos without captions or with disabled transcripts cannot be analysed
- Long transcripts and text files are capped at ~80,000 characters to manage token usage
- Analysis quality depends on transcript accuracy (auto-generated captions can contain errors)
- Image URLs must point directly to an image file and be publicly accessible
- Uploaded images are limited to 5 MB (Claude API limit per image)
- Uploaded video files are limited to 100 MB; frame-based analysis covers visual content only — audio and dialogue are not analysed
- The AI/Deepfake category analyses transcript, visual, and frame patterns — it cannot perform frame-by-frame forensic video analysis
- On macOS with pyenv, SSL certificate verification uses the system Keychain via `truststore` to handle corporate proxies

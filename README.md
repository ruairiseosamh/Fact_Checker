# YouTube Child Safety Checker

A web app that analyses YouTube videos and generates a child-appropriateness report using AI. Paste a YouTube URL and get an instant breakdown of language, violence, advertising, agenda-pushing, misinformation, and more — with an overall safety score and parental guidance.

![Demo mode screenshot showing the score ring, category breakdown, and parental guidance](https://placehold.co/860x400?text=Screenshot)

---

## Features

- **Overall safety score** (0–100) with a visual score ring
- **Age rating** — All Ages, 6+, 9+, 13+, 16+, or 18+
- **7 content categories**, each scored and flagged by severity:
  - Language (profanity, offensive terms)
  - Violence
  - Adult themes (sex, drugs, alcohol)
  - Advertising & sales (sponsors, manipulative CTAs)
  - Agenda / bias (political, ideological, religious)
  - Misinformation (false claims, pseudoscience)
  - Fear & anxiety
- **Positives list** — educational value, good role models, etc.
- **Red flags** — the most important concerns for parents
- **Parental guidance** — specific, actionable advice
- **Demo mode** — shows a realistic example result when no API key is configured

---

## Requirements

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)
- YouTube videos must have captions/transcripts enabled

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

**4. Add your API key**

Edit `.env` and replace the placeholder with your real key:

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

If no valid API key is configured, the app runs in **demo mode** — a yellow banner is shown at the top and any URL you submit returns a realistic example result so you can explore the interface without needing an API key.

---

## Project Structure

```
Fact_Checker/
├── app.py              # Flask backend — transcript fetching, Claude API calls
├── requirements.txt    # Python dependencies
├── .env                # API key (not committed to version control)
└── templates/
    └── index.html      # Single-page frontend
```

---

## How It Works

1. You paste a YouTube URL into the app
2. The backend extracts the video ID and fetches the transcript via `youtube-transcript-api`
3. The transcript is sent to **Claude Opus 4.6** (with adaptive thinking enabled) for analysis
4. Claude returns a structured JSON report covering all content categories
5. The frontend renders the report as a visual dashboard

---

## Notes

- Videos without captions or with disabled transcripts cannot be analysed
- Long transcripts are capped at ~80,000 characters to manage token usage
- Analysis quality depends on transcript accuracy (auto-generated captions can contain errors)

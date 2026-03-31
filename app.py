import os
import re
import json
from typing import Optional, Tuple
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, Response, stream_with_context
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import anthropic

app = Flask(__name__)

DEMO_MODE = not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-")
client = None if DEMO_MODE else anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

DEMO_RESULT = {
    "overall_score": 62,
    "age_rating": "9+",
    "summary": (
        "This is an example demo result showing what a real analysis looks like. "
        "The video contains mild advertising and some one-sided messaging, but is "
        "otherwise suitable for older children with parental awareness."
    ),
    "categories": {
        "language": {
            "score": 9, "severity": "none",
            "details": "No profanity or offensive language detected throughout the video.",
            "examples": [],
        },
        "violence": {
            "score": 10, "severity": "none",
            "details": "No violent content present.",
            "examples": [],
        },
        "adult_themes": {
            "score": 9, "severity": "none",
            "details": "No adult themes, sexual content, drugs, or alcohol referenced.",
            "examples": [],
        },
        "advertising_sales": {
            "score": 5, "severity": "moderate",
            "details": (
                "The video contains a mid-roll sponsor segment promoting a subscription "
                "service, and several calls-to-action urging viewers to 'click the link below'."
            ),
            "examples": ["\"Head to our sponsor's site using the link below\"", "\"Subscribe now for 20% off\""],
        },
        "agenda_pushing": {
            "score": 6, "severity": "mild",
            "details": (
                "The presenter consistently frames one political viewpoint positively without "
                "acknowledging alternative perspectives. Not heavily partisan, but one-sided."
            ),
            "examples": [],
        },
        "misinformation": {
            "score": 8, "severity": "mild",
            "details": "Mostly accurate content. One statistic cited appears to be from an unverified source.",
            "examples": ["\"Studies show 90% of people agree...\" — source not cited"],
        },
        "fear_anxiety": {
            "score": 7, "severity": "mild",
            "details": "Some discussion of global problems that could be unsettling for younger or anxious children.",
            "examples": [],
        },
    },
    "positives": [
        "Clear and engaging presentation style",
        "Encourages curiosity and further research",
        "No inappropriate language or imagery",
    ],
    "red_flags": [
        "Sponsor segment promotes a paid subscription service directly to viewers",
        "One-sided framing on a contested topic without presenting counterarguments",
    ],
    "parental_guidance": (
        "This video is fine for children aged 9 and above with a parent present to discuss "
        "the sponsored content and help contextualise the one-sided viewpoints expressed. "
        "Use it as an opportunity to talk about media literacy and advertising."
    ),
    "video_id": "dQw4w9WgXcQ",
    "language": "English",
    "is_demo": True,
}


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_id: str) -> Tuple[str, str]:
    """Fetch transcript for a YouTube video. Returns (transcript_text, language)."""
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        # Try English first, then any manually created, then auto-generated
        try:
            transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            except Exception:
                # Fall back to first available transcript
                transcript = next(iter(transcript_list))

        fetched = transcript.fetch()
        text = " ".join(snippet.text for snippet in fetched)
        return text, transcript.language
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No transcript available for this video.")
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")


SYSTEM_PROMPT = """You are a child content safety expert. You analyse YouTube video transcripts and assess how appropriate they are for children.

Your analysis must be thorough, evidence-based, and actionable for parents. Always cite specific examples from the transcript when flagging concerns."""

ANALYSIS_PROMPT = """Analyse this YouTube video transcript and produce a detailed child-appropriateness report.

VIDEO ID: {video_id}
TRANSCRIPT:
{transcript}

Produce your report in the following JSON format (output ONLY valid JSON, no markdown, no preamble):

{{
  "overall_score": <integer 0-100, where 100 = perfectly safe for all ages>,
  "age_rating": "<one of: All Ages | 6+ | 9+ | 13+ | 16+ | 18+>",
  "summary": "<2-3 sentence plain-English summary of what the video is about and the overall verdict>",
  "categories": {{
    "language": {{
      "score": <0-10, where 10 = no issues>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<specific findings, quote examples if present>",
      "examples": [<list of specific problematic phrases or empty list>]
    }},
    "violence": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<specific findings>",
      "examples": []
    }},
    "adult_themes": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<sexual content, drugs, alcohol, or other adult themes>",
      "examples": []
    }},
    "advertising_sales": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<product placements, sponsored segments, calls to purchase, manipulative sales tactics>",
      "examples": []
    }},
    "agenda_pushing": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<political, ideological, religious, or social agendas being promoted, especially if one-sided>",
      "examples": []
    }},
    "misinformation": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<factual inaccuracies, pseudoscience, conspiracy theories, or misleading claims>",
      "examples": []
    }},
    "fear_anxiety": {{
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<content that may cause fear, nightmares, or anxiety in children>",
      "examples": []
    }}
  }},
  "positives": [<list of genuinely positive aspects for children, e.g. educational value, positive role models>],
  "red_flags": [<list of the most important concerns parents should know about>],
  "parental_guidance": "<specific, actionable advice for parents>"
}}"""


@app.route("/")
def index():
    return render_template("index.html", demo_mode=DEMO_MODE)


@app.route("/analyse", methods=["POST"])
def analyse():
    url = request.json.get("url", "").strip()
    if not url:
        return {"error": "Please provide a YouTube URL."}, 400

    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Could not parse a valid YouTube video ID from that URL."}, 400

    try:
        transcript, language = get_transcript(video_id)
    except ValueError as e:
        return {"error": str(e)}, 400

    # Demo mode — return canned result directly (no streaming needed)
    if DEMO_MODE:
        demo = dict(DEMO_RESULT)
        demo["video_id"] = video_id
        return {"result": demo, "language": language}

    # Truncate transcript to avoid excessive token usage (~100k chars ≈ ~25k tokens)
    if len(transcript) > 80000:
        transcript = transcript[:80000] + "\n\n[Transcript truncated for length]"

    def generate():
        yield "data: " + json.dumps({"status": "Analysing video content with AI..."}) + "\n\n"

        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": ANALYSIS_PROMPT.format(
                            video_id=video_id,
                            transcript=transcript,
                        ),
                    }
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            # Parse and return the JSON result
            # Strip any markdown code fences if present
            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["video_id"] = video_id
            result["language"] = language
            yield "data: " + json.dumps({"result": result}) + "\n\n"

        except json.JSONDecodeError:
            yield "data: " + json.dumps({"error": "Failed to parse AI response. Please try again."}) + "\n\n"
        except anthropic.APIError as e:
            yield "data: " + json.dumps({"error": f"AI API error: {str(e)}"}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"error": f"Unexpected error: {str(e)}"}) + "\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)

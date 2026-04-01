import os
import re
import json
import base64
import tempfile
import mimetypes
import truststore
import requests
from typing import Optional, Tuple
from dotenv import load_dotenv
load_dotenv()

# Use macOS Keychain for SSL verification (handles corporate proxies like Zscaler)
truststore.inject_into_ssl()
_http_session = requests.Session()
from flask import Flask, render_template, request, Response, stream_with_context
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import anthropic

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB max upload

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
        "ai_generated": {
            "score": 8, "severity": "mild",
            "details": "The transcript shows some signs of AI-generated scripting — unusually even pacing and formulaic sentence structure. The voice may be AI-synthesised. No deepfake impersonation of real individuals detected.",
            "examples": ["Repetitive sentence openings suggest templated AI script"],
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

DEMO_IMAGE_RESULT = {
    "overall_score": 71,
    "age_rating": "9+",
    "summary": (
        "This is an example demo result showing what a real image analysis looks like. "
        "The image contains mild commercial branding and some text, but is otherwise suitable "
        "for older children with parental awareness."
    ),
    "categories": {
        "language": {
            "score": 9, "severity": "none",
            "details": "No offensive or inappropriate text visible in the image.",
            "examples": [],
        },
        "violence": {
            "score": 10, "severity": "none",
            "details": "No violent imagery, weapons, or disturbing visual content present.",
            "examples": [],
        },
        "adult_themes": {
            "score": 10, "severity": "none",
            "details": "No sexual or adult visual content detected.",
            "examples": [],
        },
        "advertising_sales": {
            "score": 6, "severity": "mild",
            "details": "The image contains visible commercial branding and a promotional logo.",
            "examples": ["Brand logo prominently displayed"],
        },
        "agenda_pushing": {
            "score": 9, "severity": "none",
            "details": "No political or ideological imagery detected.",
            "examples": [],
        },
        "misinformation": {
            "score": 8, "severity": "mild",
            "details": "One visible statistic in the image appears to lack a cited source.",
            "examples": ["Uncited statistic overlaid on image"],
        },
        "fear_anxiety": {
            "score": 9, "severity": "none",
            "details": "Nothing in the image is likely to cause fear or anxiety in children.",
            "examples": [],
        },
        "ai_generated": {
            "score": 5, "severity": "moderate",
            "details": (
                "The image shows hallmarks of AI generation — unnaturally smooth skin texture, "
                "inconsistent background detail, and slight finger anomalies typical of diffusion models. "
                "No deepfake impersonation of a real person detected, but parents should be aware the image is synthetic."
            ),
            "examples": ["Background detail inconsistent with foreground lighting", "Finger geometry irregular"],
        },
    },
    "positives": [
        "No violent or adult content",
        "No offensive language visible",
    ],
    "red_flags": [
        "Image shows strong signs of AI generation",
        "Commercial branding visible — could be used for advertising to children",
    ],
    "parental_guidance": (
        "This image appears to be AI-generated. Discuss with your child how AI can create realistic-looking "
        "images that are entirely fabricated, and why verifying image sources matters."
    ),
    "video_id": "example-image.jpg",
    "language": "N/A",
    "source_label": "image",
    "is_demo": True,
}

DEMO_TERM_RESULT = {
    "term": "blue pill",
    "risk_level": "moderate",
    "short_definition": (
        "In mainstream use, a reference to The Matrix film. Online it has been appropriated "
        "by Manosphere communities to describe someone who accepts conventional social norms "
        "around gender and relationships — used dismissively to imply naivety."
    ),
    "communities": ["Manosphere", "Red Pill / MGTOW", "Incel forums", "YouTube / TikTok rabbit holes"],
    "child_safety_context": (
        "Used in online spaces to introduce young men to radicalised views on gender roles. "
        "Teenagers may encounter 'blue pill vs red pill' framing as an entry point to extremist content. "
        "The framing can make misogynistic ideology feel like 'waking up to the truth'."
    ),
    "warning_signs": [
        "Child dismisses or mocks people as 'bluepilled'",
        "Increased references to 'waking up' or 'seeing the truth'",
        "Contempt for relationships or women expressed online or at home",
        "Engagement with 'sigma male' or 'alpha/beta' content",
    ],
    "parent_guidance": (
        "If your child uses this term, have a calm, open conversation about where they encountered it. "
        "Explore the online communities they're engaging with without being confrontational. "
        "The term itself is not dangerous, but it can signal early exposure to Manosphere content "
        "that may escalate over time."
    ),
    "related_terms": ["red pill", "black pill", "MGTOW", "incel", "sigma male", "hypergamy"],
    "is_demo": True,
}


TERM_SYSTEM_PROMPT = """You are a child internet safety expert with deep knowledge of online communities, coded language, grooming tactics, radicalisation pathways, and youth online behaviour. You help parents and educators understand online slang and terminology that may relate to child safety risks."""

TERM_LOOKUP_PROMPT = """Explain the following term or phrase in the context of child internet safety.

TERM: {term}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "term": "the term as entered",
  "risk_level": "one of: none | low | moderate | high | critical",
  "short_definition": "2-3 sentence plain-English explanation of what the term means generally and online",
  "communities": ["list of online communities, movements, or platforms where this term is used"],
  "child_safety_context": "explanation of why this term is relevant to child safety — grooming, radicalisation, exploitation, or other risks",
  "warning_signs": ["observable behaviours or signs that a child may be exposed to this term's associated risks"],
  "parent_guidance": "practical, calm advice for a parent who has encountered this term",
  "related_terms": ["list of related or connected terms worth knowing"],
  "is_demo": false
}}

If the term has no meaningful child safety relevance, set risk_level to "none" and explain that clearly in the fields. Be accurate, non-alarmist, and practically helpful for parents."""


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    for pattern in [r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})"]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_content(video_id: str) -> Tuple[str, str, str]:
    """Fetch transcript for a YouTube video. Returns (text, language, source_label)."""
    try:
        api = YouTubeTranscriptApi(http_client=_http_session)
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            except Exception:
                transcript = next(iter(transcript_list))

        fetched = transcript.fetch()
        text = " ".join(snippet.text for snippet in fetched)
        return text, transcript.language, "YouTube transcript"
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No transcript available for this video.")
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")



SYSTEM_PROMPT = """You are a child content safety expert. You analyse online content and assess how appropriate it is for children.

Your analysis must be thorough, evidence-based, and actionable for parents. Always cite specific examples from the content when flagging concerns."""

ANALYSIS_PROMPT = """Analyse the following content and produce a detailed child-appropriateness report.

SOURCE: {source_label}
URL: {url}
CONTENT:
{transcript}

Produce your report in the following JSON format (output ONLY valid JSON, no markdown, no preamble):

{{
  "overall_score": <integer 0-100, where 100 = perfectly safe for all ages>,
  "age_rating": "<one of: All Ages | 6+ | 9+ | 13+ | 16+ | 18+>",
  "summary": "<2-3 sentence plain-English summary of what the content is about and the overall verdict>",
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
    }},
    "ai_generated": {{
      "score": <0-10, where 10 = clearly human-made, 0 = almost certainly AI-generated>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<assess whether the script, voice, or content shows signs of AI generation or deepfake manipulation — look for unnatural phrasing, synthetic speech patterns, impersonation of real people, AI avatar tells, or claims that seem fabricated. Note child safety implications such as fake personas used for grooming, AI-generated misinformation, or synthetic media bypassing content moderation>",
      "examples": [<specific phrases or patterns that suggest AI generation, or empty list>]
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
        return {"error": "Please provide a URL."}, 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Extract video ID and fetch transcript
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Could not parse a YouTube video ID from that URL."}, 400

    try:
        content, language, source_label = get_youtube_content(video_id)
        display_id = video_id
    except ValueError as e:
        return {"error": str(e)}, 400

    # Demo mode — return canned result directly (no streaming needed)
    if DEMO_MODE:
        demo = dict(DEMO_RESULT)
        demo["video_id"] = display_id
        demo["language"] = language
        demo["source_label"] = source_label
        return {"result": demo}

    # Truncate to avoid excessive token usage (~80k chars ≈ ~20k tokens)
    if len(content) > 80000:
        content = content[:80000] + "\n\n[Content truncated for length]"

    def generate():
        yield "data: " + json.dumps({"status": f"Analysing {source_label} with AI..."}) + "\n\n"

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
                            source_label=source_label,
                            url=url,
                            transcript=content,
                        ),
                    }
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["video_id"] = display_id
            result["language"] = language
            result["source_label"] = source_label
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


IMAGE_SYSTEM_PROMPT = """You are a child content safety expert. You analyse images and assess how appropriate they are for children.
Your analysis must be thorough, evidence-based, and actionable for parents. Cite specific visual elements when flagging concerns."""

IMAGE_ANALYSIS_PROMPT = """Analyse the image provided and produce a detailed child-appropriateness report.

Produce your report in the following JSON format (output ONLY valid JSON, no markdown, no preamble):

{
  "overall_score": <integer 0-100, where 100 = perfectly safe for all ages>,
  "age_rating": "<one of: All Ages | 6+ | 9+ | 13+ | 16+ | 18+>",
  "summary": "<2-3 sentence plain-English summary of what the image shows and the overall verdict>",
  "categories": {
    "language": {
      "score": <0-10, where 10 = no issues>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<any text, signs, captions, or writing visible in the image and whether it is appropriate>",
      "examples": [<list of specific problematic text visible, or empty list>]
    },
    "violence": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<violent imagery, weapons, blood, injury, or other disturbing visual content>",
      "examples": []
    },
    "adult_themes": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<sexual content, nudity, adult situations, drugs, alcohol, or other adult visual themes>",
      "examples": []
    },
    "advertising_sales": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<commercial branding, product promotion, call-to-action text, or manipulative advertising imagery>",
      "examples": []
    },
    "agenda_pushing": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<political, ideological, religious, or social imagery being promoted, especially if one-sided or extremist>",
      "examples": []
    },
    "misinformation": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<misleading visual claims, manipulated or out-of-context imagery, pseudoscientific graphics, or propaganda>",
      "examples": []
    },
    "fear_anxiety": {
      "score": <0-10>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<imagery that may cause fear, nightmares, or anxiety in children — horror, disturbing scenes, threatening figures>",
      "examples": []
    },
    "ai_generated": {
      "score": <0-10, where 10 = clearly authentic photograph, 0 = almost certainly AI-generated or deepfake>,
      "severity": "<none | mild | moderate | severe>",
      "details": "<assess signs of AI generation or deepfake manipulation — unnatural textures, lighting inconsistencies, anatomical errors, background artifacts, impersonation of real people, or synthetic media indicators. Note child safety implications such as fake personas, fabricated scenarios, or CSAM risk>",
      "examples": [<specific visual anomalies suggesting AI generation, or empty list>]
    }
  },
  "positives": [<list of genuinely positive aspects, e.g. educational imagery, positive representation>],
  "red_flags": [<list of the most important visual concerns parents should know about>],
  "parental_guidance": "<specific, actionable advice for parents>"
}"""


@app.route("/analyse-image", methods=["POST"])
def analyse_image():
    image_url = request.json.get("url", "").strip()
    if not image_url:
        return {"error": "Please provide an image URL."}, 400

    if not image_url.startswith(("http://", "https://")):
        image_url = "https://" + image_url

    if DEMO_MODE:
        return {"result": dict(DEMO_IMAGE_RESULT)}

    # Use the filename portion of the URL as the display ID
    from urllib.parse import urlparse
    path = urlparse(image_url).path
    display_id = path.split("/")[-1] or urlparse(image_url).netloc

    def generate():
        yield "data: " + json.dumps({"status": "Analysing image with AI..."}) + "\n\n"

        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=IMAGE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "url", "url": image_url}},
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    ],
                }],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["video_id"] = display_id
            result["language"] = "N/A"
            result["source_label"] = "image"
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/explain", methods=["POST"])
def explain():
    term = request.json.get("term", "").strip()
    if not term or len(term) > 200:
        return {"error": "Please provide a term or phrase (max 200 characters)."}, 400

    if DEMO_MODE:
        return {"result": dict(DEMO_TERM_RESULT)}

    def generate():
        yield "data: " + json.dumps({"status": "Researching term..."}) + "\n\n"

        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=16000,
                thinking={"type": "adaptive"},
                system=TERM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": TERM_LOOKUP_PROMPT.format(term=term)}],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["is_demo"] = False
            yield "data: " + json.dumps({"result": result}) + "\n\n"

        except json.JSONDecodeError:
            yield "data: " + json.dumps({"error": "Could not parse AI response. Please try again."}) + "\n\n"
        except anthropic.APIError as e:
            yield "data: " + json.dumps({"error": f"AI API error: {str(e)}"}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"error": f"Unexpected error: {str(e)}"}) + "\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_ALLOWED_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
_ALLOWED_TEXT_EXTS  = {".txt", ".md", ".csv", ".srt", ".vtt"}


@app.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    if not file or file.filename == "":
        return {"error": "Please select an image file."}, 400

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or ""
    if mime not in _ALLOWED_IMAGE_TYPES:
        return {"error": "Unsupported type. Please upload a JPEG, PNG, GIF, or WebP image."}, 400

    raw = file.read()
    if len(raw) > 5 * 1024 * 1024:
        return {"error": "Image is too large. Maximum size is 5 MB."}, 400

    image_data = base64.standard_b64encode(raw).decode("utf-8")
    filename = file.filename or "uploaded-image"

    if DEMO_MODE:
        demo = dict(DEMO_IMAGE_RESULT)
        demo["video_id"] = filename
        demo["source_label"] = "uploaded image"
        return {"result": demo}

    def generate():
        yield "data: " + json.dumps({"status": "Analysing uploaded image with AI..."}) + "\n\n"
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=IMAGE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": image_data}},
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    ],
                }],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["video_id"] = filename
            result["language"] = "N/A"
            result["source_label"] = "uploaded image"
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/upload-video", methods=["POST"])
def upload_video():
    file = request.files.get("file")
    if not file or file.filename == "":
        return {"error": "Please select a video file."}, 400

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_VIDEO_EXTS:
        return {"error": "Unsupported format. Please upload MP4, WebM, MOV, AVI, or MKV."}, 400

    filename = file.filename or "uploaded-video"

    # Save to disk before entering the generator (request object not accessible inside)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        os.close(tmp_fd)
        file.save(tmp_path)
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return {"error": f"Failed to save uploaded file: {str(e)}"}, 500

    if DEMO_MODE:
        os.unlink(tmp_path)
        demo = dict(DEMO_IMAGE_RESULT)
        demo["video_id"] = filename
        demo["source_label"] = "uploaded video"
        return {"result": demo}

    def generate():
        try:
            yield "data: " + json.dumps({"status": "Extracting video frames..."}) + "\n\n"

            try:
                import cv2
            except ImportError:
                yield "data: " + json.dumps({"error": "Video processing requires opencv-python. Run: pip install opencv-python"}) + "\n\n"
                return

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                yield "data: " + json.dumps({"error": "Could not open video file. Please check the format."}) + "\n\n"
                return

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total < 1:
                cap.release()
                yield "data: " + json.dumps({"error": "Could not read frames from this video."}) + "\n\n"
                return

            n_frames = min(8, total)
            frames_b64 = []
            for i in range(n_frames):
                idx = int(i * total / n_frames)
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frames_b64.append(base64.standard_b64encode(buf.tobytes()).decode("utf-8"))
            cap.release()

            if not frames_b64:
                yield "data: " + json.dumps({"error": "No frames could be extracted from this video."}) + "\n\n"
                return

            yield "data: " + json.dumps({"status": f"Analysing {len(frames_b64)} video frames with AI..."}) + "\n\n"

            content = []
            for fb64 in frames_b64:
                content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": fb64}})
            content.append({
                "type": "text",
                "text": (
                    f"These are {len(frames_b64)} keyframes sampled evenly from an uploaded video file "
                    f"({filename}). Analyse them together to assess the video's content for child safety.\n\n"
                    + IMAGE_ANALYSIS_PROMPT
                ),
            })

            full_response = ""
            try:
                with client.messages.stream(
                    model="claude-opus-4-6",
                    max_tokens=4096,
                    thinking={"type": "adaptive"},
                    system=IMAGE_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content}],
                ) as stream:
                    for text in stream.text_stream:
                        full_response += text

                clean = full_response.strip()
                if clean.startswith("```"):
                    clean = re.sub(r"^```[a-z]*\n?", "", clean)
                    clean = re.sub(r"\n?```$", "", clean)

                result = json.loads(clean)
                result["video_id"] = filename
                result["language"] = "N/A"
                result["source_label"] = f"uploaded video ({len(frames_b64)} frames)"
                yield "data: " + json.dumps({"result": result}) + "\n\n"

            except json.JSONDecodeError:
                yield "data: " + json.dumps({"error": "Failed to parse AI response. Please try again."}) + "\n\n"
            except anthropic.APIError as e:
                yield "data: " + json.dumps({"error": f"AI API error: {str(e)}"}) + "\n\n"
            except Exception as e:
                yield "data: " + json.dumps({"error": f"Unexpected error: {str(e)}"}) + "\n\n"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/upload-text", methods=["POST"])
def upload_text():
    file = request.files.get("file")
    if not file or file.filename == "":
        return {"error": "Please select a text file."}, 400

    ext = os.path.splitext(file.filename or "")[1].lower()
    mime = file.content_type or ""
    if ext not in _ALLOWED_TEXT_EXTS and not mime.startswith("text/"):
        return {"error": "Unsupported type. Please upload a .txt, .md, .csv, .srt, or .vtt file."}, 400

    filename = file.filename or "uploaded-text"

    try:
        content = file.read().decode("utf-8", errors="replace")
    except Exception:
        return {"error": "Could not read the file. Please ensure it is a plain text file."}, 400

    if not content.strip():
        return {"error": "The uploaded file appears to be empty."}, 400

    if len(content) > 80000:
        content = content[:80000] + "\n\n[Content truncated for length]"

    if DEMO_MODE:
        demo = dict(DEMO_RESULT)
        demo["video_id"] = filename
        demo["source_label"] = "uploaded text"
        return {"result": demo}

    def generate():
        yield "data: " + json.dumps({"status": "Analysing uploaded text with AI..."}) + "\n\n"
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": ANALYSIS_PROMPT.format(
                        source_label="uploaded text document",
                        url=filename,
                        transcript=content,
                    ),
                }],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            clean = full_response.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)

            result = json.loads(clean)
            result["video_id"] = filename
            result["language"] = "unknown"
            result["source_label"] = "uploaded text"
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)

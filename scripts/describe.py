#!/usr/bin/env python3
"""Writes a short description (.txt) for any picture that does not have one yet.

Uses Google's free Gemini service, only if a GEMINI_API_KEY is set. If anything
goes wrong (no key, free limit reached, service down) it quietly does nothing and
the page falls back to the general topic description. It never stops the build.
"""
import base64, io, json, os, re, sys, urllib.error, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PER_RUN = 10  # protects the free daily allowance
PROMPT = (
    "You are writing the caption for an original astrology artwork on a website. "
    "Topic: {topic}. Describe only what you can actually see in the picture, in plain, "
    "natural English, in 2 or 3 sentences. The FIRST sentence must be under 120 characters "
    "and work as alt text for a blind reader. If there is readable text in the artwork, "
    "mention it. Do not use hashtags, keyword lists, markdown, or quotation marks around "
    "the whole answer. Do not invent meanings the picture does not show."
)


def small_jpeg_b64(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def clean(text):
    text = re.sub(r"[*_#`>]+", "", text or "")
    text = " ".join(text.split()).strip(" \"'")
    return text[:600].rsplit(" ", 1)[0] if len(text) > 600 else text


def ask_gemini(path, topic, model, key):
    body = {"contents": [{"parts": [
        {"text": PROMPT.format(topic=topic)},
        {"inline_data": {"mime_type": "image/jpeg", "data": small_jpeg_b64(path)}}]}]}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return clean(data["candidates"][0]["content"]["parts"][0]["text"])


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("No GEMINI_API_KEY set: skipping AI descriptions (general descriptions will be used).")
        return
    site = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
    model = site.get("ai_model", "gemini-2.5-flash-lite")
    cats = json.loads((ROOT / "config" / "categories.json").read_text(encoding="utf-8"))
    done = 0
    for folder in sorted(p for p in (ROOT / "incoming").glob("*") if p.is_dir()):
        topic = cats.get(folder.name, {}).get("title", folder.name.replace("-", " ").title())
        for img in sorted(folder.iterdir()):
            if img.suffix.lower() not in EXTS:
                continue
            note = img.with_suffix(".txt")
            if note.exists() and note.read_text(encoding="utf-8").strip():
                continue
            if done >= MAX_PER_RUN:
                print("Reached the per-run limit; the rest will be done next time.")
                return
            try:
                text = ask_gemini(img, topic, model, key)
            except (urllib.error.URLError, KeyError, IndexError, ValueError, OSError) as e:
                print(f"Could not describe {img.name}: {e}. Using the general description.")
                continue
            if len(text) < 20:
                print(f"Description for {img.name} came back too short; skipping.")
                continue
            note.write_text(text + "\n", encoding="utf-8")
            print(f"Wrote description for {img.name}")
            done += 1


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the website build
        print(f"AI descriptions skipped: {e}")

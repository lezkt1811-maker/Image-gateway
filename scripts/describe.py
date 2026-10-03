#!/usr/bin/env python3
"""Writes the description and page title (a .txt next to each picture) for new pictures.

Uses Google's free Gemini service, only if a GEMINI_API_KEY is set.
 - Picture with no .txt          -> the AI looks at it and writes "Title:" + description.
 - Picture with a .txt but no
   "Title:" line and a name that
   says nothing (like 1000126.png) -> the AI writes a title from the description text.
If anything goes wrong (no key, free limit reached, service down) it quietly does nothing
and the page falls back to the general topic title/description. It never stops the build.
"""
import base64, io, json, os, re, sys, urllib.error, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import meaningful_words, slugify  # same "is this file name meaningful?" rule

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PER_RUN = 10  # protects the free daily allowance
API = "https://generativelanguage.googleapis.com/v1beta"
PICTURE_PROMPT = (
    "You are writing the page text for an original astrology artwork on a website. "
    "Topic: {topic}. Reply in exactly this format. Line 1: TITLE: followed by a good page "
    "title of 2 to 6 words in Title Case that names what the picture shows and includes the "
    "topic name if it reads naturally (no quotes, no trailing period, no clickbait, no keyword "
    "lists). Then a blank line, then the description. Describe only what you can actually see, "
    "in plain, natural English, in 2 or 3 sentences. The FIRST sentence of the description must "
    "be under 120 characters and work as alt text for a blind reader. If there is readable text "
    "in the artwork, mention it. Do not use hashtags, markdown, or quotation marks around the "
    "whole answer. Do not invent meanings the picture does not show."
)
TITLE_PROMPT = (
    "Write a good page title for an artwork page on an astrology website. Topic: {topic}. "
    "Base it only on this description of the artwork:\n\n{desc}\n\n"
    "The title must be 2 to 6 words in Title Case, say specifically what the artwork shows, "
    "and include the topic name if it reads naturally. No quotes, no trailing period, no "
    "clickbait, no keyword lists. Reply with the title only."
)


def small_jpeg_b64(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def clean_title(t):
    t = re.sub(r"[*_#`>]+", "", t or "").strip()
    t = t.splitlines()[0] if t else ""
    t = re.sub(r"(?i)^title:\s*", "", t).strip(" \"'.")
    return t if 3 <= len(t) <= 60 else ""


def clean(text):
    """Return 'Title: X\\n\\ndescription' (title only if the AI gave a sensible one)."""
    text = re.sub(r"[*_#`>]+", "", text or "").strip()
    title = ""
    m = re.match(r"(?i)\s*title:[ \t]*(.+?)[ \t]*(?:\n|$)", text)
    if m:
        title = clean_title(m.group(1))
        text = text[m.end():]
    body = " ".join(text.split()).strip(" \"'")
    if len(body) > 600:
        body = body[:600].rsplit(" ", 1)[0]
    return f"Title: {title}\n\n{body}" if title else body


def generate(parts, model, key):
    req = urllib.request.Request(
        f"{API}/models/{model}:generateContent",
        data=json.dumps({"contents": [{"parts": parts}]}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def find_models(key):
    """Ask Google which models exist right now; return up to 3 good fast ones."""
    req = urllib.request.Request(f"{API}/models?pageSize=200", headers={"x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as resp:
        models = json.load(resp).get("models", [])
    found = []
    for m in models:
        name = m.get("name", "").replace("models/", "")
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if not re.match(r"gemini-\d", name) or "flash" not in name:
            continue
        if re.search(r"image|tts|audio|live|embed|robot|computer|thinking|exp|learnlm|gemma", name):
            continue
        ver = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
        found.append((0 if "lite" in name else 1, 1 if "preview" in name else 0,
                      -(float(ver.group(1)) if ver else 0), name))
    return [f[-1] for f in sorted(found)][:3]


def run(parts, state, key):
    """Try the current model; if Google says it is gone/limited, find and try others."""
    last, i = None, 0
    while i < len(state["models"]):
        m = state["models"][i]
        i += 1
        try:
            text = generate(parts, m, key)
            state["models"] = [m] + [x for x in state["models"] if x != m]
            return text, None
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 403, 429) and not state["discovered"]:
                state["discovered"] = True
                try:
                    extra = [x for x in find_models(key) if x not in state["models"]]
                    print(f"Model {m} not usable ({e.code}); also trying: {', '.join(extra) or 'nothing found'}")
                    state["models"] += extra
                except (urllib.error.URLError, ValueError, OSError) as e2:
                    print(f"Could not list models: {e2}")
        except (urllib.error.URLError, KeyError, IndexError, ValueError, OSError) as e:
            return "", e
    return "", last


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("No GEMINI_API_KEY set: skipping AI descriptions (general descriptions will be used).")
        return
    site = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
    cats = json.loads((ROOT / "config" / "categories.json").read_text(encoding="utf-8"))
    state = {"models": [site.get("ai_model", "gemini-2.5-flash-lite")], "discovered": False}
    done = 0
    for folder in sorted(p for p in (ROOT / "incoming").glob("*") if p.is_dir()):
        cat = slugify(folder.name)
        topic = cats.get(folder.name, {}).get("title", folder.name.replace("-", " ").title())
        for img in sorted(folder.iterdir()):
            if img.suffix.lower() not in EXTS:
                continue
            note = img.with_suffix(".txt")
            existing = note.read_text(encoding="utf-8").strip() if note.exists() else ""
            if existing:
                # a description exists: only add a title if there is none and the name says nothing
                if re.match(r"(?i)\s*title:", existing) or meaningful_words(img.stem, cat):
                    continue
                if done >= MAX_PER_RUN:
                    return print("Reached the per-run limit; the rest will be done next time.")
                text, err = run([{"text": TITLE_PROMPT.format(topic=topic, desc=existing)}], state, key)
                title = clean_title(text)
                if not title:
                    print(f"Could not write a title for {img.name}: {err or 'no usable answer'}. Using the general title.")
                    continue
                note.write_text(f"Title: {title}\n\n{existing}\n", encoding="utf-8")
                print(f"Wrote title for {img.name}: {title}")
                done += 1
                continue
            if done >= MAX_PER_RUN:
                return print("Reached the per-run limit; the rest will be done next time.")
            parts = [{"text": PICTURE_PROMPT.format(topic=topic)},
                     {"inline_data": {"mime_type": "image/jpeg", "data": small_jpeg_b64(img)}}]
            text, err = run(parts, state, key)
            text = clean(text)
            if len(text.split("\n\n")[-1]) < 20:
                print(f"Could not describe {img.name}: {err or 'answer too short'}. Using the general description.")
                continue
            note.write_text(text + "\n", encoding="utf-8")
            print(f"Wrote description for {img.name}")
            done += 1


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the website build
        print(f"AI descriptions skipped: {e}")

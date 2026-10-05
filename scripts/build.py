#!/usr/bin/env python3
"""Turns every picture in incoming/<category>/ into a finished web page in site/.

Run by GitHub every time you upload. Needs only Python + Pillow (both free).
"""
import hashlib, html, json, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
JUNK_WORDS = {"img", "image", "images", "final", "copy", "ai", "untitled", "screenshot",
              "photo", "pic", "picture", "dsc", "edit", "edited", "new", "download", "file"}
MAX_SIDE, THUMB_SIDE = 1800, 600


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s), quote=True)


def render(template, values):
    text = (ROOT / "templates" / template).read_text(encoding="utf-8")
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", str(val))
    return text


def words_of(stem):
    return [w for w in re.split(r"[^a-zA-Z0-9]+", stem) if w]


def meaningful_words(stem, category):
    """Words from the filename that say something (not IMG_9283 / final2 / AI_00091)."""
    keep = []
    for w in words_of(stem):
        lw = w.lower()
        if re.search(r"\d", lw) and re.search(r"[a-z]", lw) and len(lw) >= 6:
            continue  # random codes like d08881f5b362 are not descriptive
        base = re.sub(r"\d+", "", lw)
        if not base or base in JUNK_WORDS or lw == category:
            continue
        keep.append(base if base != lw and len(base) > 2 else lw)
    return keep


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def cat_info(cats, cat):
    title = cat.replace("-", " ").title()
    info = dict(cats["_default"])
    info.update(cats.get(cat, {}))
    info["title"] = cats.get(cat, {}).get("title", title)
    for k in ("headline", "alt_default", "summary"):
        info[k] = info[k].replace("{title}", info["title"])
    info.setdefault("default_slug", slugify(info["title"]))
    return info


def first_sentence(text, limit=140):
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    s = m.group(1) if m else text.strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def last_modified(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)],
                             cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if out:
            return out
    except OSError:
        pass
    return date.today().isoformat()


def make_web_images(src, dest_dir, slug):
    dest_dir.mkdir(parents=True, exist_ok=True)
    img = ImageOps.exif_transpose(Image.open(src))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (15, 13, 26))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    full = img.copy()
    full.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    full.save(dest_dir / f"{slug}.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    thumb = img.copy()
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
    thumb.save(dest_dir / f"{slug}-thumb.jpg", "JPEG", quality=82, optimize=True)
    return full.size


def main():
    site, cats = load("config/site.json"), load("config/categories.json")
    site_url = site["site_url"].rstrip("/")
    base = urlparse(site_url).path.rstrip("/")
    main_url = site.get("main_site_url", "").strip()
    year = date.today().year

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy(ROOT / "templates" / "style.css", OUT / "style.css")

    # ---- 1. find and process pictures -------------------------------------
    pages, used = [], set()
    incoming = ROOT / "incoming"
    folders = sorted(p for p in incoming.iterdir() if p.is_dir()) if incoming.exists() else []
    for folder in folders:
        cat = slugify(folder.name)
        info = cat_info(cats, cat)
        for src in sorted(folder.iterdir()):
            if src.suffix.lower() not in EXTS:
                continue
            try:
                Image.open(src).verify()
            except Exception as e:
                print(f"SKIPPED {src.name}: not a readable picture ({e})", file=sys.stderr)
                continue
            # optional description file; its first line may be "Title: ..."
            note = src.with_suffix(".txt")
            raw = note.read_text(encoding="utf-8").strip() if note.exists() else ""
            text_title = None
            m = re.match(r"(?i)title:[ \t]*(.+?)[ \t]*(?:\n|$)", raw)
            if m:
                text_title = m.group(1).strip().strip("\"'")[:80] or None
                raw = raw[m.end():].strip()
            if raw:
                description = " ".join(raw.split())
                alt = first_sentence(description)
            else:
                alt = info["alt_default"]
                description = info["summary"]

            words = meaningful_words(src.stem, cat)
            if text_title:
                title = text_title
                tslug = slugify(text_title)
                slug = tslug if tslug.startswith(cat) else slugify(f"{cat}-{tslug}")
            elif words:
                slug = slugify(f"{cat}-{'-'.join(words)}")
                title = " ".join(w.capitalize() for w in [info["title"], *words])
            else:
                digest = hashlib.sha1(src.read_bytes()).hexdigest()[:6]
                slug = f"{info['default_slug']}-{digest}"
                title = info["headline"]
            if slug in used:
                slug += "-" + hashlib.sha1(src.read_bytes()).hexdigest()[:6]
            used.add(slug)

            w, h = make_web_images(src, OUT / "images" / cat, slug)
            pages.append(dict(cat=cat, info=info, slug=slug, title=title, alt=alt,
                              description=description, w=w, h=h,
                              lastmod=last_modified(src),
                              url=f"{base}/{cat}/{slug}/",
                              img=f"{base}/images/{cat}/{slug}.jpg",
                              thumb=f"{base}/images/{cat}/{slug}-thumb.jpg"))
            print(f"Processed {src.relative_to(ROOT)} -> {cat}/{slug}/")

    if not pages:
        print("No pictures found in incoming/. Nothing to publish yet.")

    name, desc = site["site_name"], site["site_description"]
    origin = f"{urlparse(site_url).scheme}://{urlparse(site_url).netloc}"
    main_link = (f'<p class="links"><a href="{esc(main_url)}">Visit {esc(name)}</a></p>'
                 if main_url else "")

    def page(rel_dir, **kw):
        d = OUT / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        base_vals = dict(site_name=esc(name), site_description=esc(desc), year=year,
                         base=base, nav=(f'<a href="{base}/">All artwork</a>'
                         f'<a id="uploadLink" class="nav-upload" href="{base}/upload/" hidden>+ Upload</a>'),
                         og_type="website", og_image="", jsonld="")
        base_vals.update(kw)
        (d / "index.html").write_text(render("base.html", base_vals), encoding="utf-8")

    def cards(items):
        return "\n".join(
            f'    <a class="card" href="{p["url"]}"><img src="{p["thumb"]}" alt="{esc(p["alt"])}" '
            f'loading="lazy"><span>{esc(p["title"])}</span></a>' for p in items)

    def ld(obj):
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"

    # ---- 2. one page per picture ------------------------------------------
    by_cat = {}
    for p in pages:
        by_cat.setdefault(p["cat"], []).append(p)
    for p in pages:
        info = p["info"]
        canonical = origin + p["url"]
        img_abs = origin + p["img"]
        others = [o for o in by_cat[p["cat"]] if o is not p][:6]
        related = (f'<section class="related"><h2>More {esc(info["title"])} artwork</h2>'
                   f'<div class="grid">\n{cards(others)}\n</div></section>' if others else "")
        about = "".join(f"<p>{esc(t)}</p>" for t in info.get("about", []))
        cat_url = f"{base}/{p['cat']}/"
        meta_desc = first_sentence(p["description"], 155)
        title_tag = f"{p['title']} | {name}"
        jsonld = ld({
            "@context": "https://schema.org", "@type": "ImageObject",
            "name": p["title"], "description": p["description"],
            "contentUrl": img_abs, "url": canonical,
            "thumbnailUrl": origin + p["thumb"],
            "width": p["w"], "height": p["h"],
            "representativeOfPage": True,
            "isPartOf": {"@type": "WebSite", "name": name, "url": site_url},
            "creator": {"@type": "Organization", "name": name},
        }) + ld({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": site_url + "/"},
                {"@type": "ListItem", "position": 2, "name": info["title"], "item": origin + cat_url},
                {"@type": "ListItem", "position": 3, "name": p["title"], "item": canonical}]})
        content = render("image-page.html", dict(
            base=base, category_url=cat_url, category_title=esc(info["title"]),
            title=esc(p["title"]), image_url=p["img"], alt=esc(p["alt"]),
            width=p["w"], height=p["h"], caption=esc(p["alt"]),
            description=esc(p["description"]), about_html=about,
            main_link=(f' &middot; <a href="{esc(main_url)}">Visit {esc(name)}</a>' if main_url else ""),
            related_html=related))
        og = (f'<meta property="og:image" content="{img_abs}">\n'
              f'<meta property="og:image:alt" content="{esc(p["alt"])}">\n'
              f'<meta name="twitter:image" content="{img_abs}">')
        page(f"{p['cat']}/{p['slug']}", page_title=esc(title_tag), meta_description=esc(meta_desc),
             canonical=canonical, content=content, og_type="article", og_image=og, jsonld=jsonld)

    # ---- 3. category pages and home page ----------------------------------
    for cat, items in by_cat.items():
        info = items[0]["info"]
        page(cat, page_title=esc(f"{info['headline']} | {name}"),
             meta_description=esc(info["summary"]), canonical=f"{site_url}/{cat}/",
             content=render("list-page.html", dict(
                 heading=esc(info["headline"]), intro=esc(info["summary"]),
                 cards=cards(items), main_link=main_link)))
    page("", page_title=esc(name), meta_description=esc(desc), canonical=site_url + "/",
         content=render("list-page.html", dict(
             heading=esc(name), intro=esc(desc), cards=cards(pages), main_link=main_link)))

    # ---- 3b. private upload page (not linked, not in the sitemap) ---------
    repo = site.get("github_repo", "")
    if repo:
        topics = sorted({c for c in cats if not c.startswith("_")} | {c for c in by_cat})
        up = OUT / "upload"
        up.mkdir(exist_ok=True)
        (up / "index.html").write_text(render("upload.html", dict(
            site_name=esc(name), base=base, repo=esc(repo), repo_name=esc(repo.split("/")[-1]),
            branch=esc(site.get("upload_branch", "main")),
            topics_json=json.dumps(topics))), encoding="utf-8")

    # ---- 4. sitemap and robots.txt ----------------------------------------
    urls = [f"  <url><loc>{site_url}/</loc><lastmod>{date.today().isoformat()}</lastmod></url>"]
    urls += [f"  <url><loc>{site_url}/{c}/</loc></url>" for c in by_cat]
    for p in pages:
        urls.append(f"  <url><loc>{origin}{p['url']}</loc><lastmod>{p['lastmod']}</lastmod>\n"
                    f"    <image:image><image:loc>{origin}{p['img']}</image:loc></image:image></url>")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"Done: {len(pages)} page(s) built in site/")


if __name__ == "__main__":
    main()

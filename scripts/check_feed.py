#!/usr/bin/env python3
"""Checks site/feed.xml against Pinterest's documented RSS auto-publish rules.

Pinterest: RSS 2.x/1.x only (no Atom); each <item> needs a title, description and an image
(<enclosure> or <media:content>); each item's <link> must be on the claimed website.
Run after build.py. Exits 1 with a plain list of problems if something is wrong.
"""
import json, re, sys, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
MEDIA = "{http://search.yahoo.com/mrss/}"


def check(feed_path=SITE / "feed.xml", cfg=None):
    problems = []
    cfg = cfg or json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
    site_url = cfg["site_url"].rstrip("/")
    host, base = urlparse(site_url).netloc, urlparse(site_url).path.rstrip("/")
    try:
        root = ET.parse(feed_path).getroot()
    except (ET.ParseError, OSError) as e:
        return [f"feed.xml is not valid XML: {e}"]
    if root.tag != "rss" or not root.get("version", "").startswith("2."):
        problems.append("the feed must be RSS 2.0 (<rss version=\"2.0\">); Pinterest does not accept Atom")
    ch = root.find("channel")
    if ch is None:
        return problems + ["no <channel> element"]
    for tag in ("title", "link", "description"):
        if not (ch.findtext(tag) or "").strip():
            problems.append(f"channel is missing <{tag}>")
    items = ch.findall("item")
    if not items:
        problems.append("the feed has no items yet (add a picture first)")
    seen = set()
    for i, it in enumerate(items, 1):
        t = (it.findtext("title") or "").strip()
        label = f"item {i} ({t[:40] or 'no title'})"
        if not t: problems.append(f"{label}: missing title")
        if len(t) > 100: problems.append(f"{label}: title is longer than 100 characters")
        d = (it.findtext("description") or "").strip()
        if not d: problems.append(f"{label}: missing description")
        if len(d) > 500: problems.append(f"{label}: description is longer than 500 characters")
        link = (it.findtext("link") or "").strip()
        if urlparse(link).netloc != host:
            problems.append(f"{label}: link {link!r} is not on the claimed website {host}")
        if link in seen: problems.append(f"{label}: duplicate link")
        seen.add(link)
        guid = (it.findtext("guid") or "").strip()
        if not guid: problems.append(f"{label}: missing guid")
        try:
            parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            problems.append(f"{label}: pubDate is missing or not an RFC 822 date")
        enc = it.find("enclosure"); mc = it.find(MEDIA + "content")
        img = (enc.get("url") if enc is not None else None) or (mc.get("url") if mc is not None else None)
        if not img:
            problems.append(f"{label}: no image (needs <enclosure> or <media:content>)"); continue
        if urlparse(img).scheme != "https":
            problems.append(f"{label}: image URL is not https")
        if enc is not None:
            if not re.fullmatch(r"\d+", enc.get("length", "")) or int(enc.get("length")) <= 0:
                problems.append(f"{label}: enclosure length must be the file size in bytes")
            if not (enc.get("type") or "").startswith("image/"):
                problems.append(f"{label}: enclosure type must be an image type")
        # the files really exist in the built site
        for what, url in (("page", link), ("image", img)):
            rel = urlparse(url).path
            rel = rel[len(base):] if base and rel.startswith(base) else rel
            target = SITE / rel.lstrip("/")
            if what == "page": target = target / "index.html" if target.suffix == "" else target
            if not target.exists():
                problems.append(f"{label}: the {what} file {rel} is not in the built site")
    return problems


if __name__ == "__main__":
    probs = check()
    if probs:
        print("PINTEREST FEED PROBLEMS:"); [print(" -", p) for p in probs]; sys.exit(1)
    n = len(ET.parse(SITE / "feed.xml").getroot().find("channel").findall("item"))
    print(f"Pinterest feed OK: RSS 2.0, {n} item(s), every item has title, description, image and a link on the claimed website.")

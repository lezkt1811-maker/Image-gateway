# AGENTS.md: how automated assistants work in this repo

Read this first. It lists the conventions, commands, and limits.

## What this repo is

A static gallery site built by GitHub Actions. Every picture in `incoming/<topic>/` becomes its own web page, and the build writes `feed.xml` (used by the autopost pipeline and Pinterest), `sitemap.xml`, and the topic pages. The built site is deployed to GitHub Pages at `art.starchart13.com`. Only `main` deploys. Other branches only run the build.

## Layout

| Path | What it is |
|---|---|
| `incoming/<topic>/` | Source pictures. A folder name is a topic, and it becomes a gallery pool name. |
| `incoming/<topic>/<name>.txt` | Optional description. The first line can be `Title: ...`. |
| `config/site.json` | Site name, URL and the AI model name. Owner-only edits. |
| `config/categories.json` | Headline, summary and alt text for each topic. |
| `scripts/build.py` | Builds `site/` from `incoming/`. Pillow only. |
| `scripts/describe.py` | Optional AI descriptions for new pictures (needs an owner-held key). |
| `scripts/check_feed.py` | Pinterest feed rules (warning only). |
| `scripts/images.py` | Checks picture ratios for Instagram and pads tall pictures to 4:5. |
| `templates/` | Page templates. |
| `site/` | Build output. Not committed. |

## Commands

```bash
pip install pillow
python scripts/images.py check incoming/<topic>     # ratio and width check
python scripts/images.py pad <src> <dst.jpg>         # add dark bars to reach 4:5
python scripts/build.py                              # build site/ locally
```

## Rules for agents

1. **Never push to `main` directly.** Work on the branch you were given. Push with `git push -u origin <branch>`. A push to `main` deploys the public site.
2. **Do not open a pull request unless the owner asks.**
3. **Run the image check and the build before every commit.** Both must pass.
4. **Do not edit `config/site.json`, secrets, or the workflow files** without an owner request.
5. **Keep file names clean.** Use lowercase letters, numbers and hyphens, with no spaces. Use a `.txt` file to give a picture a useful title.
6. **Pictures are public the moment `main` deploys.** Only add pictures the owner has approved for publishing, and remove personal data (names, birth dates, locations) before you add them.

## Picture specification (Instagram-ready)

- JPEG or PNG, at least 320 px wide.
- Aspect ratio between 0.8 (4:5) and 1.91:1. Run `images.py check` and pad anything flagged with `images.py pad`.
- Padding colour: `#0B0816`, the site's dark background.

## Where pictures are used

- `art.starchart13.com/feed.xml` lists every picture with its size. The autopost repo reads it to choose Instagram images. A pool is named after the topic folder, so `incoming/website-screens/` is the pool `website-screens`.
- Each picture gets its own page and is in the sitemap.

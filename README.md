# Image-to-Webpage Robot

Drop a picture in a folder. The robot gives it its own web page, tells Google where it lives, and publishes it.

## How to add a picture (works from your phone)

1. Open this repository on GitHub.
2. Open the folder `incoming`, then the topic folder (for example `ophiuchus`).
3. Tap **Add file → Upload files**, choose your picture, then tap **Commit changes**.
4. Open the **Actions** tab and wait for the green checkmark (about 1 minute).
5. Open your site. The picture has its own page.

A new topic is just a new folder inside `incoming` (for example `incoming/lilith/`). Create it by uploading a file and typing `lilith/picture.jpg` as the name.

### Optional: say what the picture shows
Upload a text file with the **same name** as the picture (`my-art.jpg` → `my-art.txt`) containing one or two sentences describing it. The robot uses your words for the page and for the picture's description. If you skip it, it uses a general description of the topic, so a real sentence is always better.

### Picture names
`IMG_9283.jpg` works, but a name like `serpent-bearer.jpg` gives the page a better title and address.

## Change the brand name or domain
Open `config/site.json`, tap the pencil, change `site_name`, `site_url` or `site_description`, and commit. Every page updates on the next build. Nothing else mentions the brand.

## One-time setup (do this once)
1. Merge the work into the `main` branch (only `main` goes live; other branches only test the build).
2. Go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
3. After the next green checkmark, your site is at the address shown in Settings → Pages.
4. Tell Google: in Google Search Console, submit `your-site-address/sitemap.xml`. This is optional but speeds discovery.

## What it costs
Nothing. GitHub Actions, GitHub Pages and the Python tools used here are free at this size. No paid AI is used.

## What it does not do
It does not guarantee Google rankings. It makes your picture and its page easy for search engines to find and understand. It also does not look at your picture, so the descriptions come from the topic, the file name and your optional text file.

## For the curious
`scripts/build.py` does the work; `config/categories.json` holds topic descriptions; `templates/` holds the page look. The finished website is built fresh in the cloud each time and is not stored in the repository.

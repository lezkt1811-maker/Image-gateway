# Image-to-Webpage Robot

Drop a picture in a folder. The robot gives it its own web page, tells Google where it lives, and publishes it.

## Easiest way: the upload page
Open `your-site-address/upload/` (for example https://lezkt1811-maker.github.io/Image-gateway/upload/), pick your picture, tap **Upload**. The first time, the page asks for a one-time GitHub token (the page walks you through making it). After that it's just: choose picture, tap Upload. Save the page to your phone's home screen. The page is private-ish: it is not linked anywhere and tells search engines to ignore it, and it does nothing without your token.

## The other way: through GitHub's folders (works from your phone)

1. Open this repository on GitHub.
2. Open the folder `incoming`, then the topic folder (for example `ophiuchus`).
3. Tap **Add file → Upload files**, choose your picture, then tap **Commit changes**.
4. Open the **Actions** tab and wait for the green checkmark (about 1 minute).
5. Open your site. The picture has its own page.

A new topic is just a new folder inside `incoming` (for example `incoming/lilith/`). Create it by uploading a file and typing `lilith/picture.jpg` as the name.

### Optional: say what the picture shows
Upload a text file with the **same name** as the picture (`my-art.jpg` → `my-art.txt`) containing one or two sentences describing it. The robot uses your words for the page and for the picture's description. If you skip it, it uses a general description of the topic, so a real sentence is always better.

### Automatic descriptions (free AI, optional)
If you added a free Google key (see below), the robot looks at each new picture that has no `.txt` file, writes a short description itself, and saves it as a `.txt` file next to the picture. You can open that file later and change the words, and your version is used from then on. If the free allowance runs out or the service is down, the page simply gets the general topic description instead. Nothing breaks.

**One-time setup for this:**
1. Go to https://aistudio.google.com/apikey and sign in with a Google account. Tap **Create API key** and copy it. Do NOT turn on billing.
2. In this repository open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name it `GEMINI_API_KEY`, paste the key as the value, and save. Never paste the key into a file or a chat.

Note: pictures that get a description are sent to Google for that step. On Google's free plan they may use what is sent to improve their products.

### Page titles
The robot's AI also suggests a short page title and saves it as the first line of the `.txt` file, like `Title: Ophiuchus Orbit Map`. To change a title, open the `.txt` file and edit that line. Put a `Title:` line at the top of your own description file to choose the title yourself. If there is no title line, the title comes from the picture's file name.

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

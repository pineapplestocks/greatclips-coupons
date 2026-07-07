# Great Clips Coupon Scraper & Website

Automatically scrapes Great Clips coupons from Facebook Ad Library and deploys a searchable website to GitHub Pages.

## 🚀 Features

- **Automated scraping** - Runs daily via GitHub Actions
- **Free hosting** - Deploys to GitHub Pages automatically
- **No server needed** - Everything runs in GitHub's cloud
- **Searchable website** - Filter by state, price, location
- **Universal coupons highlighted** - US-wide coupons shown first
- **Buffer auto-posting** - Queues current, unposted coupons for X/Twitter on a safe schedule

## 📁 Project Structure

```
├── .github/
│   └── workflows/
│       └── scrape.yml      # GitHub Actions workflow
├── data/
│   └── coupons.json        # Scraped coupon data
├── docs/
│   └── index.html          # Generated website (GitHub Pages)
├── scraper.py              # Main scraper script
├── generate_website.py     # Website generator
├── template.html           # Website template
├── twitter_poster.py       # Buffer/X coupon auto-poster
└── README.md
```

## 🛠️ Setup Instructions

### Step 1: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it something like `greatclips-coupons`
3. Make it **Public** (required for free GitHub Pages)
4. Click **Create repository**

### Step 2: Upload Files

Upload all these files to your new repository:
- `.github/workflows/scrape.yml`
- `scraper.py`
- `generate_website.py`
- `template.html`
- `README.md`

You can do this via:
- **GitHub web interface**: Click "Add file" > "Upload files"
- **Git command line**: Clone, add files, commit, push

### Step 3: Enable GitHub Pages

1. Go to your repository **Settings**
2. Click **Pages** in the left sidebar
3. Under "Build and deployment":
   - Source: **GitHub Actions**
4. Save

### Step 4: Run the Scraper

The scraper runs automatically every day at 6 AM UTC, but you can trigger it manually:

1. Go to **Actions** tab
2. Click **Scrape Great Clips Coupons**
3. Click **Run workflow** > **Run workflow**

### Step 5: View Your Website

After the workflow completes (~5-10 minutes), your site will be live at:

```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
```

## ⚙️ Configuration

### Change Scraping Schedule

Edit `.github/workflows/scrape.yml`:

```yaml
on:
  schedule:
    # Run at 6 AM UTC daily
    - cron: '0 6 * * *'
    
    # Examples:
    # '0 */6 * * *'   - Every 6 hours
    # '0 12 * * 1'    - Every Monday at noon
    # '0 0 * * *'     - Every day at midnight
```

### Increase Scroll Depth

Edit `scraper.py`:

```python
MAX_SCROLLS = 30  # Increase for more ads (slower)
```

### Buffer Auto-Poster for X/Twitter

This repo includes a Great Clips-specific poster inspired by the auto-poster
bot pattern, but it uses your real coupon data instead of asking AI to invent
tweet content. The GitHub Actions workflow queues posts through Buffer, which
can then publish them to your connected X/Twitter channel.

Add this repository secret in GitHub:

```text
Buffer
```

If your Buffer account has more than one X/Twitter channel, also add:

```text
BUFFER_CHANNEL_ID
```

Without `BUFFER_CHANNEL_ID`, the script automatically finds the first connected
Buffer channel whose service is X/Twitter.

The `.github/workflows/twitter.yml` workflow runs three times per day and queues
one valid, unposted coupon per run in Buffer. It records posted coupons in
`data/posted_tweets.json`, so the same coupon is not repeatedly shared.

To preview locally without posting:

```bash
python twitter_poster.py --dry-run --max-posts 3
```

To preview from GitHub, open **Actions** > **Post to Buffer** > **Run workflow**
and enable `dry_run`.

## 🔧 Troubleshooting

### "No offer URLs found"

Facebook may be blocking the scraper. The workflow will retry automatically the next day.

### Website not updating

1. Check the **Actions** tab for errors
2. Make sure GitHub Pages is enabled
3. Check that the `docs/` folder exists with `index.html`

### Rate limiting

GitHub Actions has limits:
- 2,000 minutes/month for free accounts
- Each run takes ~10-15 minutes

## 📊 How It Works

1. **GitHub Actions** starts the workflow on schedule
2. **Playwright** opens a headless Chrome browser
3. **Facebook Ad Library** is scraped for Great Clips ads
4. **Each coupon URL** is visited to extract details
5. **Data is saved** to `data/coupons.json`
6. **Website is generated** from the template
7. **GitHub Pages** deploys the website

## 🆓 Cost

**$0** - Everything uses free tiers:
- GitHub Actions: Free for public repos
- GitHub Pages: Free hosting
- No API keys needed

## 📝 License

MIT - Feel free to use and modify!

# Speaking Gig Agent

A weekly GitHub Actions workflow that searches for paid speaking opportunities relevant to Tyler Skinner / Women Making Waves, classifies the results with Anthropic Claude, and emails a table using a Gmail App Password. Under the hood, the app password authenticates against Gmail's SMTP server.

## What it does

Every Sunday at 5:00 PM Pacific time, the workflow:

1. Runs targeted web searches for paid speaking gigs, speaker applications, women leadership events, founder events, workshops, retreats, and honorarium-based opportunities.
2. Fetches candidate pages.
3. Uses Anthropic Claude to extract structured opportunity data.
4. Scores opportunities for relevance and pay likelihood.
5. Deduplicates results.
6. Sends Tyler an HTML email table with:
   - Opportunity
   - Opportunity description
   - Location
   - Date of opportunity
   - How much opportunity pays
   - Link
   - Fit score
   - Pay certainty

## Required GitHub Secrets

Add these in:

`GitHub Repo → Settings → Secrets and variables → Actions → New repository secret`

Required:

```text
ANTHROPIC_API_KEY
SERPER_API_KEY
GMAIL_USER
GMAIL_APP_PASSWORD
TO_EMAIL
```

Recommended:

```text
FROM_NAME
ANTHROPIC_MODEL
MIN_SCORE
MAX_RESULTS_PER_QUERY
SEARCH_PROVIDER
```

Suggested values:

```text
FROM_NAME=Speaking Gig Agent
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
MIN_SCORE=5
MAX_RESULTS_PER_QUERY=6
SEARCH_PROVIDER=serpapi
```

## Gmail App Password

This workflow is already configured for Google/Gmail App Passwords.

Important distinction: an App Password is an authentication method. Gmail still sends the message through its SMTP server unless you rebuild this with the Gmail API/OAuth flow. For this use case, App Password + Gmail SMTP is the simplest reliable setup.

Use a Gmail App Password, not your normal Gmail password.

The automation uses:

```text
SMTP server: smtp.gmail.com
Port: 587
Security: STARTTLS
Username: full Gmail address
Password: Gmail App Password, stored as the `GMAIL_APP_PASSWORD` GitHub secret
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`, including:

```text
GMAIL_USER=your-gmail-address@gmail.com
GMAIL_APP_PASSWORD=your-16-character-google-app-password
```

Then run:

```bash
python -m speaking_gig_agent.main
```

For local dry-run mode:

```bash
DRY_RUN=true python -m speaking_gig_agent.main
```

## Manual GitHub run

Go to:

`Actions → Weekly Speaking Gig Search → Run workflow`

Set `dry_run` to `true` to test without sending an email.

## Search tuning

Edit `src/speaking_gig_agent/config.py`.

The default queries intentionally bias toward paid speaking, honorariums, women entrepreneurs, leadership, California, Central Coast, Bay Area, LA, and virtual opportunities.

## Important limitations

Many speaking opportunities do **not** publicly list compensation. The agent separates:

- `confirmed_paid`
- `likely_paid`
- `unclear`
- `unpaid`

You should review early digests and tune the search queries and scoring thresholds.

## Recommended next improvements

1. Add a persistent `seen_urls.json` or lightweight database so the same old opportunities do not repeat every week.
2. Add a second search provider such as Tavily or Brave Search.
3. Add a Google Sheet export for tracking outreach status.
4. Add separate email sections:
   - Strong paid leads
   - Good strategic leads
   - Unclear, needs human review
5. Add outreach-draft generation for the top 3 opportunities.


## Why this still mentions SMTP

Google App Passwords do not replace SMTP by themselves. They replace your normal Gmail password when an app signs into Gmail's SMTP service.

So the sending stack is:

```text
Python email script → smtp.gmail.com:587 → Gmail username + App Password → Tyler receives email
```

A non-SMTP implementation would require the Gmail API with OAuth credentials, token storage, refresh-token handling, and broader setup overhead. That is overkill for a weekly private digest.

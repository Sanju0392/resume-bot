# Resume Automation Bot — Setup Guide

## What this does
Telegram message → AI classifies → updates resume in Google Drive → auto-updates Naukri profile

---

## Step 1: Create your Telegram bot (5 minutes)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Give it a name (e.g. "My Resume Bot") and a username (e.g. `myresume_bot`)
4. Copy the **bot token** → paste into `.env` as `TELEGRAM_BOT_TOKEN`

5. Get your **user ID** (so only you can use the bot):
   - Search for **@userinfobot** on Telegram
   - Send it any message — it replies with your ID
   - Paste that number into `.env` as `ALLOWED_USER_IDS`

---

## Step 2: Get an OpenAI API key

1. Go to https://platform.openai.com/api-keys
2. Create an account → API Keys → Create new secret key
3. Paste into `.env` as `OPENAI_API_KEY`

---

## Step 3: Set up Google Drive access (10 minutes)

### 3a. Create a Drive folder
1. Go to https://drive.google.com
2. Create a new folder called "Resumes"
3. Copy the folder ID from the URL (the long string after `/folders/`)
4. Paste into `.env` as `GOOGLE_DRIVE_FOLDER_ID`

### 3b. Create a Service Account
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable the **Google Drive API** (APIs & Services → Enable APIs)
4. Go to IAM & Admin → Service Accounts → Create Service Account
5. Name it "resume-bot", click Create
6. Skip role assignment, click Done
7. Click the service account → Keys → Add Key → JSON
8. Download the JSON file → save it as `config/service_account.json`

### 3c. Share your Drive folder with the service account
1. Open the JSON file you just downloaded
2. Find the `client_email` field (looks like `resume-bot@project.iam.gserviceaccount.com`)
3. Go to your "Resumes" Drive folder
4. Click Share → paste that email → give Editor access

### 3d. Upload your base resume
Upload your current resume as a plain text file named exactly: `resume_base.txt`
into your "Resumes" Drive folder.

---

---

## Step 4: Deploy to Render (free)

### 4a. Push code to GitHub
```bash
git init
git add .
git commit -m "Resume bot"
# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/resume-bot.git
git push -u origin main
```

### 4b. Create Render service
1. Go to https://render.com → sign up free → **New +** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Name:** resume-bot
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium`
   - **Start command:** `python bot.py`
   - **Plan:** Free

### 4c. Add environment variables
In Render dashboard → **Environment** tab → add each of these:

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `ALLOWED_USER_IDS` | your numeric Telegram ID |
| `OPENAI_API_KEY` | from platform.openai.com |
| `GOOGLE_DRIVE_FOLDER_ID` | the folder ID from Step 3a |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | paste the ENTIRE contents of the JSON file (all on one line) |
| `NAUKRI_EMAIL` | your Naukri login email |
| `NAUKRI_PASSWORD` | your Naukri password |

Click **Save Changes** → **Deploy**

### 4d. Copy your Render URL
After deploy, Render shows your URL: `https://resume-bot-xxxx.onrender.com`
This is set automatically as `RENDER_EXTERNAL_URL` — no action needed.

---

## Step 5: Test it

Send `/start` to your bot on Telegram.
If it replies, the webhook is live. Then send a real update:

```
Today I automated our weekly reporting — cut it from 3 hours to 15 minutes
using Python and Google Sheets API. All 5 stakeholders approved it.
```

Expected reply:
```
✅ Resume updated!

📌 Section: Experience
📝 Added: Automated weekly reporting pipeline reducing manual effort by 87%...

📊 ATS score: 91/100
📄 Pages: 1

☁️ Drive files:
  • resume_base.txt (untouched)
  • resume_2025-06-15.txt (new)

🔄 Naukri: ✓ Updated (headline + summary + skills)
```

---

## Drive file rule (always exactly 2 files)
```
Resumes/
  resume_base.txt           ← your base, NEVER overwritten
  resume_2025-06-15.txt     ← latest update, replaced each time you update
```

---

## Troubleshooting

**Bot doesn't respond at all**
→ Check Render logs (dashboard → Logs tab)
→ Make sure `TELEGRAM_BOT_TOKEN` is correct

**"Unauthorized" message**
→ `ALLOWED_USER_IDS` doesn't match your actual Telegram ID
→ Confirm your ID from @userinfobot

**Drive error: file not found**
→ Ensure `resume_base.txt` exists in your folder
→ Ensure the service account email has Editor access to the folder

**Naukri login fails**
→ If you use "Login with Google" on Naukri, set a direct password first:
   Naukri.com → Settings → Change Password

**Render keeps sleeping even with webhooks**
→ Webhooks wake Render instantly on each message — this is expected behaviour.
   The first message after a long idle may take ~5 seconds to respond while Render wakes up.
   All subsequent messages in that session are instant.

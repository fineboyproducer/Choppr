# CHOPPR — YouTube to Shorts Engine

Paste any YouTube link → AI finds the best moments → cuts them to vertical 9:16 → ready-to-post MP4s for TikTok, Instagram Reels, and YouTube Shorts.

---

## What It Does

1. **Downloads** the YouTube video using yt-dlp
2. **Reads the transcript** (if available via YouTube captions)
3. **AI analysis** — Claude identifies the 5–8 best moments, writes hooks + captions
4. **Cuts clips** to vertical 9:16 format with FFmpeg
5. **Serves them** in the browser — preview, download, copy captions

---

## First-Time Setup (Mac)

You only need to do this once.

### Step 1 — Download the project
Unzip this folder somewhere easy, like your Desktop or Documents.

### Step 2 — Open Terminal
Press `Cmd + Space`, type **Terminal**, hit Enter.

### Step 3 — Navigate to the folder
```bash
cd ~/Desktop/choppr
# (adjust path if you put it somewhere else)
```

### Step 4 — Make the script runnable
```bash
chmod +x start.sh
```

### Step 5 — Run it
```bash
./start.sh
```

The script will:
- Install Homebrew (Mac package manager) if needed
- Install Python, FFmpeg, and yt-dlp automatically
- Ask for your **Anthropic API key** (get one free at https://console.anthropic.com/settings/keys)
- Open CHOPPR in your browser at http://localhost:5055

---

## Every Time After That

Just open Terminal, go to the folder, and run:
```bash
./start.sh
```

Or double-click `start.sh` in Finder (right-click → Open With → Terminal).

---

## Getting Your Anthropic API Key

1. Go to https://console.anthropic.com/settings/keys
2. Sign up / log in
3. Click **Create Key**
4. Copy it and paste it when `start.sh` asks

The key is saved to a `.env` file in the folder so you only need to do this once.

---

## Clips Output

All cut clips are saved to the `clips_output/` folder inside the project. You can also download them directly from the browser.

---

## Tips

- **Longer videos = longer download time.** A 30-minute video might take 5–10 minutes to download and cut.
- **No transcript?** Claude will still find clips based on the video description and title.
- **yt-dlp stops working?** Run `brew upgrade yt-dlp` — YouTube frequently updates their site and yt-dlp needs to keep up.
- **Want higher quality?** In `app.py`, change `-crf 23` to `-crf 18` (slower but better quality).

---

## Project Files

```
choppr/
├── app.py              # Flask backend (AI + video processing)
├── requirements.txt    # Python packages
├── start.sh            # One-click setup & launcher
├── templates/
│   └── index.html      # Web UI
└── clips_output/       # Your cut clips land here
```

---

Built for independent creators 🎵

import os
import json
import subprocess
import threading
import uuid
import re
import glob
import shutil
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CLIPS_DIR = os.path.join(os.path.dirname(__file__), "clips_output")
os.makedirs(CLIPS_DIR, exist_ok=True)

jobs = {}




# ── VIDEO INFO ───────────────────────────────────────────────────────────────

def get_video_info(url):
    result = subprocess.run(
        [
    "yt-dlp",
    "--user-agent", "Mozilla/5.0",
    "--no-check-certificate",
    "--dump-json",
    "--no-playlist",
    url
],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise Exception(f"yt-dlp error: {result.stderr[:500]}")
    info = json.loads(result.stdout)
    return {
        "title": info.get("title", "Unknown"),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", "Unknown"),
        "thumbnail": info.get("thumbnail", ""),
        "description": info.get("description", "")[:2000],
    }


def download_video(url, job_id):
    output_path = os.path.join(CLIPS_DIR, f"{job_id}_source.%(ext)s")
    result = subprocess.run(
        [
    "yt-dlp",
    "--user-agent", "Mozilla/5.0",
    "--no-check-certificate",
    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "-o", output_path,
    "--no-playlist",
    url,
],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        raise Exception(f"Download failed: {result.stderr[:500]}")
    for f in os.listdir(CLIPS_DIR):
        if f.startswith(f"{job_id}_source"):
            return os.path.join(CLIPS_DIR, f)
    raise Exception("Downloaded file not found")


def get_transcript(url):
    """Pull YouTube auto-captions for AI analysis."""
    subprocess.run(
        [
    "yt-dlp",
    "--user-agent", "Mozilla/5.0",
    "--no-check-certificate",
    "--write-auto-sub", "--sub-lang", "en",
    "--sub-format", "vtt", "--skip-download",
    "--output", "/tmp/yt_transcript_%(id)s", url,
],
        capture_output=True, text=True, timeout=60
    )
    files = glob.glob("/tmp/yt_transcript_*.vtt")
    if files:
        with open(files[0], "r") as f:
            raw = f.read()
        lines = raw.split("\n")
        out = []
        for line in lines:
            if "-->" not in line and line.strip() \
               and not line.startswith("WEBVTT") \
               and not line.startswith("NOTE") \
               and not re.match(r'^\d+$', line.strip()):
                clean = re.sub(r'<[^>]+>', '', line).strip()
                if clean:
                    out.append(clean)
        for f in files:
            try: os.remove(f)
            except: pass
        return " ".join(out)[:8000]
    return None


# ── AI CLIP PLANNER ──────────────────────────────────────────────────────────

def ai_identify_clips(video_info, transcript, duration, platforms):
    clip_lengths = [30, 35, 40, 45, 30, 40]
    clips = []
    start = 15

    for i, clip_len in enumerate(clip_lengths):
        if start >= duration - 10:
            break

        end = min(start + clip_len, duration - 5)
        if end <= start:
            break

        title_base = re.sub(r'[^a-zA-Z0-9_]+', '_', video_info.get("title", "clip").lower()).strip('_')
        clip_title = f"{title_base[:18]}_{i+1}"

        clips.append({
            "start_time": int(start),
            "end_time": int(end),
            "hook": f"Clip {i+1}",
            "caption": f"{video_info.get('title', 'Video clip')} 🔥 #{' #'.join([p.replace(' ', '') for p in platforms])}",
            "why": "Auto-generated clip based on video duration.",
            "platforms": platforms,
            "clip_title": clip_title
        })

        start = end + 10

    return clips


# ── SUBTITLE PIPELINE ────────────────────────────────────────────────────────

def check_whisper_available():
    return subprocess.run(["which", "whisper"], capture_output=True).returncode == 0


def extract_audio(video_path, audio_path):
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", audio_path],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise Exception(f"Audio extract failed: {result.stderr[-300:]}")


def transcribe_with_whisper(audio_path, output_dir):
    result = subprocess.run(
        [
            "whisper", audio_path,
            "--model", "base",
            "--output_format", "srt",
            "--output_dir", output_dir,
            "--language", "en",
            "--word_timestamps", "True",
        ],
        capture_output=True, text=True, timeout=300
    )
    base = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(output_dir, base + ".srt")
    if os.path.exists(srt_path):
        return srt_path
    candidates = glob.glob(os.path.join(output_dir, base + "*.srt"))
    if candidates:
        return candidates[0]
    raise Exception(f"Whisper SRT not found. stderr: {result.stderr[-300:]}")


def burn_subtitles(raw_clip_path, srt_path, final_path):
    """Burn bold white captions — classic viral shorts style."""
    safe_srt = srt_path.replace("\\", "/").replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{safe_srt}'"
        f":force_style='"
        f"FontName=Arial,"
        f"FontSize=22,"
        f"Bold=1,"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H80000000,"
        f"Outline=3,"
        f"Shadow=1,"
        f"Alignment=2,"
        f"MarginV=80"
        f"'"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", raw_clip_path,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            final_path,
        ],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise Exception(f"Subtitle burn failed: {result.stderr[-500:]}")


# ── CUT (no subtitles) ───────────────────────────────────────────────────────

def cut_clip_raw(source_path, start, end, output_path):
    """Cut and scale to 9:16 vertical."""
    duration = end - start
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", source_path,
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                   "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise Exception(f"FFmpeg cut failed: {result.stderr[-500:]}")


# ── MAIN JOB ─────────────────────────────────────────────────────────────────

def run_job(job_id, url, platforms, burn_subs):
    tmp_files = []
    try:
        whisper_ok = burn_subs and check_whisper_available()
        jobs[job_id]["whisper_available"] = whisper_ok

        # 1. Video info
        jobs[job_id].update(status="fetching_info", message="Fetching video info...")
        video_info = get_video_info(url)
        jobs[job_id]["video_info"] = video_info
        duration = video_info["duration"]

        # 2. Transcript for AI
        jobs[job_id].update(status="transcript", message="Reading transcript...")
        transcript = get_transcript(url)

        # 3. AI clip selection
        jobs[job_id].update(status="ai_analysis", message="AI is finding the best moments...")
        clips = ai_identify_clips(video_info, transcript, duration, platforms)
        jobs[job_id]["clips_plan"] = clips
        jobs[job_id]["total_clips"] = len(clips)

        # 4. Download
        jobs[job_id].update(
            status="downloading",
            message=f"Downloading video ({duration//60}m {duration%60}s)..."
        )
        source_path = download_video(url, job_id)
        tmp_files.append(source_path)

        # 5. Cut + (optionally) subtitle each clip
        jobs[job_id].update(status="cutting", clips_done=0)
        output_clips = []

        for i, clip in enumerate(clips):
            label = clip["clip_title"]
            n = i + 1
            step = f"Clip {n}/{len(clips)}: {label}"

            # 5a. Raw vertical cut
            jobs[job_id]["message"] = f"✂️  {step} — cutting..."
            raw_path = os.path.join(CLIPS_DIR, f"{job_id}_clip{n}_{label}_raw.mp4")
            cut_clip_raw(source_path, clip["start_time"], clip["end_time"], raw_path)
            tmp_files.append(raw_path)

            final_filename = f"{job_id}_clip{n}_{label}.mp4"
            final_path = os.path.join(CLIPS_DIR, final_filename)

            if whisper_ok:
                try:
                    # 5b. Extract audio
                    jobs[job_id]["message"] = f"🎙  {step} — transcribing with Whisper..."
                    audio_path = os.path.join(CLIPS_DIR, f"{job_id}_clip{n}.wav")
                    tmp_files.append(audio_path)
                    extract_audio(raw_path, audio_path)

                    # 5c. Whisper → SRT
                    srt_path = transcribe_with_whisper(audio_path, CLIPS_DIR)
                    tmp_files.append(srt_path)

                    # 5d. Burn subtitles
                    jobs[job_id]["message"] = f"🔤  {step} — burning subtitles..."
                    burn_subtitles(raw_path, srt_path, final_path)
                    clip["has_subtitles"] = True

                except Exception as sub_err:
                    print(f"[WARN] Subtitle failed for clip {n}: {sub_err}")
                    shutil.copy2(raw_path, final_path)
                    clip["has_subtitles"] = False
                    clip["subtitle_error"] = str(sub_err)
            else:
                shutil.copy2(raw_path, final_path)
                clip["has_subtitles"] = False

            clip["filename"] = final_filename
            clip["clip_number"] = n
            output_clips.append(clip)
            jobs[job_id]["clips_done"] = n

        sub_note = " with subtitles 🔤" if whisper_ok else ""
        jobs[job_id].update(
            status="done",
            message=f"Done! {len(output_clips)} clips ready{sub_note}",
            output_clips=output_clips,
        )

    except Exception as e:
        jobs[job_id].update(status="error", message=str(e))

    finally:
        for f in tmp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_job():
    data = request.json
    url = data.get("url", "").strip()
    platforms = data.get("platforms", ["TikTok", "Instagram Reels", "YouTube Shorts"])
    burn_subs = data.get("subtitles", True)

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "starting",
        "message": "Starting...",
        "clips_done": 0,
        "total_clips": 0,
        "output_clips": [],
        "clips_plan": [],
        "video_info": {},
        "whisper_available": False,
    }

    thread = threading.Thread(target=run_job, args=(job_id, url, platforms, burn_subs), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def job_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])


@app.route("/api/whisper_check")
def whisper_check():
    return jsonify({"available": check_whisper_available()})


@app.route("/clips/<filename>")
def serve_clip(filename):
    return send_from_directory(CLIPS_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5055)

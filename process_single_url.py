import os
import re
import time
import subprocess
import yt_dlp
import soundfile as sf
import math
import torch
from faster_whisper import WhisperModel

def sanitize_title(raw_title):
    title = re.sub(r'[\\/:*?"<>|]', '', raw_title)
    title = re.sub(r'[\s,，。、~!@#$%^&*\-+=()\[\]{}（）【】·|“”：；‘’\'"<>.?/\\\\]+', '_', title)
    title = title[:50]
    return title

def process_single_url(url, task_id, output_dir, model_name="small", compute_type="float32", cookies="cookies.txt"):
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'cookies': cookies if os.path.exists(cookies) else None,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        aid = info["id"]
        raw_title = info.get("title", aid)
        title = sanitize_title(raw_title)
        ext = info["ext"]
        origin_file = os.path.join(output_dir, f"{aid}.{ext}")
        base = f"{aid}_{title}_{task_id}"
        wav_file = os.path.join(output_dir, base + ".wav")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", origin_file,
            "-ar", "16000", "-ac", "1", "-vn", wav_file
        ]
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(origin_file)
    audio_len = sf.info(wav_file).duration
    segs = []
    part_num = int(math.ceil(audio_len / 300))
    for i in range(part_num):
        start = i * 300
        out_file = os.path.join(output_dir, f"{base}_p{i+1}.wav")
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-t", "300",
            "-i", wav_file, "-ar", "16000", "-ac", "1", "-vn", out_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segs.append(out_file)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    all_texts = []
    for seg in segs:
        segments, info = model.transcribe(seg, language="zh", beam_size=3, vad_filter=True)
        text = "".join([s.text for s in segments])
        all_texts.append(text)
    txt_file = os.path.join(output_dir, base + ".txt")
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(all_texts))
    for seg in segs:
        try: os.remove(seg)
        except: pass
    return txt_file, wav_file

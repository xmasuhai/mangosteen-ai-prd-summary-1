# -*- coding: utf-8 -*-
import os, subprocess, sys

BASE = r"F:\ai-video-summary\Work_Schedule"
OUT = os.path.join(BASE, "notes_03")
os.makedirs(OUT, exist_ok=True)
VIDEO = r"F:\jirengu_course_backup\山竹记账宇宙课程\山竹记账全栈版Vue 3 + Rails 7+TSX\30.【山竹记账后端】文档撰写与排期\3. 使用用例图描述功能.mp4"
WAV = os.path.join(OUT, "audio_16k.wav")

import imageio_ffmpeg
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

if not os.path.exists(WAV):
    subprocess.run([ffmpeg, "-y", "-i", VIDEO, "-vn", "-ac", "1", "-ar", "16000", WAV], check=True)
    print("audio extracted", flush=True)

from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8",
                     download_root=os.path.join(BASE, ".models"))
print("model loaded", flush=True)
segments, info = model.transcribe(WAV, language="zh", beam_size=5, vad_filter=False)
print("duration:", info.duration, flush=True)

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

lines_md = [f"# 转写稿：3. 使用用例图描述功能.mp4", "", f"- 时长：{ts(info.duration)}", "- 引擎：faster-whisper / cpu", "- 语言：zh", ""]
lines_txt = []
for seg in segments:
    text = seg.text.strip()
    lines_md.append(f"**[{ts(seg.start)}]** {text}")
    lines_md.append("")
    lines_txt.append(f"[{int(seg.start)}s] {text}")
    print(f"[{int(seg.start)}s] {text}", flush=True)

with open(os.path.join(OUT, "transcript.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines_md))
with open(os.path.join(OUT, "transcript.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines_txt))
print("DONE", flush=True)

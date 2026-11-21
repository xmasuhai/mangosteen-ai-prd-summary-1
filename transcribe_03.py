# -*- coding: utf-8 -*-
"""用 faster-whisper 把课程视频转写成逐字稿（md + txt）。

示例：
    python transcribe_03.py --video "F:\...\3. 使用用例图描述功能.mp4" --out notes_03
    python transcribe_03.py --video in.mp4 --out notes_05 --model medium --dry-run
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def pos_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"需要正整数，收到 {value!r}")
    if n <= 0:
        raise argparse.ArgumentTypeError(f"需要正整数，收到 {value!r}")
    return n


def build_parser():
    p = argparse.ArgumentParser(
        description="课程视频转写：extract 16k mono wav -> faster-whisper -> transcript.md/.txt",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--video", required=True, help="输入视频（或音频）文件路径")
    p.add_argument("--out", default="notes_03", help="输出目录，不存在会自动创建")
    p.add_argument("--model", default="small",
                   help="whisper 模型名或本地模型路径，如 tiny/base/small/medium/large-v3")
    p.add_argument("--models-dir", default=str(PROJECT_ROOT / ".models"),
                   help="模型下载/缓存目录")
    p.add_argument("--language", default="zh", help="识别语言，传 auto 可自动检测")
    p.add_argument("--beam-size", type=pos_int, default=5, help="beam search 宽度")
    p.add_argument("--device", default="cpu", help="cpu 或 cuda")
    p.add_argument("--compute-type", default="int8",
                   help="int8 / int8_float32 / float16 / float32")
    p.add_argument("--vad-filter", action="store_true",
                   help="开启 VAD 静音过滤（原脚本为关闭）")
    p.add_argument("--title", default=None,
                   help="写入 transcript.md 的标题，默认取视频文件名")
    p.add_argument("--voice", default="audio_16k.wav",
                   help="中间音频文件名，保存在输出目录内")
    p.add_argument("--force", action="store_true", help="即使中间音频已存在也重新抽取")
    p.add_argument("--dry-run", action="store_true", help="只打印解析后的参数，不执行转写")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    video = Path(args.video).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    models_dir = Path(args.models_dir).expanduser().resolve()
    wav = out_dir / args.voice
    title = args.title or video.name

    if not video.is_file():
        print(f"[error] 视频不存在：{video}", file=sys.stderr)
        return 2
    if args.model != "small" and not models_dir.exists() and not args.dry_run:
        print(f"[warn] 模型目录不存在，将自动创建：{models_dir}", file=sys.stderr)

    print(f"video      : {video}")
    print(f"out_dir    : {out_dir}")
    print(f"wav        : {wav}")
    print(f"model      : {args.model} (device={args.device}, compute_type={args.compute_type})")
    print(f"models_dir : {models_dir}")
    print(f"language   : {args.language}  beam_size={args.beam_size}  vad_filter={args.vad_filter}")
    print(f"title      : {title}")

    if args.dry_run:
        print("[dry-run] 参数解析完成，未执行转写")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    if args.force or not wav.exists():
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
            check=True,
        )
        print("audio extracted", flush=True)
    else:
        print("audio reused", flush=True)

    from faster_whisper import WhisperModel
    models_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        download_root=str(models_dir),
    )
    print("model loaded", flush=True)

    segments, info = model.transcribe(
        str(wav),
        language=None if args.language == "auto" else args.language,
        beam_size=args.beam_size,
        vad_filter=args.vad_filter,
    )
    print("duration:", info.duration, flush=True)

    def ts(t):
        h = int(t // 3600)
        m = int(t % 3600 // 60)
        s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    lines_md = [f"# 转写稿：{title}", "", f"- 时长：{ts(info.duration)}",
                f"- 引擎：faster-whisper / {args.device} / {args.compute_type}",
                f"- 模型：{args.model}", f"- 语言：{info.language or args.language}", ""]
    lines_txt = []
    count = 0
    for seg in segments:
        text = seg.text.strip()
        lines_md.append(f"**[{ts(seg.start)}]** {text}")
        lines_md.append("")
        lines_txt.append(f"[{int(seg.start)}s] {text}")
        print(f"[{int(seg.start)}s] {text}", flush=True)
        count += 1

    md_path = out_dir / "transcript.md"
    txt_path = out_dir / "transcript.txt"
    md_path.write_text("\n".join(lines_md), encoding="utf-8")
    txt_path.write_text("\n".join(lines_txt), encoding="utf-8")
    print(f"segments: {count}", flush=True)
    print(f"written  : {md_path}", flush=True)
    print(f"written  : {txt_path}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

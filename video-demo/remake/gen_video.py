#!/usr/bin/env python3
"""Generate video segments and compose final video with audio + subtitles."""

import subprocess
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

WORKDIR = "D:/APPs/VentureDhealthcare/video-demo/remake"
SCENES = os.path.join(WORKDIR, "scenes")
SEGMENTS = os.path.join(WG := WORKDIR, "segments")
PUB = "D:/APPs/VentureDhealthcare/video-demo/public"
OUTPUT_DIR = os.path.join(WORKDIR, "output")
os.makedirs(SEGMENTS, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG = "C:/Windows/Fonts/msyh.ttc"
# For ffmpeg filter, escape colon in Windows path
FF_FONT_BOLD = "C\\:/Windows/Fonts/msyhbd.ttc"


def run_ffmpeg(args, desc=""):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR [{desc}]:")
        print(r.stderr[-800:] if r.stderr else "(no stderr)")
        sys.exit(1)
    print(f"  OK: {desc}")


def prepare_long_screenshot(input_path, title, output_path):
    """Scale long screenshot to 1920 width and add title bar at top."""
    img = Image.open(input_path)
    scale = 1920 / img.width
    new_h = int(img.height * scale)
    img = img.resize((1920, new_h), Image.Resampling.LANCZOS)

    # Title bar (80px)
    bar_h = 80
    bar = Image.new("RGB", (1920, bar_h), (13, 27, 61))
    draw = ImageDraw.Draw(bar)
    font = ImageFont.truetype(FONT_BOLD, 42)
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((1920 - tw) // 2, 15), title, font=font, fill=(255, 255, 255))

    combined = Image.new("RGB", (1920, new_h + bar_h), (13, 27, 61))
    combined.paste(bar, (0, 0))
    combined.paste(img, (0, bar_h))
    combined.save(output_path)
    print(
        f"  Prepared: {os.path.basename(output_path)} "
        f"({combined.width}x{combined.height})"
    )
    return new_h + bar_h


def gen_static_segment(input_png, output_mp4, duration, zoom=False):
    """Generate video from static PNG with fade in/out and optional slow zoom."""
    fade_out = max(0, duration - 1.0)
    if zoom:
        # Slow zoom from 1.0 to 1.03 using zoompan
        total_frames = int(duration * 30)
        vf = (
            f"scale=1920:1080,"
            f"zoompan=z='1+0.03*on/{total_frames}':"
            f"d={total_frames}:s=1920x1080:fps=30,"
            f"fade=t=in:st=0:d=0.5,"
            f"fade=t=out:st={fade_out}:d=1.0"
        )
    else:
        vf = f"scale=1920:1080,fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out}:d=1.0"
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            input_png,
            "-t",
            str(duration),
            "-r",
            "30",
            "-vf",
            vf,
            "-c:v",
            "h264_qsv",
            "-b:v",
            "4M",
            "-pix_fmt",
            "yuv420p",
            output_mp4,
        ],
        f"static: {os.path.basename(output_mp4)}",
    )


def gen_scroll_segment(input_png, output_mp4, duration, total_h):
    """Generate scrolling video from prepared long screenshot."""
    max_y = total_h - 1080
    scroll_start = 1.0
    scroll_end = duration - 1.0
    scroll_dur = scroll_end - scroll_start
    fade_out = max(0, duration - 1.0)

    # crop y: 0 during fade-in, scroll during middle, hold at end
    y_expr = (
        f"if(lt(t,{scroll_start}),0,"
        f"if(gt(t,{scroll_end}),{max_y},"
        f"(t-{scroll_start})/{scroll_dur}*{max_y}))"
    )
    vf = (
        f"crop=1920:1080:0:'{y_expr}',"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={fade_out}:d=1.0"
    )
    run_ffmpeg(
        [
            "-loop",
            "1",
            "-i",
            input_png,
            "-t",
            str(duration),
            "-r",
            "30",
            "-vf",
            vf,
            "-c:v",
            "h264_qsv",
            "-b:v",
            "4M",
            "-pix_fmt",
            "yuv420p",
            output_mp4,
        ],
        f"scroll: {os.path.basename(output_mp4)}",
    )


def concat_segments(segment_files, output_mp4):
    """Concatenate video segments using ffmpeg concat demuxer."""
    list_file = os.path.join(SEGMENTS, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for sf in segment_files:
            # Use forward slashes for ffmpeg
            p = sf.replace("\\", "/")
            f.write(f"file '{p}'\n")

    run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_mp4],
        "concat all segments",
    )


def compose_final(video_no_audio, audio_wav, ass_subs, output_mp4):
    """Overlay ASS subtitles and mix audio onto concatenated video."""
    # Escape colons in ASS path for ffmpeg subtitles filter
    ass_escaped = ass_subs.replace("\\", "/").replace(":", "\\:")

    run_ffmpeg(
        [
            "-i",
            video_no_audio,
            "-i",
            audio_wav,
            "-vf",
            f"subtitles='{ass_escaped}'",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "h264_qsv",
            "-b:v",
            "6M",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-shortest",
            output_mp4,
        ],
        "compose final video with subs + audio",
    )


def main():
    with open(os.path.join(WORKDIR, "timeline.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    timeline = data["segments"]
    total_dur = data["total_duration"]

    # --- Phase 1: Prepare long screenshots ---
    print("=== Phase 1: Prepare long screenshots ===")
    long_shots = {}
    # s04_eeg
    eeg_prepared = os.path.join(SCENES, "s04_eeg_prepared.png")
    long_shots["s04_eeg"] = (
        eeg_prepared,
        prepare_long_screenshot(
            os.path.join(PUB, "rehearsal_04b_eeg_after_capture.png"),
            "脑电信号智能分析",
            eeg_prepared,
        ),
    )
    # s05_policy
    policy_prepared = os.path.join(SCENES, "s05_policy_prepared.png")
    long_shots["s05_policy"] = (
        policy_prepared,
        prepare_long_screenshot(
            os.path.join(PUB, "rehearsal_06_policy.png"),
            "医保政策智能匹配",
            policy_prepared,
        ),
    )

    # --- Phase 2: Generate video segments ---
    print("\n=== Phase 2: Generate video segments ===")
    segment_files = []
    for seg in timeline:
        seg_id = seg["id"]
        duration = seg["end"] - seg["start"]
        output = os.path.join(SEGMENTS, f"{seg_id}.mp4")
        segment_files.append(output)

        if seg_id in ("s01_pain", "s02_title", "s08_ending"):
            input_png = os.path.join(SCENES, f"{seg_id}.png")
            gen_static_segment(input_png, output, duration, zoom=False)
        elif seg_id in ("s03_home", "s06_imaging", "s07_multi"):
            input_png = os.path.join(SCENES, f"{seg_id}.png")
            gen_static_segment(input_png, output, duration, zoom=True)
        elif seg_id in long_shots:
            png_path, total_h = long_shots[seg_id]
            gen_scroll_segment(png_path, output, duration, total_h)

    # --- Phase 3: Concat segments ---
    print("\n=== Phase 3: Concatenate segments ===")
    concat_output = os.path.join(SEGMENTS, "concat_no_audio.mp4")
    concat_segments(segment_files, concat_output)

    # --- Phase 4: Compose final video ---
    print("\n=== Phase 4: Compose final video ===")
    audio_path = os.path.join(WORKDIR, "audio", "mixed.wav")
    ass_path = os.path.join(WORKDIR, "subs.ass")
    final_output = os.path.join(OUTPUT_DIR, "MedSignal_demo_1080p.mp4")
    compose_final(concat_output, audio_path, ass_path, final_output)

    # --- Verify ---
    print("\n=== Verification ===")
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=width,height,codec_name,r_frame_rate",
            "-of",
            "json",
            final_output,
        ],
        capture_output=True,
        text=True,
    )
    info = json.loads(r.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    print(f"  Duration: {float(fmt.get('duration', 0)):.2f}s")
    print(f"  Size: {int(fmt.get('size', 0)) / 1024 / 1024:.1f} MB")
    for s in streams:
        print(
            f"  Stream: {s.get('codec_name')} "
            f"{s.get('width', '')}x{s.get('height', '')} "
            f"{s.get('r_frame_rate', '')}"
        )
    print(f"\n  Output: {final_output}")


if __name__ == "__main__":
    main()

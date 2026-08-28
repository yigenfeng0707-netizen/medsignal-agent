#!/usr/bin/env python3
"""Generate text scene PNGs for video segments using Pillow."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import math

WORKDIR = "D:/APPs/VentureDhealthcare/video-demo/remake"
SCENES_DIR = os.path.join(WORKDIR, "scenes")
os.makedirs(SCENES_DIR, exist_ok=True)

W, H = 1920, 1080
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG = "C:/Windows/Fonts/msyh.ttc"

# Colors
BG_TOP = (13, 27, 61)  # #0d1b3d
BG_BOT = (26, 54, 93)  # #1a365d
WHITE = (255, 255, 255)
ORANGE = (221, 107, 32)  # #dd6b20
LIGHT_BLUE = (129, 201, 224)  # light accent
GREEN = (56, 161, 105)  # medical green
GRAY = (160, 174, 192)
ACCENT_BLUE = (49, 130, 206)


def make_gradient_bg(w, h, top, bot):
    """Create vertical gradient background."""
    img = Image.new("RGB", (w, h), top)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        r = int(top[0] + (bot[0] - top[0]) * y / h)
        g = int(top[1] + (bot[1] - top[1]) * y / h)
        b = int(top[2] + (bot[2] - top[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def draw_centered_text(draw, text, font, y, color, w=W):
    """Draw text horizontally centered at given y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bbox


def draw_text_with_shadow(
    draw, text, font, x, y, color, shadow_color=(0, 0, 0), offset=2
):
    """Draw text with drop shadow."""
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=color)


def draw_centered_with_shadow(draw, text, font, y, color, w=W):
    """Draw centered text with shadow."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2
    draw_text_with_shadow(draw, text, font, x, y, color)
    return bbox


def gen_s01_pain():
    """Pain point scene: dark background with impactful text."""
    img = make_gradient_bg(W, H, BG_TOP, BG_BOT)
    draw = ImageDraw.Draw(img)

    # Decorative top line
    draw.rectangle([(W // 2 - 200, 150), (W // 2 + 200, 152)], fill=ACCENT_BLUE)

    # Main text line 1
    f1 = ImageFont.truetype(FONT_BOLD, 68)
    draw_centered_with_shadow(draw, "交了这么多年医保", f1, 280, WHITE)

    # Main text line 2 (highlight)
    f2 = ImageFont.truetype(FONT_BOLD, 68)
    draw_centered_with_shadow(draw, "用的时候，却看不懂", f2, 400, ORANGE)

    # Separator
    draw.rectangle([(W // 2 - 300, 520), (W // 2 + 300, 522)], fill=(60, 80, 120))

    # Sub text
    f3 = ImageFont.truetype(FONT_REG, 42)
    draw_centered_with_shadow(draw, "关键医疗信号，正在被错过", f3, 580, GRAY)

    # Bottom stats
    f4 = ImageFont.truetype(FONT_BOLD, 56)
    f5 = ImageFont.truetype(FONT_REG, 28)

    stats = [
        ("73%", "老年人看不懂医保目录", 350),
        ("56%", "健康预警信号被忽略", 950),
        ("89%", "慢病管理缺乏AI辅助", 1550),
    ]
    for val, label, x in stats:
        bbox = draw.textbbox((0, 0), val, font=f4)
        vw = bbox[2] - bbox[0]
        draw.text((x - vw // 2, 750), val, font=f4, fill=ORANGE)
        bbox2 = draw.textbbox((0, 0), label, font=f5)
        lw = bbox2[2] - bbox2[0]
        draw.text((x - lw // 2, 830), label, font=f5, fill=GRAY)

    img.save(os.path.join(SCENES_DIR, "s01_pain.png"))
    print("  s01_pain.png saved")


def gen_s02_title():
    """Title scene: MedSignal branding + 7 agent tags."""
    img = make_gradient_bg(W, H, BG_TOP, BG_BOT)
    draw = ImageDraw.Draw(img)

    # Glow circle behind title
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(300, 0, -10):
        alpha = int(30 * (1 - r / 300))
        gd.ellipse(
            [W // 2 - r, 120 - r // 2, W // 2 + r, 120 + r // 2 + 300],
            fill=(49, 130, 206, alpha),
        )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Logo / title
    f_logo = ImageFont.truetype(FONT_BOLD, 96)
    draw_centered_with_shadow(draw, "MedSignal", f_logo, 180, WHITE)

    # Subtitle
    f_sub = ImageFont.truetype(FONT_REG, 44)
    draw_centered_with_shadow(draw, "多模态医疗信号智能体", f_sub, 310, LIGHT_BLUE)

    # Divider
    draw.rectangle([(W // 2 - 250, 390), (W // 2 + 250, 393)], fill=ACCENT_BLUE)

    # 7 agent tags
    tags = [
        "脑电信号",
        "医保政策",
        "医学影像",
        "健康预警",
        "智能问答",
        "医师复核",
        "数据安全",
    ]
    f_tag = ImageFont.truetype(FONT_REG, 32)
    tag_w, tag_h = 220, 60
    gap = 20
    total_w = len(tags) * tag_w + (len(tags) - 1) * gap
    start_x = (W - total_w) // 2
    tag_y = 480

    for i, tag in enumerate(tags):
        x = start_x + i * (tag_w + gap)
        # Rounded rect background
        colors = [ACCENT_BLUE, GREEN, ORANGE, ACCENT_BLUE, GREEN, ORANGE, ACCENT_BLUE]
        c = colors[i % len(colors)]
        draw.rounded_rectangle(
            [(x, tag_y), (x + tag_w, tag_y + tag_h)],
            radius=10,
            fill=c + (40,) if len(c) == 3 else c,
            outline=c,
            width=2,
        )
        # Tag text
        bbox = draw.textbbox((0, 0), tag, font=f_tag)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (x + (tag_w - tw) // 2, tag_y + (tag_h - th) // 2 - 5),
            tag,
            font=f_tag,
            fill=WHITE,
        )

    # Value proposition
    f_val = ImageFont.truetype(FONT_BOLD, 48)
    draw_centered_with_shadow(draw, "从被动报销 → 主动健康", f_val, 620, WHITE)

    # Feature highlights
    f_feat = ImageFont.truetype(FONT_REG, 32)
    features = [
        "多模态信号融合 · 脑电 + 影像 + 医保",
        "AI智能体协作 · 7大领域协同",
        "医师在环 · 可信数据空间",
    ]
    for i, feat in enumerate(features):
        draw_centered_text(draw, feat, f_feat, 730 + i * 50, GRAY)

    # Bottom badge
    draw.rounded_rectangle(
        [(W // 2 - 180, 920), (W // 2 + 180, 980)],
        radius=15,
        outline=ACCENT_BLUE,
        width=2,
    )
    f_badge = ImageFont.truetype(FONT_BOLD, 28)
    draw_centered_text(draw, "VentureD Hackathon 2026", f_badge, 933, LIGHT_BLUE)

    img.save(os.path.join(SCENES_DIR, "s02_title.png"))
    print("  s02_title.png saved")


def gen_s08_ending():
    """Ending scene: memorable closing statement."""
    img = make_gradient_bg(W, H, BG_TOP, BG_BOT)
    draw = ImageDraw.Draw(img)

    # Top decorative line
    draw.rectangle([(W // 2 - 150, 200), (W // 2 + 150, 203)], fill=ACCENT_BLUE)

    # Main statement
    f1 = ImageFont.truetype(FONT_BOLD, 72)
    draw_centered_with_shadow(draw, "让关键医疗信号", f1, 300, WHITE)

    f2 = ImageFont.truetype(FONT_BOLD, 72)
    draw_centered_with_shadow(draw, "不再被错过", f2, 420, ORANGE)

    # Divider
    draw.rectangle([(W // 2 - 300, 560), (W // 2 + 300, 562)], fill=(60, 80, 120))

    # Slogan
    f3 = ImageFont.truetype(FONT_REG, 38)
    draw_centered_with_shadow(
        draw, "识别信号  ·  守护健康  ·  连接资源", f3, 620, LIGHT_BLUE
    )

    # Team info
    f4 = ImageFont.truetype(FONT_REG, 28)
    draw_centered_text(
        draw, "MedSignal Team  ·  VentureD Hackathon 2026", f4, 780, GRAY
    )

    img.save(os.path.join(SCENES_DIR, "s08_ending.png"))
    print("  s08_ending.png saved")


def gen_phone_frame_bg():
    """Generate a phone frame background for screenshot segments."""
    img = make_gradient_bg(W, H, BG_TOP, BG_BOT)
    draw = ImageDraw.Draw(img)

    # Phone frame: centered, 500x1000 area with rounded corners
    phone_w, phone_h = 540, 1080
    px = (W - phone_w) // 2
    py = 0

    # Phone shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [(px - 10, py - 5), (px + phone_w + 10, py + phone_h + 5)],
        radius=30,
        fill=(0, 0, 0, 80),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Phone body
    draw.rounded_rectangle(
        [(px, py), (px + phone_w, py + phone_h)], radius=25, fill=(20, 30, 55)
    )
    # Phone screen area (will be overlaid with screenshot)
    draw.rounded_rectangle(
        [(px + 8, py + 8), (px + phone_w - 8, py + phone_h - 8)],
        radius=20,
        fill=(240, 240, 245),
    )

    return img, (px + 8, py + 8, phone_w - 16, phone_h - 16)


def gen_screenshot_scene(screenshot_path, title_text, output_name):
    """Generate a scene with phone frame + screenshot + title overlay."""
    img, (sx, sy, sw, sh) = gen_phone_frame_bg()
    draw = ImageDraw.Draw(img)

    # Load and paste screenshot into phone screen
    try:
        shot = Image.open(screenshot_path)
        # Scale screenshot to fit phone screen width
        scale = sw / shot.width
        new_h = int(shot.height * scale)
        if new_h > sh:
            # Crop to fit
            shot = shot.resize((sw, new_h), Image.LANCZOS)
            shot = shot.crop((0, 0, sw, sh))
        else:
            shot = shot.resize((sw, new_h), Image.LANCZOS)
            # Paste centered vertically
            paste_y = sy + (sh - new_h) // 2
            img.paste(shot, (sx, paste_y))
    except Exception as e:
        print(f"  Warning: could not load {screenshot_path}: {e}")

    # Title bar at top
    f_title = ImageFont.truetype(FONT_BOLD, 42)
    draw_centered_with_shadow(draw, title_text, f_title, 30, WHITE)

    img.save(os.path.join(SCENES_DIR, output_name))
    print(f"  {output_name} saved")


def main():
    print("=== Generating text scene PNGs ===")
    gen_s01_pain()
    gen_s02_title()
    gen_s08_ending()

    print("\n=== Generating screenshot scene PNGs ===")
    pub = "D:/APPs/VentureDhealthcare/video-demo/public"
    gen_screenshot_scene(
        os.path.join(pub, "rehearsal_01_home.png"), "登录即推送健康预警", "s03_home.png"
    )
    gen_screenshot_scene(
        os.path.join(pub, "rehearsal_05c_imaging_viewer.png"),
        "医学影像 AI 辅助",
        "s06_imaging.png",
    )
    gen_screenshot_scene(
        os.path.join(pub, "rehearsal_03_chat_reply.png"),
        "多智能体协作",
        "s07_multi.png",
    )

    print("\n=== All scenes generated ===")


if __name__ == "__main__":
    main()

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# --- Settings ---
W, H = 1080, 1920  # TikTok vertical
CARD_W, CARD_H = 900, 400
CARD_RADIUS = 40
CARD_COLOR = (34, 39, 46, 255)  # Dark card
SHADOW_OFFSET = 20
SHADOW_COLOR = (0, 0, 0, 120)
GRADIENT_TOP = (58, 123, 213)
GRADIENT_BOTTOM = (34, 193, 195)

# --- Load assets ---
icon_path = "assets/workplace.jpg"
font_bold = "fonts/Roboto-Bold.ttf"
font_regular = "fonts/Roboto-Regular.ttf"

# --- Create gradient background ---
bg = Image.new("RGB", (W, H), (255, 255, 255))
draw = ImageDraw.Draw(bg)
for y in range(H):
    r = int(GRADIENT_TOP[0] + (GRADIENT_BOTTOM[0] - GRADIENT_TOP[0]) * y / H)
    g = int(GRADIENT_TOP[1] + (GRADIENT_BOTTOM[1] - GRADIENT_TOP[1]) * y / H)
    b = int(GRADIENT_TOP[2] + (GRADIENT_BOTTOM[2] - GRADIENT_TOP[2]) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# --- Draw shadow for card ---
shadow = Image.new("RGBA", (CARD_W + SHADOW_OFFSET*2, CARD_H + SHADOW_OFFSET*2), (0, 0, 0, 0))
shadow_draw = ImageDraw.Draw(shadow)
shadow_draw.rounded_rectangle(
    [SHADOW_OFFSET, SHADOW_OFFSET, CARD_W + SHADOW_OFFSET, CARD_H + SHADOW_OFFSET],
    radius=CARD_RADIUS,
    fill=SHADOW_COLOR
)
shadow = shadow.filter(ImageFilter.GaussianBlur(10))
bg.paste(shadow, ((W - CARD_W)//2 - SHADOW_OFFSET, 400 - SHADOW_OFFSET), shadow)

# --- Draw card ---
card = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
card_draw = ImageDraw.Draw(card)
card_draw.rounded_rectangle(
    [0, 0, CARD_W, CARD_H],
    radius=CARD_RADIUS,
    fill=CARD_COLOR
)

# --- Add circular icon ---
icon = Image.open(icon_path).convert("RGBA").resize((100, 100))
mask = Image.new("L", (100, 100), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
icon.putalpha(mask)
card.paste(icon, (40, 40), icon)

# --- Add text ---
community = "r/IndianWorkplace"
title = "As sleep deprivation is a well-documented form of torture..."
desc = "Just pulled an all nighter, it was for program monitoring work..."
upvotes = "↑ 12.3k"
comments = "💬 1.2k"

font_title = ImageFont.truetype(font_bold, 38)
font_desc = ImageFont.truetype(font_regular, 28)
font_meta = ImageFont.truetype(font_regular, 24)

# Community name
card_draw.text((160, 50), community, font=font_meta, fill=(215, 218, 220))

# Title (bold)
card_draw.text((40, 160), title, font=font_title, fill=(255, 255, 255))

# Description (smaller)
card_draw.text((40, 220), desc, font=font_desc, fill=(200, 200, 200))

# Upvotes and comments (bottom right)
card_draw.text((CARD_W - 250, CARD_H - 50), upvotes, font=font_meta, fill=(255, 180, 80))
card_draw.text((CARD_W - 120, CARD_H - 50), comments, font=font_meta, fill=(120, 200, 255))

# --- Paste card onto background ---
bg.paste(card, ((W - CARD_W)//2, 400), card)

# --- Save ---
bg.save("tiktok_reddit_post.png")
print("Saved as tiktok_reddit_post.png")
import json
import re
from pathlib import Path
from typing import Dict, Final
import time
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

import translators
from playwright.sync_api import ViewportSize, sync_playwright
from rich.progress import track

from utils import settings
from utils.console import print_step, print_substep
from utils.imagenarator import imagemaker
from utils.playwright import clear_cookie_by_name
from utils.videos import save_data

__all__ = ["get_screenshots_of_reddit_posts"]


def split_comment_into_chunks(text, min_words=1, max_words=3):
    """
    Splits a comment into chunks of 1-3 words (default), for animated display.
    Returns a list of text chunks.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_size = min(max_words, len(words) - i)
        # Optionally randomize chunk size between min_words and max_words
        # chunk_size = random.randint(min_words, min(chunk_size, max_words))
        chunks.append(' '.join(words[i:i+chunk_size]))
        i += chunk_size
    return chunks

def get_screenshots_of_reddit_posts(reddit_object: dict, screenshot_num: int):
    """Downloads screenshots of reddit posts with improved anti-bot measures and supports chunked comments"""
    print_step("Taking screenshots with improved anti-bot measures...")
    
    # Get reddit ID and create directories
    reddit_id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)

    try:
        # Get dimensions from settings
        screenshot_width = int(700)
        post_height = int(150)

        # Create title screenshot
        create_reddit_style_screenshot(
            reddit_object["thread_title"],
            f"assets/temp/{reddit_id}/png/title.png",
            screenshot_width,
            post_height,
            is_title=True,
            subreddit=settings.config["reddit"]["thread"]["subreddit"]
        )

        # Create comment screenshots (chunked: 1-3 words per image)
        if screenshot_num > 0:
            print_substep(f"Creating {screenshot_num} comment screenshots (chunked)...")
            for i in range(screenshot_num):
                if i < len(reddit_object["comments"]):
                    comment = reddit_object["comments"][i]
                    comment_text = comment["comment_body"]
                    chunks = split_comment_into_chunks(comment_text, min_words=1, max_words=3)
                    for j, chunk in enumerate(chunks):
                        create_reddit_style_screenshot(
                            chunk,
                            f"assets/temp/{reddit_id}/png/comment_{i}_{j}.png",
                            screenshot_width,
                            post_height,
                            is_title=False,
                            comment_data=comment
                        )

        print_substep("Screenshots created successfully!")
            
    except Exception as err:
        print_substep(f"Error during screenshot creation: {str(err)}", style="red")
        raise err

def create_reddit_style_screenshot(text, output_path, width, height, is_title=True, subreddit=None, comment_data=None):
    """Creates a Reddit-style screenshot with visually attractive padding, spacing, and fonts"""
    try:
        # Enhanced padding and spacing
        horizontal_padding = int(width * 0.10)  # 10% of width for side padding
        vertical_padding = int(height * 0.08)   # 8% of height for top/bottom padding
        inner_padding = int(width * 0.045)      # 4.5% of width for inner spacing

        # Card background and shadow
        card_radius = 32
        card_bg_color = (255, 255, 255, 245)
        shadow_color = (0, 0, 0, 28)
        shadow_offset = 8

        # Increase width/height for padding and shadow
        total_width = width + (horizontal_padding * 2) + shadow_offset
        total_height = height + (vertical_padding * 2) + shadow_offset

        # Create base image with transparency
        post_image = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(post_image)

        # Draw shadow
        shadow_box = [
            shadow_offset,
            shadow_offset,
            total_width - shadow_offset,
            total_height - shadow_offset
        ]
        draw.rounded_rectangle(shadow_box, radius=card_radius, fill=shadow_color)

        # Draw card background
        card_box = [
            0,
            0,
            total_width - shadow_offset,
            total_height - shadow_offset
        ]
        draw.rounded_rectangle(card_box, radius=card_radius, fill=card_bg_color)

        # Resolve resource paths relative to project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        # Load fonts (use bold for usernames/subreddit)
        base_font_size = int(width * 0.032)  # Larger base font for readability
        font_small = ImageFont.truetype(os.path.join(project_root, "fonts", "Roboto-Regular.ttf"), int(base_font_size * 0.75))
        font_small_bold = ImageFont.truetype(os.path.join(project_root, "fonts", "Roboto-Bold.ttf"), int(base_font_size * 0.75))
        font_title = ImageFont.truetype(os.path.join(project_root, "fonts", "Roboto-Bold.ttf"), int(base_font_size * 1.5))
        font_body = ImageFont.truetype(os.path.join(project_root, "fonts", "Roboto-Regular.ttf"), int(base_font_size * 1.1))

        # Colors
        text_gray = (26, 26, 27)
        secondary_gray = (129, 131, 132)
        accent_blue = (0, 121, 211)

        # Create circular icon
        workplace_image = Image.open(os.path.join(project_root, "assets", "workplace.jpg"))
        icon_size = (int(width * 0.06), int(width * 0.06))  # 6% of width for icon
        workplace_image = workplace_image.resize(icon_size)

        # Create circular mask
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)

        # Layout positions
        icon_position = (horizontal_padding, vertical_padding)
        post_image.paste(circular_icon, icon_position, circular_icon)

        text_start_x = icon_position[0] + icon_size[0] + inner_padding
        meta_y = vertical_padding

        if is_title:
            # Subreddit (bold, blue), metadata, and title
            draw.text((text_start_x, meta_y), f"r/{subreddit}", font=font_small_bold, fill=accent_blue)
            draw.text((text_start_x + int(width * 0.22), meta_y), "• Posted now", font=font_small, fill=secondary_gray)
            draw.text((text_start_x, meta_y + int(base_font_size * 0.95)), "Posted by u/RedditBot", font=font_small, fill=secondary_gray)

            # Title text
            content_y = meta_y + icon_size[1] + int(base_font_size * 1.2)
            font_to_use = font_title
        else:
            # Username (bold), metadata, and comment
            username = "u/Commenter"
            if comment_data and "comment_author" in comment_data:
                username = f'u/{comment_data["comment_author"]}'
            draw.text((text_start_x, meta_y), username, font=font_small_bold, fill=text_gray)
            draw.text((text_start_x + int(width * 0.22), meta_y), "• Now", font=font_small, fill=secondary_gray)

            # Comment text
            content_y = meta_y + icon_size[1] + int(base_font_size * 1.2)
            font_to_use = font_body

        # Word wrap text with adjusted width for padding
        max_width = width - (inner_padding * 2)
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_to_use)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Draw text with increased line spacing
        for i, line in enumerate(lines):
            draw.text(
                (horizontal_padding, content_y + (i * int(base_font_size * 1.7))),
                line,
                font=font_to_use,
                fill=text_gray
            )

        # Save the image
        # Flatten to RGB with white background before saving (fixes ffmpeg overlay issues)
        if post_image.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", post_image.size, (255, 255, 255))
            bg.paste(post_image, mask=post_image.split()[-1])
            bg.save(output_path)
        else:
            post_image.save(output_path)
        return post_image

    except Exception as e:
        print_substep(f"Error creating screenshot: {str(e)}")
        return None

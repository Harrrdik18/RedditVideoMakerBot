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


def get_screenshots_of_reddit_posts(reddit_object: dict, screenshot_num: int):
    """Downloads screenshots of reddit posts with improved anti-bot measures"""
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

        # Create comment screenshots
        if screenshot_num > 0:
            print_substep(f"Creating {screenshot_num} comment screenshots...")
            for i in range(screenshot_num):
                if i < len(reddit_object["comments"]):
                    comment = reddit_object["comments"][i]
                    create_reddit_style_screenshot(
                        comment["comment_body"],
                        f"assets/temp/{reddit_id}/png/comment_{i}.png",
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
    """Creates a Reddit-style screenshot with proper dimensions and styling"""
    try:
        # Calculate padding - only horizontal padding
        horizontal_padding = int(width * 0.12)  # 8% of width for side padding
        inner_padding = int(width * 0.04)  # 4% of width for inner spacing
        
        # Increase only the width to accommodate padding
        total_width = width + (horizontal_padding * 2)
        total_height = height  # Keep original height
        
        # Create new image with padding
        post_image = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(post_image)
        
        # Load fonts
        base_font_size = int(width * 0.02)  # 2% of width for base font
        font_small = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), base_font_size)
        font_title = ImageFont.truetype(os.path.join("fonts", "Roboto-Medium.ttf"), int(base_font_size * 1.5))
        font_body = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), int(base_font_size * 1.2))
        
        # Colors
        text_gray = (26, 26, 27)
        secondary_gray = (129, 131, 132)
        
        # Create circular icon
        workplace_image = Image.open("assets/workplace.jpg")
        icon_size = (int(width * 0.04), int(width * 0.04))  # 4% of width for icon
        workplace_image = workplace_image.resize(icon_size)
        
        # Create circular mask
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)
        
        if is_title:
            # Title post layout with horizontal padding
            icon_position = (horizontal_padding, inner_padding)  # Only horizontal padding
            post_image.paste(circular_icon, icon_position, circular_icon)
            
            # Subreddit and metadata
            text_start_x = icon_position[0] + icon_size[0] + inner_padding
            draw.text((text_start_x, inner_padding), f"r/{subreddit}", font=font_small, fill=text_gray)
            draw.text((text_start_x + int(width * 0.15), inner_padding), "• Posted now", font=font_small, fill=secondary_gray)
            draw.text((text_start_x, inner_padding + base_font_size + 2), "Posted by u/RedditBot", font=font_small, fill=secondary_gray)
            
            # Title text starting position
            content_y = inner_padding + icon_size[1] + int(base_font_size * 1.5)
            font_to_use = font_title
        else:
            # Comment layout with horizontal padding
            icon_position = (horizontal_padding, inner_padding)  # Only horizontal padding
            post_image.paste(circular_icon, icon_position, circular_icon)
            
            # Comment metadata
            text_start_x = icon_position[0] + icon_size[0] + inner_padding
            draw.text((text_start_x, inner_padding), "u/Commenter", font=font_small, fill=text_gray)
            draw.text((text_start_x + int(width * 0.15), inner_padding), "• Now", font=font_small, fill=secondary_gray)
            
            # Comment text starting position
            content_y = inner_padding + icon_size[1] + inner_padding
            font_to_use = font_body
        
        # Word wrap text with adjusted width for padding
        max_width = width - (inner_padding * 3)  # Account for padding
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
        lines.append(' '.join(current_line))
        
        # Draw text
        for i, line in enumerate(lines):
            draw.text(
                (horizontal_padding, content_y + (i * int(base_font_size * 1.5))),
                line,
                font=font_to_use,
                fill=text_gray
            )
        
        # Save the image
        post_image.save(output_path)
        return post_image
        
    except Exception as e:
        print_substep(f"Error creating screenshot: {str(e)}")
        return None

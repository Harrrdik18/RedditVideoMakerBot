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
        W = int(settings.config["settings"]["resolution_w"])
        screenshot_width = int((W * 40) // 100)
        post_height = int(screenshot_width * (9/16))

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
        # Calculate proper dimensions
        W = int(settings.config["settings"]["resolution_w"])
        H = int(settings.config["settings"]["resolution_h"])
        
        # Adjust width to be 40% of video width instead of 45% to ensure full visibility
        screenshot_width = int((W * 40) // 100)  # For 1920x1080 this gives 768 pixels
        # Calculate height while maintaining aspect ratio
        screenshot_height = int(screenshot_width * (9/16))  # This maintains 16:9 ratio
        
        # Create new image with dark background
        post_image = Image.new('RGBA', (screenshot_width, screenshot_height), (26, 26, 27, 255))
        draw = ImageDraw.Draw(post_image)
        
        # Calculate proportional sizes based on new width
        padding_x = int(screenshot_width * 0.02)  # 2% of width for padding
        icon_size = (int(screenshot_width * 0.04), int(screenshot_width * 0.04))  # 4% of width for icon
        base_font_size = int(screenshot_width * 0.02)  # 2% of width for base font
        
        # Load fonts with adjusted sizes
        font_small = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), base_font_size)
        font_title = ImageFont.truetype(os.path.join("fonts", "Roboto-Medium.ttf"), int(base_font_size * 1.5))
        font_body = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), int(base_font_size * 1.2))
        
        # Colors
        text_gray = (215, 218, 220)
        secondary_gray = (129, 131, 132)
        
        # Create circular icon
        workplace_image = Image.open("assets/workplace.jpg")
        workplace_image = workplace_image.resize(icon_size)
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)
        
        if is_title:
            # Title post layout
            icon_position = (padding_x, padding_x)
            post_image.paste(circular_icon, icon_position, circular_icon)
            
            # Subreddit and metadata
            text_start_x = icon_position[0] + icon_size[0] + padding_x
            draw.text((text_start_x, padding_x), f"r/{subreddit}", font=font_small, fill=text_gray)
            draw.text((text_start_x + int(screenshot_width * 0.15), padding_x), "• Posted now", font=font_small, fill=secondary_gray)
            draw.text((text_start_x, padding_x + base_font_size + 2), "Posted by u/RedditBot", font=font_small, fill=secondary_gray)
            
            # Title text starting position
            content_y = padding_x + icon_size[1] + int(base_font_size * 1.5)
            font_to_use = font_title
        else:
            # Comment layout - simplified for better focus on content
            icon_position = (padding_x, padding_x)
            post_image.paste(circular_icon, icon_position, circular_icon)
            
            # Comment metadata
            text_start_x = icon_position[0] + icon_size[0] + padding_x
            draw.text((text_start_x, padding_x), "u/Commenter", font=font_small, fill=text_gray)
            draw.text((text_start_x + int(screenshot_width * 0.15), padding_x), "• Now", font=font_small, fill=secondary_gray)
            
            # Comment text starting position
            content_y = padding_x + icon_size[1] + padding_x
            font_to_use = font_body
        
        # Word wrap text with adjusted width
        max_width = screenshot_width - (padding_x * 3)  # Additional padding for safety
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
        
        # Draw text with adjusted line height
        line_height = int(base_font_size * (1.8 if is_title else 1.4))
        for i, line in enumerate(lines):
            draw.text((padding_x, content_y + i*line_height), line, font=font_to_use, fill=text_gray)
        
        # Add interaction elements at the bottom for title only
        if is_title:
            interaction_y = screenshot_height - (base_font_size * 2.5)  # Moved up slightly
            draw.text((padding_x, interaction_y), "↑", font=font_small, fill=secondary_gray)
            draw.text((padding_x * 2, interaction_y), "1.2k", font=font_small, fill=secondary_gray)
            draw.text((padding_x * 4, interaction_y), "↓", font=font_small, fill=secondary_gray)
            draw.text((padding_x * 6, interaction_y), "💬 234", font=font_small, fill=secondary_gray)
        
        # Save the image
        post_image.save(output_path)
        
    except Exception as e:
        print_substep(f"Error creating screenshot: {str(e)}")
        raise e

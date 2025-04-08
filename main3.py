#!/usr/bin/env python
import math
import sys
from os import name
from pathlib import Path
from subprocess import Popen
import shutil
import os

from utils import settings
from utils.cleanup import cleanup
from utils.console import print_markdown, print_step, print_substep
from utils.ffmpeg_install import ffmpeg_install
from utils.id import id
from video_creation.background import chop_background
from video_creation.final_video import make_final_video
from video_creation.voices import save_text_to_mp3

def setup_directories(reddit_id):
    """Create necessary directories and copy files to the correct locations"""
    # Create directories
    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)
    Path("assets/backgrounds/video").mkdir(parents=True, exist_ok=True)
    
    # Copy example.png to the correct locations
    shutil.copy("ex2.png", f"assets/temp/{reddit_id}/png/title.png")
    shutil.copy("ex2.png", f"assets/temp/{reddit_id}/png/comment_0.png")
    
    # Copy test.mp4 to backgrounds directory
    target_path = "assets/backgrounds/video/test.mp4"
    if not os.path.exists(target_path):
        print_substep(f"Copying test.mp4 to {target_path}")
        shutil.copy("test.mp4", target_path)

def main() -> None:
    # First, modify settings to disable background audio
    settings.config["settings"]["background"]["background_audio_volume"] = 0
    
    # Add a custom background configuration for test.mp4
    settings.background_options = {
        "video": {
            "test": ["local", "test.mp4", "test", "center"]
        },
        "audio": None
    }
    
    # Set the background video in settings to use our custom configuration
    settings.config["settings"]["background"]["background_video"] = "test"
    
    # Create a mock reddit object with the actual post content
    reddit_object = {
        "thread_id": "1jot23x",
        "thread_title": "As sleep deprivation is a well-documented form of torture, how does corporates justify making their employees work 24/7?",
        "thread_url": "https://www.reddit.com/r/IndianWorkplace/comments/1jot23x/",
        "thread_post": "Just pulled an all nighter, it was for program monitoring work where I just had to watch the screen for the whole night and inform IT people if any of our finance programs broke down.\n\nThen in the morning the people continued asking me to work till 12 pm. So essentially I had no sleep from yesterday till today 12 pm. After which I tried sleeping but couldn't fall asleep. It literally broke me from inside, I have had pulled all nighters in the past but that was due to travel, my personal work or some celebrations etc.\n\nBut this time I completely feel broken from inside, knowing that I'll have to do this continously for the coming 4 days and then once at the beginning of every month.\n\nI don't know why but this just feels like torture to me.",
        "comments": [{"comment_body": "Example comment", "comment_url": "https://www.reddit.com/r/IndianWorkplace/comments/1jot23x/comment/", "comment_id": "123"}]
    }
    
    # Generate a reddit ID for the temp folders
    reddit_id = id(reddit_object)
    
    # Set up directories and copy files
    setup_directories(reddit_id)
    
    # Generate TTS audio
    length, number_of_comments = save_text_to_mp3(reddit_object)
    length = math.ceil(length)
    
    # Get background config from settings
    bg_config = {
        "video": settings.background_options["video"]["test"],
        "audio": None
    }
    
    # Process background
    chop_background(bg_config, length, reddit_object)
    
    # Create final video
    make_final_video(number_of_comments, length, reddit_object, bg_config)
    
    # Cleanup
    print_markdown("## Clearing temp files")
    cleanup(reddit_id)

if __name__ == "__main__":
    if sys.version_info.major != 3 or sys.version_info.minor not in [10, 11]:
        print(
            "This program requires Python 3.10 or 3.11. Please install the correct version and try again."
        )
        sys.exit()
    
    ffmpeg_install()
    directory = Path().absolute()
    config = settings.check_toml(
        f"{directory}/utils/.config.template.toml", f"{directory}/config.toml"
    )
    if config is False:
        sys.exit()
        
    try:
        main()
        print_step("Done! 🎉 The video is in the results folder 📁")
    except Exception as err:
        print_step(
            f"An error occurred! Please check the error message below:\n"
            f"Error: {err}"
        )
        raise err
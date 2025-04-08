#!/usr/bin/env python
import sys
from pathlib import Path
import json
from utils import settings
from utils.console import print_step, print_substep
import yt_dlp
import random
import time

def load_background_options():
    """Load background options from JSON files"""
    try:
        # Load background videos
        with open("./utils/background_videos.json") as json_file:
            video_options = json.load(json_file)
            # Remove comment
            if "__comment" in video_options:
                del video_options["__comment"]
        return video_options
    except Exception as e:
        print(f"Error loading background options: {str(e)}")
        return None

def get_random_user_agent():
    """Return a random modern user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Edge/123.0.0.0'
    ]
    return random.choice(user_agents)

def download_background_video(uri: str, filename: str):
    """Downloads a background video from YouTube with anti-bot measures."""
    try:
        Path("./assets/backgrounds/video/").mkdir(parents=True, exist_ok=True)
        
        if Path(f"assets/backgrounds/video/{filename}").is_file():
            print_substep(f"Video {filename} already exists, skipping download.")
            return True
        
        print_step("Downloading background video with enhanced anti-bot measures...")
        print_substep(f"Source: {uri}")
        print_substep(f"Target: {filename}")
        
        # Enhanced options to bypass restrictions
        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]",
            "outtmpl": f"assets/backgrounds/video/{filename}",
            "retries": 15,
            "fragment_retries": 10,
            "quiet": False,
            "no_warnings": False,
            "progress": True,
            "user_agent": get_random_user_agent(),
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            },
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "cookiefile": "youtube_cookies.txt",  # Save cookies to file
            "socket_timeout": 30,
        }

        # Add random delay before download
        delay = random.uniform(2, 5)
        print_substep(f"Waiting {delay:.2f} seconds before download...")
        time.sleep(delay)

        max_attempts = 3
        current_attempt = 1

        while current_attempt <= max_attempts:
            try:
                print_substep(f"Download attempt {current_attempt}/{max_attempts}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(uri)
                
                if Path(f"assets/backgrounds/video/{filename}").is_file():
                    print_substep("Background video downloaded successfully! 🎉", style="bold green")
                    return True
                
            except Exception as e:
                print_substep(f"Attempt {current_attempt} failed: {str(e)}", style="yellow")
                if current_attempt < max_attempts:
                    wait_time = random.uniform(5, 10)
                    print_substep(f"Waiting {wait_time:.2f} seconds before next attempt...")
                    time.sleep(wait_time)
                    # Get new user agent for next attempt
                    ydl_opts["user_agent"] = get_random_user_agent()
                current_attempt += 1
        
        print_substep("All download attempts failed!", style="bold red")
        return False
            
    except Exception as err:
        print_substep(f"Fatal error during download: {str(err)}", style="bold red")
        return False

def debug_video():
    """Debug the video download process"""
    print_step("Starting video download debug with anti-bot measures...")
    
    # Test with a specific video first
    test_video = {
        "uri": "https://www.youtube.com/watch?v=n_Dv4JMiwK8",  # Your video URL
        "filename": "test_background.mp4"
    }
    
    print_step("Attempting test download...")
    success = download_background_video(test_video["uri"], test_video["filename"])
    
    if success:
        print_step("Video download debug completed successfully! ✅")
        print_substep(f"Video saved to: assets/backgrounds/video/{test_video['filename']}")
    else:
        print_step("Video download debug failed! ❌")
        print_substep("Try these alternatives:")
        print_substep("1. Use a VPN or different network")
        print_substep("2. Try downloading at a different time")
        print_substep("3. Consider using a local video file instead")

if __name__ == "__main__":
    try:
        directory = Path().absolute()
        config = settings.check_toml(
            f"{directory}/utils/.config.template.toml", f"{directory}/config.toml"
        )
        if config is False:
            sys.exit()
        
        debug_video()
        
    except KeyboardInterrupt:
        print("\nDebug process interrupted by user")
        sys.exit()
    except Exception as err:
        print(f"Fatal error: {str(err)}")
        raise err
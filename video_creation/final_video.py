import multiprocessing
import os
import re
import tempfile
import textwrap
import threading
import time
from os.path import exists  # Needs to be imported specifically
from pathlib import Path
from typing import Dict, Final, Tuple

import ffmpeg
import os.path
import translators
from PIL import Image, ImageDraw, ImageFont, ImageOps
from rich.console import Console
from rich.progress import track

from utils import settings
from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.fonts import getheight
from utils.thumbnail import create_thumbnail
from utils.videos import save_data

console = Console()


class ProgressFfmpeg(threading.Thread):
    def __init__(self, vid_duration_seconds, progress_update_callback):
        threading.Thread.__init__(self, name="ProgressFfmpeg")
        self.stop_event = threading.Event()
        self.output_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.vid_duration_seconds = vid_duration_seconds
        self.progress_update_callback = progress_update_callback

    def run(self):
        while not self.stop_event.is_set():
            latest_progress = self.get_latest_ms_progress()
            if latest_progress is not None:
                completed_percent = latest_progress / self.vid_duration_seconds
                self.progress_update_callback(completed_percent)
            time.sleep(1)

    def get_latest_ms_progress(self):
        lines = self.output_file.readlines()

        if lines:
            for line in lines:
                if "out_time_ms" in line:
                    out_time_ms_str = line.split("=")[1].strip()
                    if out_time_ms_str.isnumeric():
                        return float(out_time_ms_str) / 1000000.0
                    else:
                        # Handle the case when "N/A" is encountered
                        return None
        return None

    def stop(self):
        self.stop_event.set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()


def name_normalize(name: str) -> str:
    name = re.sub(r'[?\\"%*:|<>]', "", name)
    name = re.sub(r"( [w,W]\s?\/\s?[o,O,0])", r" without", name)
    name = re.sub(r"( [w,W]\s?\/)", r" with", name)
    name = re.sub(r"(\d+)\s?\/\s?(\d+)", r"\1 of \2", name)
    name = re.sub(r"(\w+)\s?\/\s?(\w+)", r"\1 or \2", name)
    name = re.sub(r"\/", r"", name)

    lang = settings.config["reddit"]["thread"]["post_lang"]
    if lang:
        print_substep("Translating filename...")
        translated_name = translators.translate_text(name, translator="google", to_language=lang)
        return translated_name
    else:
        return name


def prepare_background(reddit_id: str, W: int, H: int) -> str:
    output_path = f"assets/temp/{reddit_id}/background_noaudio.mp4"
    output = (
        ffmpeg.input(f"assets/temp/{reddit_id}/background.mp4")
        .filter("crop", f"ih*({W}/{H})", "ih")
        .output(
            output_path,
            an=None,
            **{
                "c:v": "h264",
                "b:v": "20M",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
            },
        )
        .overwrite_output()
    )
    try:
        output.run(quiet=True)
    except ffmpeg.Error as e:
        print(e.stderr.decode("utf8"))
        exit(1)
    return output_path


def create_fancy_thumbnail(image, text, text_color, padding, wrap=35):
    print_step(f"Creating Reddit-style thumbnail for: {text}")
    
    try:
        # Create a new image with dark background (Reddit dark mode)
        post_size = (700, 150)
        post_image = Image.new('RGBA', post_size, (255, 255, 255, 255))  # Reddit dark mode background
        
        # Calculate the Reddit post area size (centered in the larger image)
        reddit_post_width = 600
        reddit_post_height = 150
        reddit_post = Image.new('RGBA', (reddit_post_width, reddit_post_height), (255, 255, 255, 255))
        
        # Open and resize workplace image to a circular icon
        workplace_image = Image.open("assets/workplace.jpg")
        icon_size = (32, 32)  # Reddit-style icon size
        workplace_image = workplace_image.resize(icon_size)
        
        # Create a circular mask for the icon
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)
        
        # Draw on the Reddit post area
        draw = ImageDraw.Draw(reddit_post)
        
        # Load fonts
        font_small = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 16)
        font_title = ImageFont.truetype(os.path.join("fonts", "Roboto-Medium.ttf"), 20)
        font_body = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 14)
        
        # Colors
        text_gray = (26, 26, 27)
        secondary_gray = (26, 26, 27)  # Reddit dark mode secondary text
        
        # Header section
        icon_position = (16, 16)
        reddit_post.paste(circular_icon, icon_position, circular_icon)
        
        # Subreddit and metadata
        subreddit = settings.config["reddit"]["thread"]["subreddit"]
        draw.text((56, 19), f"r/{subreddit}", font=font_small, fill=text_gray)

        
        # Title (with word wrap)
        title_x = 16
        title_y = 70
        
        # Word wrap for title
        words = text.split()
        lines = []
        current_line = []
        max_width = reddit_post_width - 32  # Account for padding

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_title)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))

        # Draw title
        for i, line in enumerate(lines):
            draw.text((title_x, title_y + i*25), line, font=font_title, fill=text_gray)
        
        # Add interaction elements at the bottom
        interaction_y = title_y + (len(lines) * 25) + 50
        draw.text((20, interaction_y), "↑", font=font_small, fill=secondary_gray)
        draw.text((40, interaction_y), "1.2k", font=font_small, fill=secondary_gray)
        draw.text((80, interaction_y), "↓", font=font_small, fill=secondary_gray)
        draw.text((140, interaction_y), "💬 234", font=font_small, fill=secondary_gray)
        
        # Calculate position to center the Reddit post in the larger image
        paste_x = (post_size[0] - reddit_post_width) // 2
        paste_y = (post_size[1] - reddit_post_height) // 2
        
        # Paste the Reddit post onto the larger image
        post_image.paste(reddit_post, (paste_x, paste_y))
        
        return post_image
        
    except Exception as e:
        print_substep(f"Error creating thumbnail: {str(e)}")
        # If there's an error, return the original template as fallback
        return image


def merge_background_audio(audio: ffmpeg, reddit_id: str):
    """Gather an audio and merge with assets/backgrounds/background.mp3
    Args:
        audio (ffmpeg): The TTS final audio but without background.
        reddit_id (str): The ID of subreddit
    """
    background_audio_volume = settings.config["settings"]["background"]["background_audio_volume"]
    if background_audio_volume == 0:
        return audio  # Return the original audio
    else:
        # sets volume to config
        bg_audio = ffmpeg.input(f"assets/temp/{reddit_id}/background.mp3").filter(
            "volume",
            background_audio_volume,
        )
        # Merges audio and background_audio
        merged_audio = ffmpeg.filter([audio, bg_audio], "amix", duration="longest")
        return merged_audio  # Return merged audio


def make_final_video(
    number_of_clips: int,
    length: int,
    reddit_obj: dict,
    background_config: Dict[str, Tuple],
):
    """Gathers audio clips, gathers all screenshots, stitches them together and saves the final video to assets/temp
    Args:
        number_of_clips (int): Index to end at when going through the screenshots'
        length (int): Length of the video
        reddit_obj (dict): The reddit object that contains the posts to read.
        background_config (Tuple[str, str, str, Any]): The background config to use.
    """
    # settings values
    W: Final[int] = int(settings.config["settings"]["resolution_w"])
    H: Final[int] = int(settings.config["settings"]["resolution_h"])

    opacity = settings.config["settings"]["opacity"]

    reddit_id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    allowOnlyTTSFolder: bool = (
        settings.config["settings"]["background"]["enable_extra_audio"]
        and settings.config["settings"]["background"]["background_audio_volume"] != 0
    )

    print_step("Creating the final video 🎥")

    background_clip = ffmpeg.input(prepare_background(reddit_id, W=W, H=H))

    # Gather all audio clips
    audio_clips = list()
    if number_of_clips == 0 and settings.config["settings"]["storymode"] == "false":
        print(
            "No audio clips to gather. Please use a different TTS or post."
        )  # This is to fix the TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
        exit()
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"] == 0:
            audio_clips = [ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3")]
            audio_clips.insert(1, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio.mp3"))
        elif settings.config["settings"]["storymodemethod"] == 1:
            audio_clips = [
                ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                for i in track(range(number_of_clips + 1), "Collecting the audio files...")
            ]
            audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))

    else:
        audio_clips = [
            ffmpeg.input(f"assets/temp/{reddit_id}/mp3/{i}.mp3") for i in range(number_of_clips)
        ]
        audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))

        audio_clips_durations = [
            float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/{i}.mp3")["format"]["duration"])
            for i in range(number_of_clips)
        ]
        audio_clips_durations.insert(
            0,
            float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
        )
    audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)
    ffmpeg.output(
        audio_concat, f"assets/temp/{reddit_id}/audio.mp3", **{"b:a": "192k"}
    ).overwrite_output().run(quiet=True)

    console.log(f"[bold green] Video Will Be: {length} Seconds Long")

    screenshot_width = int((W * 45) // 100)
    audio_path = f"assets/temp/{reddit_id}/audio.mp3"
    if os.path.exists(audio_path):
        audio = ffmpeg.input(audio_path)
        final_audio = merge_background_audio(audio, reddit_id)
    else:
        # Use silent audio if no audio file exists
        print_substep("No audio found, using silent audio track.")
        final_audio = ffmpeg.input(f"anullsrc=r=44100:cl=mono", f="lavfi").output("pipe:", t=length, format="wav")["a"]

    image_clips = list()

    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)

    # Credits to tim (beingbored)
    # get the title_template image and draw a text in the middle part of it with the title of the thread
    # Comment out or remove the original title template loading
    # title_template = Image.open("assets/title_template.png")
    # Instead, create a blank canvas
    # Use the same screenshot function for the title as for comments, for visual consistency
    from video_creation.screenshot_downloader import create_reddit_style_screenshot, get_screenshots_of_reddit_posts

    title = reddit_obj["thread_title"]
    title = name_normalize(title)

    # Generate all screenshots (title and chunked comments)
    get_screenshots_of_reddit_posts(
        reddit_object=reddit_obj,
        screenshot_num=number_of_clips
    )

    image_clips.insert(
        0,
        ffmpeg.input(f"assets/temp/{reddit_id}/png/title.png")["v"].filter(
            "scale", screenshot_width, -1
        ),
    )

    current_time = 0
    if settings.config["settings"]["storymode"]:
        audio_clips_durations = [
            float(
                ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")["format"]["duration"]
            )
            for i in range(number_of_clips)
        ]
        audio_clips_durations.insert(
            0,
            float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
        )
        if settings.config["settings"]["storymodemethod"] == 0:
            image_clips.insert(
                1,
                ffmpeg.input(f"assets/temp/{reddit_id}/png/story_content.png").filter(
                    "scale", screenshot_width, -1
                ),
            )
            background_clip = background_clip.overlay(
                image_clips[0],
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[0]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[0]
        elif settings.config["settings"]["storymodemethod"] == 1:
            for i in track(range(0, number_of_clips + 1), "Collecting the image files..."):
                image_clips.append(
                    ffmpeg.input(f"assets/temp/{reddit_id}/png/img{i}.png")["v"].filter(
                        "scale", screenshot_width, -1
                    )
                )
                background_clip = background_clip.overlay(
                    image_clips[i],
                    enable=f"between(t,{current_time},{current_time + audio_clips_durations[i]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )
                current_time += audio_clips_durations[i]
    else:
        # --- New logic for margin and chunked comment display with fade transitions ---
        margin_x = int(W * 0.05)
        margin_y = int(H * 0.05)
        # Post (title) image: fade in, hold, fade out
        post_img_path = f"assets/temp/{reddit_id}/png/title.png"
        post_duration = 3  # seconds to display post
        fade_duration = 0.5  # seconds for fade in/out

        # Get background video size
        probe = ffmpeg.probe(f"assets/temp/{reddit_id}/background_noaudio.mp4")
        video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
        bg_w = int(video_stream["width"])
        bg_h = int(video_stream["height"])
        # DEBUG: Overlay solid red color for first 5 seconds, full screen, top-left
        # red_img = ffmpeg.input(f"color=c=red:s={bg_w}x{bg_h}:d=5:r=60", f="lavfi")["v"]
        # background_clip = background_clip.overlay(
        #     red_img,
        #     enable=f"between(t,0,5)",
        #     x="0",
        #     y="0",
        # )
        current_time = 5  # Start comments after post

        # For each comment, render each chunk as text (no card, just text) using drawtext
        from video_creation.screenshot_downloader import split_comment_into_chunks
        # Use a generic system font for debug
        font_size = 48  # Adjust as needed
        font_color = "red"  # DEBUG: Use red for visibility
        comment_y = "(h/2)"  # DEBUG: Center vertically

        for i in range(number_of_clips):
            comment = reddit_obj["comments"][i]
            chunks = split_comment_into_chunks(comment["comment_body"], min_words=1, max_words=3)
            for chunk in chunks:
                # DEBUG: Always show text for 2 seconds, no fade, use Arial system font
                print_substep(f"[DEBUG FONTCONFIG] About to draw comment chunk text: '{chunk}' with ffmpeg.drawtext (line 407)")
                background_clip = ffmpeg.drawtext(
                    background_clip,
                    text=chunk,
                    x="(w-text_w)/2",
                    y=comment_y,
                    fontsize=font_size,
                    fontcolor=font_color,
                    fontfile=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Roboto-Black.ttf')),
                    alpha=1,
                    enable=f"between(t,{current_time},{current_time + 2})"
                )
                print_substep(f"[DEBUG FONTCONFIG] Completed drawing comment chunk text: '{chunk}' with ffmpeg.drawtext (line 417)")
                current_time += 2
    title = re.sub(r"[^\w\s-]", "", reddit_obj["thread_title"])
    idx = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])
    title_thumb = reddit_obj["thread_title"]

    filename = f"{name_normalize(title)[:251]}"
    subreddit = settings.config["reddit"]["thread"]["subreddit"]

    if not exists(f"./results/{subreddit}"):
        print_substep("The 'results' folder could not be found so it was automatically created.")
        os.makedirs(f"./results/{subreddit}")

    if not exists(f"./results/{subreddit}/OnlyTTS") and allowOnlyTTSFolder:
        print_substep("The 'OnlyTTS' folder could not be found so it was automatically created.")
        os.makedirs(f"./results/{subreddit}/OnlyTTS")

    # create a thumbnail for the video
    settingsbackground = settings.config["settings"]["background"]

    if settingsbackground["background_thumbnail"]:
        if not exists(f"./results/{subreddit}/thumbnails"):
            print_substep(
                "The 'results/thumbnails' folder could not be found so it was automatically created."
            )
            os.makedirs(f"./results/{subreddit}/thumbnails")
        # get the first file with the .png extension from assets/backgrounds and use it as a background for the thumbnail
        first_image = next(
            (file for file in os.listdir("assets/backgrounds") if file.endswith(".png")),
            None,
        )
        if first_image is None:
            print_substep("No png files found in assets/backgrounds", "red")

        else:
            font_family = settingsbackground["background_thumbnail_font_family"]
            font_size = settingsbackground["background_thumbnail_font_size"]
            font_color = settingsbackground["background_thumbnail_font_color"]
            thumbnail = Image.open(f"assets/backgrounds/{first_image}")
            width, height = thumbnail.size
            thumbnailSave = create_thumbnail(
                thumbnail,
                font_family,
                font_size,
                font_color,
                width,
                height,
                title_thumb,
            )
            thumbnailSave.save(f"./assets/temp/{reddit_id}/thumbnail.png")
            print_substep(f"Thumbnail - Building Thumbnail in assets/temp/{reddit_id}/thumbnail.png")

    text = f"Background by {background_config['video'][2]}"
    print_substep("[DEBUG FONTCONFIG] About to draw background credit text with ffmpeg.drawtext (line 472)")
    background_clip = ffmpeg.drawtext(
        background_clip,
        text=text,
        x=f"(w-text_w)",
        y=f"(h-text_h)",
        fontsize=5,
        fontcolor="White",
        fontfile=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Roboto-Black.ttf')),
    )
    print_substep("[DEBUG FONTCONFIG] Completed drawing background credit text with ffmpeg.drawtext (line 481)")
    # Overlay the post/title image at the start of the video for 3 seconds
    post_img_path = f"assets/temp/{reddit_id}/png/title.png"
    screenshot_width = int((W * 45) // 100)
    post_img = ffmpeg.input(post_img_path)["v"].filter("scale", screenshot_width, -1)
    # Center the overlay
    background_clip = background_clip.overlay(
        post_img,
        enable="between(t,0,3)",
        x="(main_w-overlay_w)/2",
        y="(main_h-overlay_h)/2"
    )

    print_step("Rendering the video with post/title overlay at start")
    from tqdm import tqdm

    pbar = tqdm(total=100, desc="Progress: ", bar_format="{l_bar}{bar}", unit=" %")

    def on_update_example(progress) -> None:
        status = round(progress * 100, 2)
        old_percentage = pbar.n
        pbar.update(status - old_percentage)

    defaultPath = f"results/{subreddit}"
    with ProgressFfmpeg(length, on_update_example) as progress:
        path = defaultPath + f"/{filename}"
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this.
        try:
            print_substep("[DEBUG FONTCONFIG] About to call ffmpeg.output (line 496)")
            ffmpeg.output(
                background_clip,
                path,
                f="mp4",
                **{
                    "c:v": "h264",
                    "b:v": "20M",
                    "threads": multiprocessing.cpu_count(),
                },
            ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                quiet=True,
                overwrite_output=True,
                capture_stdout=False,
                capture_stderr=False,
            )
            print_substep("[DEBUG FONTCONFIG] Completed ffmpeg.output for background video only (line 515)")
        except ffmpeg.Error as e:
            print(e.stderr.decode("utf8"))
            exit(1)
    old_percentage = pbar.n
    pbar.update(100 - old_percentage)
    if allowOnlyTTSFolder:
        path = defaultPath + f"/OnlyTTS/{filename}"
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this.
        print_step("Rendering the Only TTS Video 🎥")
        with ProgressFfmpeg(length, on_update_example) as progress:
            try:
                ffmpeg.output(
                    background_clip,
                    audio,
                    path,
                    f="mp4",
                    **{
                        "c:v": "h264",
                        "b:v": "20M",
                        "b:a": "192k",
                        "threads": multiprocessing.cpu_count(),
                    },
                ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                    quiet=True,
                    overwrite_output=True,
                    capture_stdout=False,
                    capture_stderr=False,
                )
            except ffmpeg.Error as e:
                print(e.stderr.decode("utf8"))
                exit(1)

        old_percentage = pbar.n
        pbar.update(100 - old_percentage)
    pbar.close()
    save_data(subreddit, filename + ".mp4", title, idx, background_config["video"][2])
    print_step("Removing temporary files 🗑")
    cleanups = cleanup(reddit_id)
    print_substep(f"Removed {cleanups} temporary files 🗑")
    print_step("Done! 🎉 The video is in the results folder 📁")

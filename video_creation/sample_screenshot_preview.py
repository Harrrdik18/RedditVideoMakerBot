import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from screenshot_downloader import create_reddit_style_screenshot

def main():
    width = 700
    height = 180

    # Sample post (title)
    post_title = "What is the most underrated programming language and why?"
    subreddit = "AskProgramming"
    create_reddit_style_screenshot(
        text=post_title,
        output_path="sample_post.png",
        width=width,
        height=height,
        is_title=True,
        subreddit=subreddit,
        comment_data=None
    )

    # Sample comment 1
    comment1 = {
        "comment_body": "I think Lua is incredibly underrated. It's lightweight, embeddable, and has a simple syntax.",
        "comment_author": "codewizard"
    }
    create_reddit_style_screenshot(
        text=comment1["comment_body"],
        output_path="sample_comment1.png",
        width=width,
        height=height,
        is_title=False,
        subreddit=None,
        comment_data=comment1
    )

    # Sample comment 2
    comment2 = {
        "comment_body": "For me, it's Nim. It compiles to C, is fast, and has a Python-like syntax. Great for systems programming.",
        "comment_author": "sysdev"
    }
    create_reddit_style_screenshot(
        text=comment2["comment_body"],
        output_path="sample_comment2.png",
        width=width,
        height=height,
        is_title=False,
        subreddit=None,
        comment_data=comment2
    )

    print("Sample images generated: sample_post.png, sample_comment1.png, sample_comment2.png")

if __name__ == "__main__":
    main()
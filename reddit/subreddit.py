import re

import praw
from praw.models import MoreComments
from prawcore.exceptions import ResponseException

from utils import settings
from utils.ai_methods import sort_by_similarity
from utils.console import print_step, print_substep
from utils.posttextparser import posttextparser
from utils.subreddit import get_subreddit_undone
from utils.videos import check_done
from utils.voice import sanitize_text


def extract_post_id_from_url(url: str) -> str:
    """
    Extract post ID from various Reddit URL formats
    Args:
        url (str): Reddit URL
    Returns:
        str: Post ID or None if not found
    """
    # List of possible URL patterns
    patterns = [
        r'reddit\.com/r/\w+/comments/(\w+)',  # Standard URL
        r'reddit\.com/comments/(\w+)',        # Short URL
        r'redd\.it/(\w+)',                    # Ultra short URL
        r'/(\w+)/?$'                          # Fallback for ID at end of URL
    ]
    
    # Clean the URL first
    url = url.strip().lower()
    if not url:
        return None
        
    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_subreddit_threads(POST_ID: str = None):
    """
    Returns a list of threads from the subreddit.
    Now supports direct URL input.
    """
    print_substep("Logging into Reddit.")
    
    content = {}
    # Initialize similarity_score at the start
    similarity_score = None
    
    # Handle authentication
    if settings.config["reddit"]["creds"]["2fa"]:
        print("\nEnter your two-factor authentication code from your authenticator app.\n")
        code = input("> ")
        print()
        pw = settings.config["reddit"]["creds"]["password"]
        passkey = f"{pw}:{code}"
    else:
        passkey = settings.config["reddit"]["creds"]["password"]
    
    username = settings.config["reddit"]["creds"]["username"]
    if str(username).casefold().startswith("u/"):
        username = username[2:]
    
    try:
        reddit = praw.Reddit(
            client_id=settings.config["reddit"]["creds"]["client_id"],
            client_secret=settings.config["reddit"]["creds"]["client_secret"],
            user_agent="Accessing Reddit threads",
            username=username,
            passkey=passkey,
            check_for_async=False,
        )
    except ResponseException as e:
        if e.response.status_code == 401:
            print("Invalid credentials - please check them in config.toml")
            raise e
    except Exception as e:
        print("Something went wrong with Reddit authentication...")
        raise e

    # Check if POST_ID is actually a URL
    if POST_ID and ('reddit.com' in POST_ID.lower() or 'redd.it' in POST_ID.lower()):
        extracted_id = extract_post_id_from_url(POST_ID)
        if extracted_id:
            POST_ID = extracted_id
            print_substep(f"Extracted post ID from URL: {POST_ID}")
    
    # Get the submission
    if POST_ID:  # Direct post ID or URL provided
        submission = reddit.submission(id=POST_ID)
        subreddit = submission.subreddit
    elif settings.config["reddit"]["thread"]["post_id"]:  # Post ID from config
        if 'reddit.com' in settings.config["reddit"]["thread"]["post_id"].lower() or 'redd.it' in settings.config["reddit"]["thread"]["post_id"].lower():
            # Config contains URL instead of ID
            extracted_id = extract_post_id_from_url(settings.config["reddit"]["thread"]["post_id"])
            if extracted_id:
                submission = reddit.submission(id=extracted_id)
            else:
                raise ValueError("Invalid Reddit URL in config")
        else:
            submission = reddit.submission(id=settings.config["reddit"]["thread"]["post_id"])
        subreddit = submission.subreddit
    else:  # No specific post, get from subreddit
        if not settings.config["reddit"]["thread"]["subreddit"]:
            try:
                subreddit_input = input("What subreddit would you like to pull from? ")
                subreddit = reddit.subreddit(re.sub(r"r\/", "", subreddit_input))
            except ValueError:
                subreddit = reddit.subreddit("askreddit")
                print_substep("Subreddit not defined. Using AskReddit.")
        else:
            sub = settings.config["reddit"]["thread"]["subreddit"]
            print_substep(f"Using subreddit: r/{sub} from TOML config")
            subreddit_choice = sub
            if str(subreddit_choice).casefold().startswith("r/"):
                subreddit_choice = subreddit_choice[2:]
            subreddit = reddit.subreddit(subreddit_choice)
            
        # Get submission from subreddit
        if settings.config["ai"]["ai_similarity_enabled"]:
            threads = subreddit.hot(limit=50)
            keywords = settings.config["ai"]["ai_similarity_keywords"].split(",")
            keywords = [keyword.strip() for keyword in keywords]
            keywords_print = ", ".join(keywords)
            print(f"Sorting threads by similarity to the given keywords: {keywords_print}")
            threads, similarity_scores = sort_by_similarity(threads, keywords)
            submission, similarity_score = get_subreddit_undone(threads, subreddit, similarity_scores=similarity_scores)
        else:
            threads = subreddit.hot(limit=25)
            submission = get_subreddit_undone(threads, subreddit)

    if submission is None:
        return get_subreddit_threads(POST_ID)

    elif not submission.num_comments and settings.config["settings"]["storymode"] == "false":
        print_substep("No comments found. Skipping.")
        exit()

    submission = check_done(submission)  # double-checking

    upvotes = submission.score
    ratio = submission.upvote_ratio * 100
    num_comments = submission.num_comments
    threadurl = f"https://new.reddit.com/{submission.permalink}"

    print_substep(f"Video will be: {submission.title} :thumbsup:", style="bold green")
    print_substep(f"Thread url is: {threadurl} :thumbsup:", style="bold green")
    print_substep(f"Thread has {upvotes} upvotes", style="bold blue")
    print_substep(f"Thread has a upvote ratio of {ratio}%", style="bold blue")
    print_substep(f"Thread has {num_comments} comments", style="bold blue")
    if similarity_score:
        print_substep(
            f"Thread has a similarity score up to {round(similarity_score * 100)}%",
            style="bold blue",
        )

    content["thread_url"] = threadurl
    content["thread_title"] = submission.title
    content["thread_id"] = submission.id
    content["is_nsfw"] = submission.over_18
    content["comments"] = []
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"] == 1:
            content["thread_post"] = posttextparser(submission.selftext)
        else:
            content["thread_post"] = submission.selftext
    else:
        for top_level_comment in submission.comments:
            if isinstance(top_level_comment, MoreComments):
                continue

            if top_level_comment.body in ["[removed]", "[deleted]"]:
                continue  # # see https://github.com/JasonLovesDoggo/RedditVideoMakerBot/issues/78
            if not top_level_comment.stickied:
                sanitised = sanitize_text(top_level_comment.body)
                if not sanitised or sanitised == " ":
                    continue
                if len(top_level_comment.body) <= int(
                    settings.config["reddit"]["thread"]["max_comment_length"]
                ):
                    if len(top_level_comment.body) >= int(
                        settings.config["reddit"]["thread"]["min_comment_length"]
                    ):
                        if (
                            top_level_comment.author is not None
                            and sanitize_text(top_level_comment.body) is not None
                        ):  # if errors occur with this change to if not.
                            content["comments"].append(
                                {
                                    "comment_body": top_level_comment.body,
                                    "comment_url": top_level_comment.permalink,
                                    "comment_id": top_level_comment.id,
                                }
                            )

    print_substep("Received subreddit threads Successfully.", style="bold green")
    return content

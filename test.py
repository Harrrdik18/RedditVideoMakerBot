from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

def test_fancy_thumbnail():
    try:
        # Create a new image with white background
        post_size = (600, 150)
        post_image = Image.new('RGBA', post_size, (255, 255, 255, 255))
        
        # Reddit post area size
        reddit_post_width = 600
        reddit_post_height = 150
        reddit_post = Image.new('RGBA', (reddit_post_width, reddit_post_height), (255, 255, 255, 255))
        
        # Open and resize workplace image
        workplace_image = Image.open("assets/workplace.jpg")
        icon_size = (32, 32)
        workplace_image = workplace_image.resize(icon_size)
        
        # Create circular mask
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)
        
        # Draw on Reddit post area
        draw = ImageDraw.Draw(reddit_post)
        
        # Load fonts
        font_small = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 16)
        font_title = ImageFont.truetype(os.path.join("fonts", "Roboto-Medium.ttf"), 20)
        font_body = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 14)
        
        # Colors
        text_gray = (26, 26, 27)
        secondary_gray = (129, 131, 132)
        
        # Header section
        icon_position = (16, 16)
        reddit_post.paste(circular_icon, icon_position, circular_icon)
        
        # Subreddit and metadata
        draw.text((56, 19), "r/IndianWorkplace", font=font_small, fill=text_gray)

        
        # Sample title text
        text = "This is a test post title that will be wrapped across multiple lines to show how it looks in the thumbnail"
        
        # Title with word wrap
        title_x = 16
        title_y = 70
        words = text.split()
        lines = []
        current_line = []
        max_width = reddit_post_width - 32

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
        
        # Add interaction elements
        interaction_y = title_y + (len(lines) * 25) + 50
        draw.text((20, interaction_y), "↑", font=font_small, fill=secondary_gray)
        draw.text((40, interaction_y), "1.2k", font=font_small, fill=secondary_gray)
        draw.text((80, interaction_y), "↓", font=font_small, fill=secondary_gray)
        draw.text((140, interaction_y), "💬 234", font=font_small, fill=secondary_gray)
        
        # Center Reddit post in larger image
        paste_x = (post_size[0] - reddit_post_width) // 2
        paste_y = (post_size[1] - reddit_post_height) // 2
        
        # Paste Reddit post onto larger image
        post_image.paste(reddit_post, (paste_x, paste_y))
        
        # Save the result
        post_image.save("test_thumbnail.png")
        print("Thumbnail created successfully as test_thumbnail.png")
        
    except Exception as e:
        print(f"Error creating thumbnail: {str(e)}")

if __name__ == "__main__":
    test_fancy_thumbnail()
    


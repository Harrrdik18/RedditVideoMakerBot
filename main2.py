from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

def create_reddit_style_post():
    try:
        # Create a new image with dark background (Reddit dark mode)
        post_size = (800, 500)  # Adjusted to fit all content
        post_image = Image.new('RGBA', post_size, (26, 26, 27, 255))  # Reddit dark mode background
        
        # Open and resize workplace image to a circular icon
        workplace_image = Image.open("assets/workplace.jpg")
        icon_size = (32, 32)  # Smaller icon to match Reddit
        workplace_image = workplace_image.resize(icon_size)
        
        # Create a circular mask
        mask = Image.new('L', icon_size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + icon_size, fill=255)
        circular_icon = ImageOps.fit(workplace_image, mask.size, centering=(0.5, 0.5))
        circular_icon.putalpha(mask)
        
        draw = ImageDraw.Draw(post_image)
        
        # Load fonts
        font_small = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 13)
        font_title = ImageFont.truetype(os.path.join("fonts", "Roboto-Medium.ttf"), 20)
        font_body = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 14)
        
        # Colors
        text_gray = (215, 218, 220)  # Reddit dark mode text color
        secondary_gray = (129, 131, 132)  # Reddit dark mode secondary text
        green_tag = (67, 160, 71)  # Discussion tag color
        
        # Header section
        icon_position = (16, 16)
        post_image.paste(circular_icon, icon_position, circular_icon)
        
        # Subreddit and metadata
        draw.text((56, 16), "r/ahmedabad", font=font_small, fill=text_gray)
        draw.text((150, 16), "• 2 hr. ago", font=font_small, fill=secondary_gray)
        draw.text((56, 32), "dhwanitshah22", font=font_small, fill=secondary_gray)
        
        # Title (with word wrap)
        title = "You have all the money/luxury and achieved everything in the world with infinite years to live you ever wanted, now what next?"
        title_x = 16
        title_y = 70
        
        # Word wrap for title
        words = title.split()
        lines = []
        current_line = []
        max_width = post_size[0] - 32

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
        
        # Discussion tag
        draw.rectangle((16, 140, 90, 160), fill=green_tag)
        draw.text((25, 142), "Discussion", font=font_small, fill=text_gray)
        
        # Post content
        content_y = 180
        content = [
            "Note - this might be an existential shock to some !",
            "",
            "I have an interesting case for all people here, consider that the you have achieved all your goals ? yes , like making xyz cr of money, buying a house, having a family, landing a dream job, getting a partner, buying a car/mansion what not.",
            "",
            "Assume that all your desires are fulfilled, now WHAT NEXT ?",
            "",
            "add on : you have got infinite life span,",
            "",
            "now, ever wondered how would you spend the next eternity with your self ?",
            "",
            "would it be art, drama, dance, music, chess, math, science, writing, poetry ? what would it be ?"
        ]
        
        for line in content:
            draw.text((16, content_y), line, font=font_body, fill=text_gray)
            content_y += 25 if line else 15
        
        # Save the result
        post_image.save("reddit_style_post.png")
        print("Reddit-style post thumbnail saved as reddit_style_post.png")
        
    except Exception as e:
        print(f"Error creating thumbnail: {str(e)}")

if __name__ == "__main__":
    create_reddit_style_post()
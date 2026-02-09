from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# Configuration
OUTPUT_PATH = "static/img/logo.png"
WIDTH = 500
HEIGHT = 120
BG_COLOR = (0, 0, 0, 0) # Transparent

# MCOT Colors
ORANGE = (242, 101, 34)
PURPLE = (46, 26, 105)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)

def create_logo():
    # Create Canvas
    img = Image.new('RGBA', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Draw Icon (Stylized Abstract Eye / Globe)
    # Center of Icon: (60, 60)
    # Radius: 40
    
    # Outer Orange Arc
    draw.arc([20, 20, 100, 100], start=140, end=400, fill=ORANGE, width=6)
    
    # Inner Purple Arc (Interlocking)
    draw.arc([35, 35, 85, 85], start=-40, end=220, fill=PURPLE, width=6)
    
    # Central "Lens" Dot
    draw.ellipse([50, 50, 70, 70], fill=ORANGE)
    
    # 2. Draw Text "MCOT"
    # Try to use a system font, fallback to default
    try:
        # MacOS typical path
        font_main = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", 48)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    except:
        try:
             # Linux/Docker fallback
             font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
             font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
             # Default fallback
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()

    # Draw "MCOT"
    draw.text((120, 25), "MCOT", font=font_main, fill=WHITE)
    
    # Draw "RENTAL" underneath
    # Calculate width of MCOT to align RENTAL
    draw.text((122, 75), "RENTAL SERVICE", font=font_sub, fill=ORANGE, spacing=10)

    # 3. Add Glow/Shadow (Simulated by drawing translucent underneath? Pillow filter better)
    # For simplicity, we just save the clean sharp logo. The CSS `drop-shadow` handles the glow better.

    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    img.save(OUTPUT_PATH, "PNG")
    print(f"Logo generated at {OUTPUT_PATH}")

if __name__ == "__main__":
    create_logo()

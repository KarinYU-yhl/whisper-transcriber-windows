import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

def create_gradient(width, height, start_color, end_color):
    base = Image.new('RGBA', (width, height), start_color)
    top = Image.new('RGBA', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def create_icon_image(size=1024):
    # Colors (MLX-like style: Dark Blue/Purple)
    start_color = (30, 30, 60, 255)
    end_color = (70, 130, 180, 255) # SteelBlue
    
    # Create background
    img = create_gradient(size, size, start_color, end_color)
    draw = ImageDraw.Draw(img)
    
    # Draw a rounded rectangle border (optional, macOS adds its own usually, but let's make it fill the square mostly)
    # Actually, for macOS icons, we usually provide the full square and the OS masks it, 
    # but providing a pre-rounded shape looks better if we want a specific shape.
    # Let's just fill the canvas for now, or maybe a circle.
    
    # Let's draw a stylized "W" or Waveform
    # Draw a simple waveform representation
    center_y = size // 2
    width = size
    
    # Waveform bars
    bar_color = (255, 255, 255, 230)
    num_bars = 9
    bar_width = size // 15
    spacing = size // 20
    
    total_width = (num_bars * bar_width) + ((num_bars - 1) * spacing)
    start_x = (size - total_width) // 2
    
    import math
    for i in range(num_bars):
        # Create a wave pattern
        x = i / (num_bars - 1) * 2 * math.pi # 0 to 2pi
        height_factor = 0.3 + 0.5 * abs(math.sin(x)) # 0.3 to 0.8
        
        bar_height = int(size * height_factor * 0.6)
        x_pos = start_x + i * (bar_width + spacing)
        y_pos = center_y - bar_height // 2
        
        draw.rounded_rectangle(
            [x_pos, y_pos, x_pos + bar_width, y_pos + bar_height],
            radius=bar_width//2,
            fill=bar_color
        )

    return img

def generate_icns():
    # 1. Create master image
    print("Generating master icon...")
    img = create_icon_image(1024)
    img.save("icon_master.png")
    
    # 2. Create iconset folder
    iconset_dir = "AppIcon.iconset"
    if not os.path.exists(iconset_dir):
        os.makedirs(iconset_dir)
        
    # 3. Generate sizes
    sizes = [16, 32, 128, 256, 512]
    
    for s in sizes:
        # Normal
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(os.path.join(iconset_dir, f"icon_{s}x{s}.png"))
        
        # Retina (@2x)
        s2 = s * 2
        resized_2x = img.resize((s2, s2), Image.Resampling.LANCZOS)
        resized_2x.save(os.path.join(iconset_dir, f"icon_{s}x{s}@2x.png"))
        
    # 4. Convert to icns using iconutil
    print("Converting to .icns...")
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", "app_icon.icns"], check=True)
        print("Successfully created app_icon.icns")
    except subprocess.CalledProcessError as e:
        print(f"Error creating icns: {e}")
    except FileNotFoundError:
        print("Error: 'iconutil' not found. Are you on macOS?")

    # Cleanup (optional)
    # import shutil
    # shutil.rmtree(iconset_dir)
    # os.remove("icon_master.png")

if __name__ == "__main__":
    generate_icns()

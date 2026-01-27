from PIL import Image
import os

# Path to the artifact (source of truth)
# I need to find the specific file. 
# It was icon_closing_store_check_1769543917446.png
# But I will look in D:\Project A\assets\images\icon_closing_3d.png to be sure of what is serving.

target = r"D:\Project A\assets\images\icon_closing_3d.png"

try:
    img = Image.open(target)
    corners = [
        (0, 0),
        (img.width - 1, 0),
        (0, img.height - 1),
        (img.width - 1, img.height - 1)
    ]
    
    print(f"Checking {target}")
    for x, y in corners:
        pixel = img.getpixel((x, y))
        print(f"Pixel at ({x}, {y}): {pixel}")

except Exception as e:
    print(f"Error: {e}")

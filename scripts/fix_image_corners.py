from PIL import Image
import os
import glob

# Threshold for "dark" pixel (0-255). 
# If a pixel is darker than this in all channels, it's considered part of the black corner.
# The corners were (2,2,0), (4,5,7). So strict threshold like 20 is safe.
THRESHOLD = 40 

def is_dark(pixel):
    # Handle RGBA and RGB
    if len(pixel) == 4:
        r, g, b, a = pixel
    else:
        r, g, b = pixel
    return r < THRESHOLD and g < THRESHOLD and b < THRESHOLD

def flood_fill_corner(img, start_x, start_y):
    width, height = img.size
    pixels = img.load()
    
    # Queue for BFS
    queue = [(start_x, start_y)]
    visited = set([(start_x, start_y)])
    
    # Check start pixel first
    if not is_dark(pixels[start_x, start_y]):
        return # Corner is already bright, not a black corner artifact

    while queue:
        x, y = queue.pop(0)
        
        # turn white
        if len(pixels[x, y]) == 4:
             pixels[x, y] = (255, 255, 255, 255)
        else:
             pixels[x, y] = (255, 255, 255)
        
        # Check neighbors
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited:
                    if is_dark(pixels[nx, ny]):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

def process_file(filepath):
    print(f"Processing {filepath}...")
    try:
        img = Image.open(filepath).convert("RGBA")
        w, h = img.size
        
        # Seed from 4 corners
        flood_fill_corner(img, 0, 0)
        flood_fill_corner(img, w-1, 0)
        flood_fill_corner(img, 0, h-1)
        flood_fill_corner(img, w-1, h-1)
        
        # Convert back to RGB if mostly opaque or keep RGBA?
        # User wants White background. RGB is safer to force white.
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3]) # Paste using alpha channel if any
        
        # Actually our flood fill made pixels "White" in RGB/RGBA.
        # But if the original image was RGB, the flood fill logic works.
        # If it was transparent, 'is_dark' might fail on transparent pixels (0,0,0,0) which look black in RGB values but have 0 alpha.
        # But the generated images are likely RGB with black corners.
        
        bg.save(filepath)
        print(f"Fixed {filepath}")
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    target_dir = r"D:\Project A\assets\images"
    patterns = ["icon_*_3d.png"] 
    
    for pattern in patterns:
        files = glob.glob(os.path.join(target_dir, pattern))
        for f in files:
            process_file(f)

if __name__ == "__main__":
    main()

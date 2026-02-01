from PIL import Image
import os

source = r"C:\Users\adjay\.gemini\antigravity\brain\261b092b-32a6-4d9f-8083-a05934441dee\uploaded_media_1769545807026.png"
dest = r"d:\Project A\assets\images\logo.png"

try:
    img = Image.open(source)
    # Convert to RGBA to handle transparency if present, to correctly find bbox
    img = img.convert("RGBA")
    
    # Get bounding box of non-zero alpha pixels OR non-white pixels?
    # User image looks like white background?
    # If it's a white background, bbox on alpha might not work if alpha is 255 everywhere.
    # Let's try to find bbox of "difference from white".
    
    bg = Image.new(img.mode, img.size, (255, 255, 255))
    diff = Image.frombytes(img.mode, img.size, bytes([0]*len(img.tobytes()))) 
    # Actually simpler: compare pixel values.
    # PIL ImageOps.invert might help if we have white bg.
    
    # Simple approach: Turn white (255,255,255) to transparent, then getbbox.
    datas = img.getdata()
    newData = []
    for item in datas:
        # If pixel is white (or very close), make it transparent
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    
    img.putdata(newData)
    
    bbox = img.getbbox()
    if bbox:
        cropped = img.crop(bbox)
        # Check aspect ratio. If too tall, maybe we should crop more?
        # But auto-crop to content is usually what is desired.
        cropped.save(dest)
        print(f"Cropped and saved to {dest}. New size: {cropped.size}")
    else:
        # If empty (all white), just copy
        img.save(dest)
        print("Image was empty or all white? Saved as is.")
        
except Exception as e:
    print(f"Error processing logo: {e}")

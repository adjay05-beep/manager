import os
import glob

# Try to find and delete the 'nul' file
# 'nul' is reserved, so it might be tricky.
# Using \\.\ prefix to bypass reserved name check if it's a file on disk
try:
    if os.path.exists("nul"):
         os.remove("nul")
         print("Deleted standard nul")
    
    # Try absolute path with namespace prefix
    abs_path = os.path.abspath("nul")
    unc_path = r"\\?\{}".format(abs_path)
    if os.path.exists(unc_path):
        os.remove(unc_path)
        print(f"Deleted {unc_path}")
    else:
        print("Could not find file via UNC path")
        
except Exception as e:
    print(f"Error: {e}")

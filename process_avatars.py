
import os
from PIL import Image


def process_image():
    # Batch configuration: (Source Image, Output Directory)
    # Order based on user request: Savaşçı (0), Korucu (1), Keşiş (2)
    batch_jobs = [
        (
            "C:/Users/leven/.gemini/antigravity/brain/9e56ee5c-d0ca-45f3-b2d9-5dc9fe55953c/uploaded_image_0_1765483945863.jpg",
            "assets/characters/warrior_female"
        ),
        (
            "C:/Users/leven/.gemini/antigravity/brain/9e56ee5c-d0ca-45f3-b2d9-5dc9fe55953c/uploaded_image_1_1765483945863.jpg",
            "assets/characters/ranger_female"
        ),
        (
            "C:/Users/leven/.gemini/antigravity/brain/9e56ee5c-d0ca-45f3-b2d9-5dc9fe55953c/uploaded_image_2_1765483945863.jpg",
            "assets/characters/monk_female"
        )
    ]

    for source_path, output_dir in batch_jobs:
        print(f"Processing {source_path} -> {output_dir}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            img = Image.open(source_path)
            img = img.convert("RGBA")
            
            width, height = img.size
            
            # Grid dimensions based on user desc (15 images) -> likely 5 cols x 3 rows
            cols = 5
            rows = 3
            
            tile_width = width // cols
            tile_height = height // rows
            
            count = 1
            
            for r in range(rows):
                for c in range(cols):
                    if count > 15:
                        break
                        
                    left = c * tile_width
                    upper = r * tile_height
                    right = left + tile_width
                    lower = upper + tile_height
                    
                    # Crop
                    tile = img.crop((left, upper, right, lower))
                    
                    # Remove background (Simple White Threadhold)
                    datas = tile.getdata()
                    new_data = []
                    for item in datas:
                        # Check for white-ish background
                        # R, G, B > 240
                        if item[0] > 240 and item[1] > 240 and item[2] > 240:
                             new_data.append((255, 255, 255, 0)) # Transparent
                        else:
                             new_data.append(item)
                    
                    tile.putdata(new_data)
                    
                    # Save
                    save_path = os.path.join(output_dir, f"level_{count}.png")
                    tile.save(save_path, "PNG")
                    print(f"Saved: {save_path}")
                    
                    count += 1
                    
        except Exception as e:
            print(f"Error processing {source_path}: {e}")


if __name__ == "__main__":
    process_image()

import numpy as np
import cv2

def detect_change(image_bytes):
    # Dummy logic (replace with UNet/YOLO later)
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid or unsupported image file.")

    height, width, _ = img.shape
    regions = []

    # Split into 4 regions
    for i in range(2):
        for j in range(2):
            region = img[i*height//2:(i+1)*height//2, j*width//2:(j+1)*width//2]
            damage_score = np.random.randint(0, 100)

            regions.append({
                "zone": f"Zone-{i}{j}",
                "damage": damage_score
            })

    return regions
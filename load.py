from flask import Flask, render_template_string, request
import requests
import base64
import numpy as np
import cv2
import os
import time
import glob
from skimage.metrics import structural_similarity as ssim

app = Flask(__name__)

if not os.path.exists('images'):
    os.makedirs('images')

original_image_base64 = None
original_image_np = None
current_angle = 0

def is_duplicate(img_new_np, folder="images", threshold=0.97):
    img_new = cv2.cvtColor(img_new_np, cv2.COLOR_BGR2GRAY)
    img_new = cv2.resize(img_new, (256, 256))
    for file in glob.glob(os.path.join(folder, "*.png")):
        img = cv2.imread(file, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, (256, 256))
        score = ssim(img_new, img)
        if score > threshold:
            print(f"[SKIP] Captcha mirip dengan {file} (score={score:.4f})")
            return True
    return False

def fetch_and_decode_unique_image(max_attempts=10):
    global original_image_base64, original_image_np, current_angle
    attempt = 0
    while attempt < max_attempts:
        url = "https://x.skymavis.com/captcha-srv/check"
        payload = {
            "app_key": "c7306be6-6e3d-4a3a-9fbe-ec1ca58a31c9",
            "context": "ronin-faucet"
        }
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json"
        }
        res = requests.post(url, json=payload, headers=headers)
        original_image_base64 = res.json()["image"]
        img_bytes = base64.b64decode(original_image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if not is_duplicate(img_np):
            original_image_np = img_np
            current_angle = 0
            print(f"[OK] Gambar unik ditemukan pada percobaan ke-{attempt+1}")
            return
        attempt += 1
    # Jika tetap duplikat, pakai yang terakhir
    original_image_np = img_np
    current_angle = 0
    print("[WARNING] Tidak menemukan gambar unik setelah 10 percobaan, pakai gambar terakhir.")

def rotate_image_from_original(angle):
    if original_image_np is not None:
        h, w = original_image_np.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(original_image_np, M, (w, h))
        return rotated
    return None

def get_current_preview():
    if original_image_np is not None:
        rotated = rotate_image_from_original(current_angle)
        _, buffer = cv2.imencode('.png', rotated)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    return ""

@app.route("/", methods=["GET", "POST"])
def index():
    global current_angle
    action = request.form.get("action")

    if action == "next" or original_image_np is None:
        fetch_and_decode_unique_image()
    elif action == "rotate_left":
        current_angle = (current_angle - 30) % 360
    elif action == "rotate_right":
        current_angle = (current_angle + 30) % 360
    elif action == "save":
        rotated = rotate_image_from_original(current_angle)
        filename = f"images/upright_{int(time.time())}.png"
        cv2.imwrite(filename, rotated)
        return f"<h2>Saved as {filename}</h2><a href='/'>Back</a>"

    preview = get_current_preview()
    html = f"""
    <html>
    <head><title>Axie Upright Collector</title></head>
    <body style="font-family:sans-serif;">
        <h2>Preview Gambar Captcha (Rotasi: {current_angle}°)</h2>
        <form method="post">
            <img src="{preview}" style="max-width:350px; border:2px solid #333;"/><br><br>
            <button name="action" value="rotate_left">⟲ Rotate -30°</button>
            <button name="action" value="rotate_right">⟳ Rotate +30°</button>
            <button name="action" value="next">Next Captcha</button>
            <button name="action" value="save">Save Upright</button>
        </form>
        <p>
            <small>
                Setelah gambar upright, klik <b>Save Upright</b> untuk menyimpan ke folder <code>/images</code>.<br>
                Captcha yang mirip koleksi lama akan otomatis di-skip saat Next Captcha.<br>
                (Jika gambar terus sama, kemungkinan model Axie dari server memang duplikat.)
            </small>
        </p>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == "__main__":
    app.run(debug=True)

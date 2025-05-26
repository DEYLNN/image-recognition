import os
import requests
import base64
import numpy as np
import cv2
import glob
from skimage.metrics import structural_similarity as ssim
import time
import random

upright_folder = "images"
os.makedirs(upright_folder, exist_ok=True)
target_wallet = "addrs evm"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

def make_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://faucet.roninchain.com",
        "referer": "https://faucet.roninchain.com/",
        "sec-ch-ua": '"Chromium";v="124", "Not.A/Brand";v="8"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": random.choice(USER_AGENTS)
    }

def fetch_captcha(session):
    url = "https://x.skymavis.com/captcha-srv/check"
    payload = {
        "app_key": "c7306be6-6e3d-4a3a-9fbe-ec1ca58a31c9",
        "context": "ronin-faucet"
    }
    headers = make_headers()
    res = session.post(url, json=payload, headers=headers, timeout=15)
    data = res.json()
    captcha_id = data["id"]
    img_base64 = data["image"]
    img_bytes = base64.b64decode(img_base64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    captcha_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return captcha_id, captcha_img

def predict_upright_angle(captcha_img, upright_folder="images"):
    captcha_gray = cv2.cvtColor(captcha_img, cv2.COLOR_BGR2GRAY)
    h, w = captcha_gray.shape
    upright_files = glob.glob(f"{upright_folder}/*.png")
    best_score = -1
    best_angle = 0
    best_ref = None

    for angle in range(0, 360, 30):
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        rotated = cv2.warpAffine(captcha_gray, M, (w, h))
        for upright_path in upright_files:
            upright = cv2.imread(upright_path)
            upright_gray = cv2.cvtColor(upright, cv2.COLOR_BGR2GRAY)
            upright_gray_resized = cv2.resize(upright_gray, (w, h))
            score = ssim(upright_gray_resized, rotated)
            if score > best_score:
                best_score = score
                best_angle = angle
                best_ref = upright_path

    return best_angle, best_score, best_ref

def submit_captcha(session, captcha_id, angle):
    url = "https://x.skymavis.com/captcha-srv/submit"
    payload = {
        "app_key": "c7306be6-6e3d-4a3a-9fbe-ec1ca58a31c9",
        "id": captcha_id,
        "result": angle
    }
    headers = make_headers()
    res = session.post(url, json=payload, headers=headers, timeout=15)
    return res.json()

def claim_faucet(session, token, captcha_id, wallet):
    url = f"https://faucet-api.roninchain.com/faucet/weth/{wallet}"
    payload = {
        "token": token,
        "id": captcha_id
    }
    headers = make_headers()
    res = session.post(url, json=payload, headers=headers, timeout=15)
    return res.json()

if __name__ == "__main__":
    session = requests.Session()
    print(f"\nMulai claim 5x tanpa proxy:")
    for i in range(5):
        print(f"\n=== Iterasi ke-{i+1} / 5 ===")
        try:
            captcha_id, captcha_img = fetch_captcha(session)
            print(f"[{i+1}] Captcha diambil (ID: {captcha_id})")

            angle, score, ref = predict_upright_angle(captcha_img)
            print(f"[{i+1}] Prediksi captcha harus diputar: {angle} derajat (score: {score:.4f}) Ref: {ref}")

            submit_response = submit_captcha(session, captcha_id, angle)
            print(f"[{i+1}] Response submit:\n{submit_response}")

            token = submit_response.get("token")
            faucet_id = submit_response.get("result", {}).get("id")

            if token and faucet_id:
                claim_response = claim_faucet(session, token, faucet_id, target_wallet)
                print(f"[{i+1}] Response claim faucet:\n{claim_response}")
            else:
                print(f"[{i+1}] [!] Gagal dapat token atau ID untuk claim faucet.")
        except Exception as e:
            print(f"[{i+1}] [ERROR] {e}")
        delay = random.uniform(10, 15)
        print(f"Delay {delay:.2f} detik sebelum lanjut...")
        time.sleep(delay)
    print(f"===== Selesai 5x claim faucet tanpa proxy =====\n")

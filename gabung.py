import asyncio
from playwright.async_api import async_playwright
import base64
import numpy as np
import cv2
import glob
from skimage.metrics import structural_similarity as ssim
import requests
import random
import os

captcha_folder = "captha"
upright_folder = "images"
os.makedirs(captcha_folder, exist_ok=True)

# Wallet kamu (target faucet)
target_wallet = "0xa094583651BC23451d4fb26971c972629a8ddc05"

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

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Tempat simpan response
        captcha_response = {}

        async def on_response(response):
            url = response.url
            if "/captcha-srv/check" in url and response.request.method == "POST":
                try:
                    data = await response.json()
                    captcha_response['id'] = data.get('id')
                    captcha_response['image'] = data.get('image')
                    print(f"[PLAYWRIGHT] Captcha ID: {captcha_response['id']}")
                except Exception as e:
                    print("Gagal ambil response:", e)

        page.on("response", on_response)

        # 1. Buka web & trigger captcha
        await page.goto('https://faucet.roninchain.com/')
        await page.wait_for_timeout(2000)
        # Trigger permintaan captcha (bisa diubah sesuai kebutuhan webnya)
        # Biasanya captcha muncul setelah isi address dan klik/aksi lain
        random_address = "0xa094583651BC23451d4fb26971c972629a8ddc05"
        await page.fill('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/div[1]/div[2]/input', random_address)
        await page.wait_for_timeout(1000)
        await page.click('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/div[3]/span/div')
        await page.wait_for_timeout(1000)
        await page.click('xpath=//*[@id="radix-:r1:"]/div/ul/li[5]')
        await page.wait_for_timeout(1000)
        await page.click('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/button')
        await page.wait_for_timeout(2000)

        # Tunggu response captcha muncul (max 10 detik)
        for _ in range(20):
            if 'image' in captcha_response:
                break
            await asyncio.sleep(0.5)

        if 'image' not in captcha_response:
            print("Captcha tidak berhasil diambil dari browser!")
            await browser.close()
            return

        # 2. Proses gambar captcha dari response Playwright
        captcha_id = captcha_response['id']
        img_base64 = captcha_response['image']
        img_bytes = base64.b64decode(img_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        captcha_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        filename = f"{captcha_folder}/captcha_{captcha_id}.png"
        cv2.imwrite(filename, captcha_img)
        print(f"Captcha disimpan di: {filename}")

        angle, score, ref = predict_upright_angle(captcha_img)
        print(f"Prediksi captcha harus diputar: {angle} derajat (score: {score:.4f}) Ref: {ref}")

        # 3. Submit captcha via requests (atau bisa pakai page.evaluate untuk submit via browser)
        submit_url = "https://x.skymavis.com/captcha-srv/submit"
        payload = {
            "app_key": "c7306be6-6e3d-4a3a-9fbe-ec1ca58a31c9",
            "id": captcha_id,
            "result": angle
        }
        # Gunakan headers yang sesuai agar fingerprint mirip browser
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://faucet.roninchain.com",
            "referer": "https://faucet.roninchain.com/",
            "user-agent": await page.evaluate("() => navigator.userAgent")
        }
        res = requests.post(submit_url, json=payload, headers=headers)
        submit_response = res.json()
        print("Response submit:", submit_response)

        token = submit_response.get("token")
        faucet_id = submit_response.get("result", {}).get("id")

        if token and faucet_id:
            claim_url = f"https://faucet-api.roninchain.com/faucet/ron/{target_wallet}"
            payload_claim = {
                "token": token,
                "id": faucet_id
            }
            res2 = requests.post(claim_url, json=payload_claim, headers=headers)
            print("Claim faucet response:", res2.json())
        else:
            print("Gagal dapat token atau ID untuk claim faucet.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def on_request(request):
            resource_type = request.resource_type
            url = request.url
            if (resource_type == 'xhr' or resource_type == 'fetch') and 'check' in url:
                print('🔄 [XHR CHECK]', request.method, url)
                # Ambil hanya POST payload
                if request.method == "POST":
                    post_data = request.post_data
                    print('📤 POST DATA:', post_data)

        page.on("request", on_request)

        await page.goto('https://faucet.roninchain.com/')
        random_address = "0x45f5a18731b082AA2730105dDAC1b07c8ef81630"
        await page.wait_for_timeout(5000)
        await page.fill('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/div[1]/div[2]/input', random_address)
        await page.wait_for_timeout(3000)
        await page.click('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/div[3]/span/div')
        await page.wait_for_timeout(1000)
        await page.click('xpath=//*[@id="radix-:r1:"]/div/ul/li[5]')
        await page.wait_for_timeout(1000)
        await page.click('xpath=//*[@id="__next"]/div[2]/div[2]/div[2]/div[3]/form/button')
        await page.wait_for_timeout(2000)

        await page.screenshot(path=f'example-chromium.png')
        await browser.close()

asyncio.run(main())


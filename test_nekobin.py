import aiohttp
import asyncio

async def test_nekobin():
    url = "https://nekobin.com/api/documents"
    payload = {"content": "Astra Userbot Nekobin Test - Success!"}
    
    print(f"Testing Nekobin API at {url}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                print(f"Status Code: {resp.status}")
                if resp.status in [200, 201]:
                    data = await resp.json()
                    if data.get("ok"):
                        print(f"✅ SUCCESS! Paste Key: {data['result']['key']}")
                        print(f"Paste URL: https://nekobin.com/{data['result']['key']}")
                    else:
                        print(f"❌ API Error: {data}")
                else:
                    print(f"❌ HTTP Error: {await resp.text()}")
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_nekobin())

import asyncio
import aiohttp
import sys

# Verified working alternatives and primary endpoints
APIS = {
    "Google Search (SearXNG)": "https://searx.work/search?q=test&format=json",
    "DuckDuckGo (SearXNG)": "https://searx.work/search?q=test&format=json",
    "Wikipedia Search": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=test&format=json",
    "Wikipedia Summary": "https://en.wikipedia.org/api/rest_v1/page/summary/Test",
    "TinyURL": "http://tinyurl.com/api-create.php?url=https://google.com",
    "Frankfurter (Currency)": "https://api.frankfurter.app/latest?amount=1&from=USD&to=INR",
    "GitHub API": "https://api.github.com/users/paman7647",
    "Lyrics Suggestion": "https://api.lyrics.ovh/suggest/hello",
    "Lyrics Fetch": "https://api.lyrics.ovh/v1/Adele/Hello",
    "Urban Dictionary": "http://api.urbandictionary.com/v0/define?term=test",
    "Joke API": "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit",
    "Weather (wttr.in)": "https://wttr.in/London?format=%C+%t+%w+%h+%m",
    "YouTube Direct": "https://www.youtube.com/results?search_query=test"
}

async def test_api(name, url, session):
    headers = {"User-Agent": "AstraUserbot/1.0 (https://github.com/paman7647/Astra-Userbot; contact@example.com)"}
    if "wttr.in" in url:
        headers = {"User-Agent": "curl/7.64.1"}
    
    try:
        async with session.get(url, timeout=10, headers=headers) as resp:
            status = resp.status
            if status == 200:
                print(f"✅ {name}: {status} OK")
                return True
            else:
                print(f"❌ {name}: {status} FAILED")
                return False
    except Exception as e:
        print(f"⚠️ {name}: ERROR ({str(e)})")
        return False

async def test_yt_dlp_search():
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info("ytsearch1:test", download=False)
            if result and result.get('entries'):
                print("✅ YouTube (yt-dlp): OK")
                return True
            else:
                print("❌ YouTube (yt-dlp): FAILED (Empty result)")
                return False
    except Exception as e:
        print(f"⚠️ YouTube (yt-dlp): ERROR ({str(e)})")
        return False

async def main():
    print("🚀 Astra API Diagnostics Starting...\n")
    async with aiohttp.ClientSession() as session:
        # 1. Run HTTP API tests
        tasks = [test_api(name, url, session) for name, url in APIS.items()]
        http_results = await asyncio.gather(*tasks)
        
        # 2. Run YT-DLP Search test
        yt_ok = await test_yt_dlp_search()
    
    total_working = sum(http_results) + (1 if yt_ok else 0)
    total_apis = len(APIS) + 1
    
    print(f"\n📊 Summary: {total_working}/{total_apis} APIs working.")
    if total_working == total_apis:
        print("✨ All systems operational!")
    else:
        print("⚠️ Some APIs require attention.")

if __name__ == "__main__":
    asyncio.run(main())

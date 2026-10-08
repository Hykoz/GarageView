import httpx
import asyncio

async def run_tests():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        print("Testing Login...")
        res = await client.post("/auth/login", json={"username": "baptiste", "password": "ChangeMoi123!_Securise"})
        print("Login Status:", res.status_code)
        cookies = res.cookies
        
        print("Testing Trigger...")
        res = await client.post("/action/trigger", cookies=cookies)
        print("Trigger Status:", res.status_code)
        
        print("Testing State...")
        res = await client.get("/state", cookies=cookies)
        print("State:", res.json())
        
        print("Testing Stream (checking headers)...")
        async with client.stream("GET", "/stream", cookies=cookies) as response:
            print("Stream Status:", response.status_code)
            print("Stream Headers:", response.headers.get("content-type"))

if __name__ == "__main__":
    asyncio.run(run_tests())

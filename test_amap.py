
import asyncio
from amap_server import geocode, poi_search, poi_around, route, route_by_address

async def main():
    print(await poi_around("116.397,39.918", "酒店", radius=1000))
    print("---")
    print(await route("116.322,39.895", "116.397,39.918", mode="driving"))
    print("---")
    print(await route_by_address("北京西站", "故宫博物院", mode="driving", city="北京"))

asyncio.run(main())


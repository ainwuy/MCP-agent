"""
高德地图 MCP Server
提供地理编码、路径规划、POI 搜索等能力，供 LangGraph Agent 调用。
"""
import os
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import logging

load_dotenv()

# ⚠️ stdio 模式下 stdout 是协议通道，日志必须走 stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("amap")

mcp = FastMCP("AmapServer")

API_KEY = os.getenv("AMAP_API_KEY", "")
BASE_URL = "https://restapi.amap.com/v3"


async def _get(path: str, params: dict) -> dict:
    """统一的 GET 请求封装，出错时返回带 error 的字典而不是抛异常。"""
    if not API_KEY:
        return {"error": "未配置 AMAP_API_KEY，请检查 .env"}
    params = {**params, "key": API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}{path}", params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"请求高德失败 {path}: {e}")
        return {"error": f"请求失败: {e}"}


@mcp.tool()
async def geocode(address: str, city: str = "") -> str:
    """
    将中文地址转换为经纬度坐标。

    适用于：需要知道某个地点的精确位置，或作为路线规划的入参。
    注意：高德坐标格式为「经度,纬度」(lng,lat)，与常见的纬度在前不同。

    :param address: 结构化地址，如「北京西站」「故宫博物院」
    :param city: 可选，限定查询城市，如「北京」，能显著提高准确度
    :return: 该地址的经纬度坐标
    """
    data = await _get("/geocode/geo", {"address": address, "city": city})

    if "error" in data:
        return f"⚠️ {data['error']}"
    if data.get("status") != "1" or not data.get("geocodes"):
        return f"⚠️ 未找到「{address}」的坐标：{data.get('info', '未知错误')}"

    loc = data["geocodes"][0]["location"]
    return f"📍 {address} 的坐标是：{loc}（格式 经度,纬度）"

@mcp.tool()
async def poi_search(keyword: str, city: str = "", types: str = "") -> str:
    """
    按关键词搜索地点（POI），返回名称、地址、坐标、电话等信息。

    适用于：用户想找某类地点，如「北京有哪些五星级酒店」「故宫附近有什么好吃的」
    「上海迪士尼在哪」。支持景点、酒店、餐厅、商场、车站等各种类型。

    注意：
    - 这只是信息查询，不能预订。若用户要求"订…"，明确说明你无法下单。
    - 返回的坐标格式为「经度,纬度」(lng,lat)。

    :param keyword: 搜索关键词，如「酒店」「海底捞」「故宫博物院」
    :param city: 限定城市，强烈建议传入，能大幅提高准确度，如「北京」
    :param types: 可选，POI 分类码，如「100000」=住宿服务、「050000」=餐饮服务
    :return: 命中的地点列表（名称 / 地址 / 坐标 / 电话）
    """
    data = await _get("/place/text", {
        "keywords": keyword,
        "city": city,
        "types": types,
        "offset": 10,      # 返回条数
        "page": 1,
        "extensions": "all",
    })

    if "error" in data:
        return f"⚠️ {data['error']}"
    if data.get("status") != "1":
        return f"⚠️ 搜索「{keyword}」失败：{data.get('info', '未知错误')}"

    pois = data.get("pois", [])
    if not pois:
        return f"🔍 没有找到与「{keyword}」相关的地点，试试换个关键词或指定城市。"

    # ↓↓↓ 这部分你自己写：把 pois 列表格式化成人话 ↓↓↓
    lines = [f"🔍 找到 {len(pois)} 个与「{keyword}」相关的地点："]
    for i, poi in enumerate(pois, 1):
        name = poi.get("name", "未知")
        addr = poi.get("address", "（无地址）")
        loc = poi.get("location", "")
        # 提示：poi["address"] 有时是 list，有时是 str，需要处理
        lines.append(f"{i}. {name}\n   地址：{addr}\n   坐标：{loc}")
    return "\n".join(lines)

@mcp.tool()
async def poi_around(location: str, keyword: str = "", radius: int = 1000, types: str = "") -> str:
    """
    搜索某个坐标点周边的地点（POI）。

    适用于：「故宫附近有什么酒店」「这附近 500 米内有餐厅吗」「中关村周边哪有地铁站」。
    注意：location 必须是「经度,纬度」格式的坐标。如果用户给的是地名
    （如"故宫附近"），你要先调用 geocode 工具把地名转成坐标，再调用本工具。

    :param location: 中心点坐标，格式「经度,纬度」，如「116.397,39.918」
    :param keyword: 可选，进一步筛选关键词，如「酒店」「火锅」
    :param radius: 搜索半径，单位米，默认 1000，最大 50000
    :param types: 可选，POI 分类码
    :return: 周边地点列表
    """
    data = await _get("/place/around", {
        "location": location,
        "keywords": keyword,
        "radius": radius,
        "types": types,
        "offset": 10,
        "page": 1,
        "extensions": "all",
    })

    if "error" in data:
        return f"⚠️ {data['error']}"
    if data.get("status") != "1":
        return f"⚠️ 周边搜索失败：{data.get('info', '未知错误')}"

    pois = data.get("pois", [])
    if not pois:
        return f"🔍 {location} 周边 {radius} 米内没找到相关地点。"

    lines = [f"🔍 {location} 周边 {radius} 米内找到 {len(pois)} 个地点："]
    for i, poi in enumerate(pois, 1):
        name = poi.get("name", "未知")
        addr = poi.get("address", "（无地址）")
        addr = addr[0] if isinstance(addr, list) else addr  # ⚠️ 高德返回有时是 list
        loc = poi.get("location", "")
        distance = poi.get("distance", "")  # 周边搜索会返回距离
        line = f"{i}. {name}\n   地址：{addr}\n   坐标：{loc}"
        if distance:
            line += f"\n   距离：{distance} 米"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
async def route(origin: str, destination: str, mode: str = "driving", city: str = "") -> str:
    """
    路径规划：计算两点之间的路线、距离和耗时。

    适用于：「从北京西站到故宫怎么走」「颐和园到天坛坐地铁要多久」。
    重要：origin 和 destination 必须是「经度,纬度」坐标。如果用户给的是地名，
    你必须先调用 geocode 把地名转成坐标，然后再调用本工具。

    :param origin: 起点坐标，格式「经度,纬度」，如「116.322,39.895」
    :param destination: 终点坐标，格式「经度,纬度」
    :param mode: 交通方式，可选 driving(驾车) / walking(步行) / transit(公交地铁) / bicycling(骑行)
    :param city: 公交模式(city=transit)下建议传入城市名，如「北京」
    :return: 路线方案（距离、时长、具体走法）
    """
    # 端点映射
    endpoints = {
        "driving": "/direction/driving",
        "walking": "/direction/walking",
        "bicycling": "/direction/bicycling",
        "transit": "/direction/transit/integrated",
    }
    if mode not in endpoints:
        return f"⚠️ 不支持的交通方式「{mode}」，可选：driving/walking/transit/bicycling"

    params = {"origin": origin, "destination": destination}
    if mode == "transit":
        params["city"] = city

    data = await _get(endpoints[mode], params)

    if "error" in data:
        return f"⚠️ {data['error']}"
    if data.get("status") != "1":
        return f"⚠️ 路径规划失败：{data.get('info', '未知错误')}"

    if mode in ("driving", "walking", "bicycling"):
        path = data.get("route", {}).get("paths", [{}])[0]
        distance = int(path.get("distance", 0))  # 米
        duration = int(path.get("duration", 0))  # 秒
        distance_km = round(distance / 1000, 2)
        duration_min = round(duration / 60, 1)
        mode_zh = {"driving": "驾车", "walking": "步行", "bicycling": "骑行"}[mode]
        return (
            f"🛣 {mode_zh}路线\n"
            f"   总距离：约 {distance_km} 公里\n"
            f"   预计用时：约 {duration_min} 分钟"
        )

    elif mode == "transit":
        transits = data.get("route", {}).get("transits", [])
        if not transits:
            return "⚠️ 暂无公交方案，建议试试驾车或步行。"
        best = transits[0]
        duration_min = round(int(best.get("duration", 0)) / 60, 1)
        walk_m = int(best.get("walking_distance", 0))
        lines = [
            f"🚌 推荐公交方案\n   预计用时：约 {duration_min} 分钟   步行：约 {walk_m} 米\n   路线：",
        ]
        for seg in best.get("segments", []):
            busline = seg.get("busline", {})
            if busline and busline.get("name"):
                lines.append(f"     · {busline['name']}")
            elif seg.get("railway", {}).get("name"):
                lines.append(f"     · {seg['railway']['name']}")
        return "\n".join(lines)

@mcp.tool()
async def route_by_address(origin_name: str, destination_name: str,
                          mode: str = "driving", city: str = "") -> str:
    """
    一步到位：输入起点和终点的地名，直接返回路线方案。
    内部自动完成「地名→坐标→路径规划」，无需手动转换。

    适用于：用户直接说地名时优先用这个，比分别调用 geocode + route 更快更准。

    :param origin_name: 起点地名，如「北京西站」
    :param destination_name: 终点地名，如「故宫博物院」
    :param mode: driving/walking/transit/bicycling
    :param city: 城市名，如「北京」，能大幅提高地名解析准确度
    :return: 路线方案
    """
    # 1) 两个地名分别 geocode


    loc1_resp = await _get("/geocode/geo", {"address": origin_name, "city": city})
    loc2_resp = await _get("/geocode/geo", {"address": destination_name, "city": city})

    if loc1_resp.get("status") != "1" or not loc1_resp.get("geocodes"):
        return f"⚠️ 找不到「{origin_name}」的坐标"
    if loc2_resp.get("status") != "1" or not loc2_resp.get("geocodes"):
        return f"⚠️ 找不到「{destination_name}」的坐标"

    origin = loc1_resp["geocodes"][0]["location"]
    destination = loc2_resp["geocodes"][0]["location"]

    # 2) 再调 route（注意：必须直接传坐标，不能 await route()，因为那是 MCP 工具，循环依赖）

    endpoints = {
        "driving": "/direction/driving",
        "walking": "/direction/walking",
        "bicycling": "/direction/bicycling",
        "transit": "/direction/transit/integrated",
    }
    if mode not in endpoints:
        return f"⚠️ 不支持的交通方式「{mode}」"

    params = {"origin": origin, "destination": destination}
    if mode == "transit":
        params["city"] = city

    route_data = await _get(endpoints[mode], params)
    if route_data.get("status") != "1":
        return f"⚠️ 路径规划失败：{route_data.get('info', '未知错误')}"

    # 3) 格式化（可以从 route 函数里复制一段，这里简化版）
    if mode in ("driving", "walking", "bicycling"):
        path = route_data.get("route", {}).get("paths", [{}])[0]
        km = round(int(path.get("distance", 0)) / 1000, 2)
        minutes = round(int(path.get("duration", 0)) / 60, 1)
        mode_zh = {"driving": "驾车", "walking": "步行", "bicycling": "骑行"}[mode]
        return (
            f"🚩 从「{origin_name}」到「{destination_name}」\n"
            f"   {mode_zh}：约 {km} 公里 / {minutes} 分钟\n"
            f"   起点坐标：{origin}\n"
            f"   终点坐标：{destination}"
        )
    elif mode == "transit":
        transits = route_data.get("route", {}).get("transits", [])
        if transits:
            best = transits[0]
            return (
                f"🚩 从「{origin_name}」到「{destination_name}」\n"
                f"   公交：约 {round(int(best.get('duration', 0)) / 60, 1)} 分钟\n"
                f"   起点：{origin}\n   终点：{destination}"
            )
        return f"⚠️ 这两个地点之间暂无直达公交方案"


if __name__ == '__main__':
    mcp.run(transport="stdio")

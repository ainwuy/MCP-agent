"""
天气 MCP Server
---------------------------------
数据源：高德开放平台天气 API
  https://restapi.amap.com/v3/weather/weatherInfo

相比原 OpenWeather 方案的优势：
1. 支持**中文城市名**（「北京」而不是「Beijing」），无需 LLM 做中英翻译
2. 免费额度 30 万次/天（OpenWeather 免费版仅 60 次/分钟、100 万次/月）
3. 提供 temperature_float / humidity_float 精确字段
4. 支持未来 3-4 天预报（extensions=all），对出行规划场景很有价值
"""

import os
import logging

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 加载环境变量
load_dotenv()

# ⚠️ stdio 模式下 stdout 是协议通道，日志必须走 stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather")

# 初始化 MCP 服务器
mcp = FastMCP("WeatherServer")

# 高德天气 API 配置
AMAP_WEATHER_BASE = "https://restapi.amap.com/v3/weather/weatherInfo"
API_KEY = os.getenv("AMAP_API_KEY", "")

# 星期数字 → 中文
WEEK_MAP = {"1": "周一", "2": "周二", "3": "周三", "4": "周四",
            "5": "周五", "6": "周六", "7": "周日"}


async def _get_weather(city: str, extensions: str = "base") -> dict:
    """
    调用高德天气 API，出错时返回带 error 的字典而不是抛异常。

    :param city: 城市名（支持中文，如「北京」）或城市编码(adcode)
    :param extensions: base=实况天气 / all=预报天气
    :return: 天气数据字典；若出错返回包含 error 信息的字典
    """
    if not API_KEY:
        return {"error": "未配置 AMAP_API_KEY，请检查 .env"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                AMAP_WEATHER_BASE,
                params={"key": API_KEY, "city": city, "extensions": extensions},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"请求高德天气失败 {city}/{extensions}: {e}")
        return {"error": f"请求失败: {e}"}


@mcp.tool()
async def query_weather(city: str) -> str:
    """
    查询指定城市的实时天气（当前温度、天气状况、湿度、风力风向）。

    适用于：出行前查看目的地当前天气，或回答「XX今天天气怎么样」
    「北京热不热」。**支持中文城市名**，如「北京」「上海」「广州」；
    也支持城市编码(adcode)。

    :param city: 城市名称，支持中文，如「北京」
    :return: 该城市当前的实况天气
    """
    data = await _get_weather(city, extensions="base")

    if "error" in data:
        return f"⚠️ {data['error']}"
    # 注意：城市不存在时高德仍返回 status=1 / info=OK，只是 lives 为空数组，
    # 所以必须拆成两个判断，否则会显示"失败：OK"这种莫名其妙的提示。
    if data.get("status") != "1":
        return f"⚠️ 查询「{city}」天气失败：{data.get('info', '未知错误')}"
    if not data.get("lives"):
        return f"⚠️ 查不到「{city}」的天气数据，请确认城市名是否正确（支持中文城市名或 adcode）"

    live = data["lives"][0]
    # 优先用 float 字段（更精确），没有则回退到整数字符串
    temp = live.get("temperature_float") or live.get("temperature", "?")
    humidity = live.get("humidity_float") or live.get("humidity", "?")

    return (
        f"🌍 {live.get('province', '')}{live.get('city', city)}\n"
        f"🌤 天气：{live.get('weather', '未知')}\n"
        f"🌡 温度：{temp}°C\n"
        f"💧 湿度：{humidity}%\n"
        f"🌬 风向：{live.get('winddirection', '未知')}风   风力：{live.get('windpower', '未知')}级\n"
        f"🕐 更新：{live.get('reporttime', '未知')}"
    )


@mcp.tool()
async def query_weather_forecast(city: str) -> str:
    """
    查询指定城市未来几天的天气预报（白天/夜间天气、最高/最低温、风力）。

    适用于：规划未来行程时查看天气趋势，如「明天去故宫玩天气怎么样」
    「这周末北京天气如何」「下周上海会下雨吗」。**支持中文城市名**。

    :param city: 城市名称，支持中文，如「北京」
    :return: 未来 3-4 天的天气预报（白天 / 夜间分开）
    """
    data = await _get_weather(city, extensions="all")

    if "error" in data:
        return f"⚠️ {data['error']}"
    if data.get("status") != "1":
        return f"⚠️ 查询「{city}」预报失败：{data.get('info', '未知错误')}"
    if not data.get("forecasts"):
        return f"⚠️ 查不到「{city}」的预报数据，请确认城市名是否正确（支持中文城市名或 adcode）"

    forecast = data["forecasts"][0]
    casts = forecast.get("casts", [])
    if not casts:
        return f"⚠️ 「{city}」暂无预报数据"

    lines = [f"📅 {forecast.get('city', city)} 未来 {len(casts)} 天预报：\n"]
    for c in casts:
        week = WEEK_MAP.get(str(c.get("week", "")), "")
        day_t = c.get("daytemp_float") or c.get("daytemp", "?")
        night_t = c.get("nighttemp_float") or c.get("nighttemp", "?")
        lines.append(
            f"📆 {c.get('date', '?')} {week}\n"
            f"   白天 {c.get('dayweather', '?')}｜{day_t}°C｜{c.get('daywind', '')}风 {c.get('daypower', '')}级\n"
            f"   夜间 {c.get('nightweather', '?')}｜{night_t}°C｜{c.get('nightwind', '')}风 {c.get('nightpower', '')}级\n"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_weather_tips(season: str) -> str:
    """
    获取指定季节的天气贴士。
    这是演示同一个 MCP Server 可以包含多个 Tool 的例子。
    :param season: 季节名称 (spring, summer, autumn, winter)
    """
    tips = {
        "spring": "🌸 春季多风，注意防风保暖，预防花粉过敏。",
        "summer": "☀️ 夏季炎热，注意防暑降温，多喝水。",
        "autumn": "🍁 秋季干燥，注意补水润肺，早晚温差大。",
        "winter": "❄️ 冬季寒冷，注意防寒保暖，预防感冒。"
    }
    return tips.get(season.lower(), "❓ 未知季节，请注意身体健康。")


if __name__ == "__main__":
    # 以标准 I/O 方式运行 MCP 服务器
    mcp.run(transport="stdio")

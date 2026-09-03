"""
DashScope 模型名诊断脚本（针对 mcp_agent 项目）
------------------------------------------------
用途：用项目里实际的 ChatTongyi 通道，逐个测试候选模型名，
      找出当前 API Key 下真正可用的那个，避免"猜名字"踩坑。

背景：写错模型名时 DashScope 不一定报 "model not exist"，
      而是报极具迷惑性的 400 / InvalidParameter / "url error, please check url"，
      看着像网络问题，实际是模型名非法。

运行（在项目根目录、用项目的 venv）：
    .venv\\Scripts\\python.exe check_models.py
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Windows 控制台编码兜底
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

# 加载本项目的 .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)  # override=True：确保 .env 优先于系统环境变量

API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
CURRENT_MODEL = os.getenv("MODEL", "")

# ChatTongyi 从环境变量读 key，必须显式塞进去
os.environ["DASHSCOPE_API_KEY"] = API_KEY

# ---------- 待测试的 LLM 候选（按 DashScope 官方命名规律排列）----------
LLM_CANDIDATES = [
    # .env 当前值，先验证它是不是罪魁祸首
    "qwen3.8-max",
    # 老一代稳定款（记忆中实测可用）
    "qwen-plus",
    "qwen-turbo",
    "qwen-max",
    # qwen3 系列
    "qwen3-max",
    "qwen3-plus",
    "qwen3-turbo",
    # 带日期快照款（记忆中实测可用）
    "qwen3.7-plus-2026-05-26",
    # 长文本
    "qwen-long",
]


def classify_error(msg: str) -> str:
    """把报错归类成人话"""
    low = msg.lower()
    if "url error" in low or "please check url" in low:
        return "模型名非法（伪装成 url error）"
    if "model not exist" in low or "model_not_exist" in low:
        return "模型不存在"
    if "invalidapikey" in low.replace("_", "").replace(" ", ""):
        return "API Key 无效"
    if "quota" in low or "allocationquota" in low or "freetier" in low:
        return "额度不足/耗尽"
    if "arrearage" in low or "overdue" in low:
        return "账号欠费"
    if "throttle" in low or "rate limit" in low:
        return "触发限流"
    return "其他: " + msg[:100]


def test_llm(model_name: str) -> tuple:
    """用 ChatTongyi 测单个模型，返回 (是否可用, 说明)"""
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage

        llm = ChatTongyi(model=model_name, streaming=False)
        resp = llm.invoke([HumanMessage(content="只回复两个字：你好")])
        content = (resp.content or "").strip()[:30]
        return True, f"可用，回复：{content}"
    except Exception as e:
        return False, classify_error(str(e).replace("\n", " "))


def main():
    print("=" * 66)
    print("DashScope 模型名诊断  (通道：ChatTongyi / langchain_community)")
    print("=" * 66)

    if not API_KEY:
        print("\n[X] .env 中未检测到 DASHSCOPE_API_KEY，请先填写")
        return

    print(f"\nAPI Key : {API_KEY[:10]}...{API_KEY[-6:]}  (中间已隐藏)")
    print(f"当前 MODEL: {CURRENT_MODEL or '(未设置)'}")

    print("\n" + "-" * 66)
    print(f"{'结果':<6}{'模型名':<28}{'说明'}")
    print("-" * 66)

    ok_models = []
    for m in LLM_CANDIDATES:
        ok, detail = test_llm(m)
        flag = "[OK]" if ok else "[XX]"
        mark = " <== 当前 .env 值" if m == CURRENT_MODEL else ""
        print(f"{flag:<6}{m:<28}{detail}{mark}")
        if ok:
            ok_models.append(m)

    print("\n" + "=" * 66)
    print("结论")
    print("=" * 66)
    if ok_models:
        print(f"\n可用模型（按推荐顺序）：{', '.join(ok_models)}")
        print(f"\n请把 .env 改成：")
        print(f"    MODEL={ok_models[0]}")
        if CURRENT_MODEL and CURRENT_MODEL not in ok_models:
            print(f"\n[!] 你当前的 MODEL={CURRENT_MODEL} 不可用，这就是 400 报错的原因。")
    else:
        print("\n[X] 没有任何模型可用。请去控制台确认 key 状态与额度：")
        print("    https://bailian.console.aliyun.com/")
    print("=" * 66)


if __name__ == "__main__":
    main()

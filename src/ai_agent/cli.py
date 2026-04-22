from __future__ import annotations

import argparse
from pathlib import Path

from .agent import AIAgent
from .config import AgentConfig


WELCOME = """
Aurora Agent (Offline)
输入 `help` 查看指令，输入 `exit` 退出。
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Aurora Agent locally (no external API required).")
    parser.add_argument("--db", default="./data/agent.db", help="SQLite database path.")
    parser.add_argument("--once", default=None, help="Run one command and exit.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = AgentConfig.from_db_path(Path(args.db))
    agent = AIAgent(config)

    if args.once:
        print(agent.handle_message(args.once))
        return

    print(WELCOME.strip())
    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会话结束。")
            break
        if not user_input:
            continue
        response = agent.handle_message(user_input)
        print(f"Agent> {response}")
        if agent.should_exit:
            break


if __name__ == "__main__":
    main()


import os
from dotenv import load_dotenv
from src.graph import graph

load_dotenv()

def main():
    print("=" * 60)
    print("TravelBuddy - Trợ lý Du lịch Thông minh")
    print("Gõ 'quit' để thoát.")
    print("=" * 60)

    while True:
        user_input = input("\nBạn: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break

        for event in graph.stream({"messages": [("user", user_input)]}):
            for value in event.values():
                msg = value["messages"][-1]
                if msg.content:
                    print(f"\nTravelBuddy: {msg.content}")

if __name__ == "__main__":
    main()
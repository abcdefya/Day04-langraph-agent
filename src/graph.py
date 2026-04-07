import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq  # Thay đổi ở đây
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

from src.state import AgentState
from src.tools.tools import search_flights, search_hotels, calculate_budget
from src.telemetry.metrics import tracker
from src.telemetry.logger import logger

# Load biến môi trường
load_dotenv()

# 1. Khởi tạo danh sách Tools 
tools_list = [search_flights, search_hotels, calculate_budget]

# 2. Khởi tạo LLM dùng Groq
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# Bind tools để LLM có thể thực hiện Function Calling 
llm_with_tools = llm.bind_tools(tools_list)

# ===== LOAD SYSTEM PROMPT (GLOBAL) =====

current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "..", "system_prompt.txt")

try:
    with open(prompt_path, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.error(f"❌ Không tìm thấy file prompt tại: {prompt_path}")
    SYSTEM_PROMPT = "Bạn là trợ lý du lịch TravelBuddy."

def build_model_messages(state: AgentState):
    history = list(state["messages"])

    if history and isinstance(history[0], SystemMessage):
        return history

    return [SystemMessage(content=SYSTEM_PROMPT), *history]


def agent_node(state: AgentState):
    """
    Gọi model với system prompt ổn định ở mỗi step và log telemetry.
    """
    model_messages = build_model_messages(state)

    start_time = time.time()
    response = llm_with_tools.invoke(model_messages)
    latency = int((time.time() - start_time) * 1000)

    if response.tool_calls:
        for tc in response.tool_calls:
            log_data = {
                "tool": tc["name"],
                "arguments": tc["args"],
                "latency_ms": latency,
            }
            logger.info(
                f"🔧 Agent quyết định gọi Tool: {tc['name']} với tham số: {tc['args']}"
            )
            logger.log_event("TOOL_CALL", log_data)
    else:
        # logger.info("💬 Agent trả lời trực tiếp cho người dùng.")
        preview = (response.content[:100] + "...") if response.content else ""
        logger.log_event("DIRECT_RESPONSE", {"content": preview})

    if getattr(response, "usage_metadata", None):
        tracker.track_request(
            provider="groq",
            model="llama-3.3-70b",
            usage=response.usage_metadata,
            latency_ms=latency,
        )

    return {"messages": [response]}

builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools_list))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition) 
builder.add_edge("tools", "agent") 

graph = builder.compile()
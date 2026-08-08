from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from src.agent.config import tools, memory, model
from src.agent.state import State
from src.agent.utils.prompt import CHATBOT_SYSTEM_PROMPT


def build_graph() -> StateGraph:
    graph_bulder = StateGraph(State)

    def chatbot(state: State):
        project_id = state["project_id"]

        message = model.invoke([
            SystemMessage(content=CHATBOT_SYSTEM_PROMPT),
            *state["messages"]
        ])
        return { "messages": [message], "project_id": project_id }

    tool_node = ToolNode(tools)

    graph_bulder.add_node("chatbot", chatbot)
    graph_bulder.add_node("tools", tool_node)

    graph_bulder.add_conditional_edges("chatbot", tools_condition)
    graph_bulder.add_edge("tools", "chatbot")
    graph_bulder.add_edge(START, "chatbot")

    return graph_bulder.compile(checkpointer=memory)

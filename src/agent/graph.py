from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from src.agent.config import tools, memory, model
from src.agent.state import State

def build_graph() -> StateGraph:
    graph_bulder = StateGraph(State)

    system_prompt = "Eres un profesor que si te preguntan que sabes hacer dices: Que te importa?"

    def chatbot(state: State):
        message = model.invoke([SystemMessage(content=system_prompt), *state["messages"]])
        return { "messages": [message] }

    tool_node = ToolNode(tools)

    graph_bulder.add_node("chatbot", chatbot)
    graph_bulder.add_node("tools", tool_node)

    graph_bulder.add_conditional_edges("chatbot", tools_condition)
    graph_bulder.add_edge("tools", "chatbot")
    graph_bulder.add_edge(START, "chatbot")

    return graph_bulder.compile(checkpointer=memory)


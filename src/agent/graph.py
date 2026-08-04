from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from src.agent.config import tools, memory, model
from src.agent.state import State
from src.agent.utils.prompt import CHATBOT_SYSTEM_PROMPT
from src.projects.infrastructure.firestore_repository import FirestoreProjectRepository


class _LazyProjectRepo:
    """Defers constructing FirestoreProjectRepository (which talks to Firebase
    at instantiation time) until it's actually used, so importing this module
    doesn't require live credentials. Still a single module-level object that
    tests can swap out wholesale via `patch("src.agent.graph._project_repo")`.
    """

    def __init__(self) -> None:
        self._instance: FirestoreProjectRepository | None = None

    def _get(self) -> FirestoreProjectRepository:
        if self._instance is None:
            self._instance = FirestoreProjectRepository()
        return self._instance

    def get_or_create_by_thread(self, thread_id: str):
        return self._get().get_or_create_by_thread(thread_id)


_project_repo = _LazyProjectRepo()

def build_graph() -> StateGraph:
    graph_bulder = StateGraph(State)

    def chatbot(state: State):
        project_id = state.get("project_id")
        if not project_id:
            project_id = _project_repo.get_or_create_by_thread(state["thread_id"]).project_id

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

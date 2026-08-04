from src.agent.graph import build_graph
from src.agent.config import graph_config

def stream_grap_updates(user_input: str):
    graph = build_graph()
    thread_id = graph_config["configurable"]["thread_id"]

    user_message = { "role": "user", "content": user_input }
    messages = [user_message]

    graph_stream = graph.stream(
        { "messages": messages, "thread_id": thread_id },
        config=graph_config,
        stream_mode="values"
    )

    for event in graph_stream:
        event["messages"][-1].pretty_print()


## Seguramente como nos vamos a comunicar desde un front, esto no se use, pero lo dejo por si acaso.
def run_chat_loop():
    while True:
        try:
            user_input = input("User: ")
            if (user_input.lower() in ["exit", "quit", "q"]):
                print("Chat ended.")
                break
            stream_grap_updates(user_input)
        except:
            stream_grap_updates(user_input="Tell goodbye!")
            break
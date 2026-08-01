from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


## Annotated es para que el langchain sepa que es un mensaje.
## add_messages funciona como "hook" para que cada vez que haya un nuevo mensaje se agregue al estado (a la lista).
class State(TypedDict):
    messages: Annotated[list, add_messages]
    thread_id: str
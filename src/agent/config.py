from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from src.agent.infrastructure.llm.chat_model_factory import build_chat_model
from src.shared.llm_config.loader import load_llm_config
from src.agent.tools.project_metadata_tool import update_project_metadata_tool
from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool
from src.agent.tools.campaign_builder.approve_campaign_tool import approve_campaign_tool
from src.agent.tools.image_builder.image_builder_tool import image_builder_tool
from src.agent.tools.image_builder.approve_images_tool import approve_images_tool
from src.agent.tools.landing_builder.landing_builder_tool import landing_builder_tool
from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool


load_dotenv()

memory = MemorySaver()

tools = [
    update_project_metadata_tool,
    image_builder_tool,
    approve_images_tool,
    campaign_builder_tool,
    approve_campaign_tool,
    landing_builder_tool,
    promote_landing_tool,
]

config = load_llm_config().for_agent()
model_loaded = build_chat_model(config)

model = model_loaded.bind_tools(tools)


## El thread_id es el id de la conversación. Como es el mismo va a conservar el estado de la conversación.
## Si quisiera una conversacion nueva, tendria que cambiar el thread_id.
graph_config = { "configurable": { "thread_id": "1" } }

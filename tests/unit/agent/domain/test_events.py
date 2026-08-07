from src.agent.domain.events import (
    ChatEvent, start_event, message_event, tool_call_event,
    tool_result_event, done_event, error_event,
)


def test_start_event_carries_thread_id():
    event = start_event("t-1")
    assert isinstance(event, ChatEvent)
    assert event.event == "start"
    assert event.data == {"thread_id": "t-1"}


def test_message_event_carries_content():
    assert message_event("hola").data == {"content": "hola"}


def test_tool_call_event_carries_name_and_args():
    event = tool_call_event("image_builder_tool", {"brief_dict": {"b": 1}})
    assert event.event == "tool_call"
    assert event.data == {"name": "image_builder_tool", "args": {"brief_dict": {"b": 1}}}


def test_tool_result_event_carries_result_payload():
    event = tool_result_event("image_builder_tool", "success", {"creatives": []})
    assert event.event == "tool_result"
    assert event.data == {
        "name": "image_builder_tool",
        "status": "success",
        "result": {"creatives": []},
    }


def test_done_event_allows_null_project_id():
    assert done_event("t-1", None).data == {"thread_id": "t-1", "project_id": None}


def test_error_event_carries_message():
    assert error_event("boom").data == {"message": "boom"}

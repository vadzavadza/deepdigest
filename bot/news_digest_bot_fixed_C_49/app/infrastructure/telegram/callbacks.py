def topic_create() -> str:
    return "topic:create"


def topics_list() -> str:
    return "topics:list"


def topic_view(topic_id: int) -> str:
    return f"topic:{topic_id}:view"


def topic_edit(topic_id: int) -> str:
    return f"topic:{topic_id}:edit"


def topic_delete(topic_id: int) -> str:
    return f"topic:{topic_id}:delete"


def topic_language(topic_id: int, language: str) -> str:
    return f"topic:{topic_id}:lang:{language}"


def topic_mode(topic_id: int, mode: str) -> str:
    return f"topic:{topic_id}:mode:{mode}"


def channels_list() -> str:
    return "channels:list"


def settings_open() -> str:
    return "settings:open"


def help_open() -> str:
    return "help:open"


def channel_select(channel_id: int) -> str:
    return f"channel:{channel_id}:select"



def channel_register_this_chat() -> str:
    return "channels:register:this_chat"


def channel_view(channel_id: int) -> str:
    return f"channel:{channel_id}:view"


def topic_run(topic_id: int) -> str:
    return f"topic:{topic_id}:run"

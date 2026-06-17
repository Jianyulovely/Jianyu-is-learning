from core.tool.base import BaseTool


class AskHuman(BaseTool):
    """Add a tool to ask human for help."""

    name: str = "ask_human"
    description: str = (
        "Ask the Telegram user a concise clarification question when required "
        "information is missing and the task cannot continue safely."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The question you want to ask the human.",
            }
        },
        "required": ["inquire"],
    }

    async def execute(self, inquire: str) -> str:
        return inquire.strip()

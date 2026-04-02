import os
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI


# prob list all models here
class Agent(str, Enum):
    GEMINI_3_1_PRO_PREVIEW = "gemini-3.1-pro-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"

    def initialize(self) -> str:
        match self:
            case Agent.GEMINI_3_1_PRO_PREVIEW:
                if not os.environ.get("GOOGLE_API_KEY"):
                    raise ValueError("GOOGLE_API_KEY environment variable not set")
            case Agent.GEMINI_2_5_PRO:
                if not os.environ.get("GOOGLE_API_KEY"):
                    raise ValueError("GOOGLE_API_KEY environment variable not set")
            case Agent.GEMINI_2_5_FLASH:
                if not os.environ.get("GOOGLE_API_KEY"):
                    raise ValueError("GOOGLE_API_KEY environment variable not set")

        return self.value

    def create_agent(self) -> ChatGoogleGenerativeAI:
        match self:
            case Agent.GEMINI_3_1_PRO_PREVIEW:
                return ChatGoogleGenerativeAI(model=self.value)
            case Agent.GEMINI_2_5_PRO:
                return ChatGoogleGenerativeAI(model=self.value)
            case Agent.GEMINI_2_5_FLASH:
                return ChatGoogleGenerativeAI(model=self.value)

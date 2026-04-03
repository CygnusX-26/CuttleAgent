import os
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


# prob list all models here
class Agent(str, Enum):
    GEMINI_3_1_PRO_PREVIEW = "gemini-3.1-pro-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GPT_5_1 = "gpt-5.1"
    GPT_5_MINI = "gpt-5-mini"

    def initialize(self) -> str:
        match self:
            case (
                Agent.GEMINI_3_1_PRO_PREVIEW
                | Agent.GEMINI_2_5_PRO
                | Agent.GEMINI_2_5_FLASH
            ):
                if not os.environ.get("GOOGLE_API_KEY"):
                    raise ValueError("GOOGLE_API_KEY environment variable not set")
            case Agent.GPT_5_1 | Agent.GPT_5_MINI:
                if not os.environ.get("OPENAI_API_KEY"):
                    raise ValueError("OPENAI_API_KEY environment variable not set")

        return self.value

    def create_agent(self) -> ChatGoogleGenerativeAI | ChatOpenAI:
        match self:
            case (
                Agent.GEMINI_3_1_PRO_PREVIEW
                | Agent.GEMINI_2_5_PRO
                | Agent.GEMINI_2_5_FLASH
            ):
                return ChatGoogleGenerativeAI(model=self.value)
            case Agent.GPT_5_1 | Agent.GPT_5_MINI:
                return ChatOpenAI(model=self.value)

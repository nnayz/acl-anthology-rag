from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    """
    Configuration of the API
    """

    # GROQ
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

    pass

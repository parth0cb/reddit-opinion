from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    query: str

class Credentials(BaseModel):
    api_key: str
    base_url: Optional[str] = "https://api.openai.com/v1"
    model: Optional[str] = "gpt-3.5-turbo"

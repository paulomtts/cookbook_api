from pydantic import BaseModel
from typing import List, Any


class DefaultOutput(BaseModel):
    data: Any
    status: int
    message: str

class DeleteData(BaseModel):
    field: str
    ids: List[int]
from datetime import datetime

from pydantic import BaseModel


class PingResponse(BaseModel):
    status: str
    timestamp: datetime

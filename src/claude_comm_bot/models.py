from pydantic import BaseModel, Field


class NotifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    kind: str | None = Field(
        None,
        description="One of: finished (default), error, crash, info. Changes the message header.",
    )


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=3500)
    options: list[str] | None = Field(
        None,
        description="Optional answer choices rendered as inline-keyboard buttons.",
        max_length=8,
    )
    session_id: str | None = None
    timeout: int | None = Field(
        None,
        description="Override server's default wait timeout in seconds. 0 = wait forever.",
    )


class AskResponse(BaseModel):
    answer: str
    via: str = Field(..., description="'button' or 'text'.")


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    pending_asks: int


class RouteCatalogEntry(BaseModel):
    id: str
    method: str
    path: str
    description: str
    auth: bool

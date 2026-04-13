from datetime import datetime
from pydantic import BaseModel


class ModelRegistryCreate(BaseModel):
    model_name: str
    model_version: str | None = None
    parameter_count: str | None = None
    license: str | None = None
    model_card_url: str | None = None
    context_window_size: int | None = None
    supports_ner: bool = False
    supports_vision: bool = False


class ModelRegistryRead(BaseModel):
    id: int
    model_name: str
    model_version: str | None
    parameter_count: str | None
    license: str | None
    model_card_url: str | None
    is_active: bool
    added_at: datetime
    context_window_size: int | None
    supports_ner: bool
    supports_vision: bool
    model_config = {"from_attributes": True}


class ModelRegistryUpdate(BaseModel):
    model_version: str | None = None
    parameter_count: str | None = None
    license: str | None = None
    model_card_url: str | None = None
    is_active: bool | None = None
    context_window_size: int | None = None
    supports_ner: bool | None = None
    supports_vision: bool | None = None

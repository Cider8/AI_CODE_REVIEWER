"""Small helpers for converting Beanie Documents -> Pydantic response schemas.

Beanie documents expose `.id` (PydanticObjectId) and `model_dump()` already
includes an `"id"` key. Our response schemas define `id` with alias `_id`
and `populate_by_name=True`. To avoid passing both `"id"` and `"_id"` for
the same field (which pydantic v2 rejects), we drop the `"id"` key first.
"""

from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def doc_to_schema(doc, schema: Type[T], **extra) -> T:
    """`extra` supplies fields the schema declares but the document does not
    (e.g. a computed quota). Passing them here keeps those fields required on
    the schema, so forgetting one is a loud validation error rather than a
    silently wrong default."""
    data = doc.model_dump()
    data.pop("id", None)
    data["_id"] = doc.id
    data.update(extra)
    return schema(**data)

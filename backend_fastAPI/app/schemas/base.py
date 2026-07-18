from pydantic import BaseModel, ConfigDict


def to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model that serializes fields as camelCase (matches the
    existing React frontend which expects e.g. `overallScore`,
    `preferredLanguages`, `securityIssues`, etc.)

    Accepts both snake_case and camelCase on input, outputs camelCase.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

import re
from typing import Annotated, ClassVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


def normalize_phone(value):
    if not isinstance(value, str) or not re.fullmatch(r"\+?[0-9() -]+", value.strip()):
        raise ValueError("Use an international phone number")
    digits = re.sub(r"[^0-9]", "", value)
    if not re.fullmatch(r"[1-9][0-9]{7,14}", digits):
        raise ValueError("Phone number must contain 8 to 15 digits including country code")
    return digits


Phone = Annotated[str, BeforeValidator(normalize_phone)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$"
    ),
]
Password = Annotated[str, Field(min_length=12, max_length=128)]
LongText = Annotated[str, Field(max_length=20000)]
PositiveId = Annotated[int, Field(gt=0)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchModel(RequestModel):
    nullable_fields: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in self.model_fields_set - self.nullable_fields:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

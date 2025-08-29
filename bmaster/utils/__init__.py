from typing import Annotated
from pydantic import (
	BaseModel,
	BeforeValidator,
	PlainSerializer,
	ValidationError,
	Field,
	field_validator
)
from datetime import time


# Custom parser: Convert string "HH:MM" to datetime.time
def parse_time_hhmm(value: str | time) -> time:
	if isinstance(value, str):
		try:
			hours, minutes = map(int, value.split(':'))
			return time(hours, minutes)
		except (ValueError, AttributeError) as e:
			raise ValueError(f"Invalid time format: {value}. Use 'HH:MM'") from e
	return value  # If already a time object, pass through

# Custom serializer: Convert datetime.time to "HH:MM" string with leading zeros
def serialize_time_hhmm(t: time) -> str:
	return f"{t.hour:02}:{t.minute:02}"

# Create an annotated type that combines both
TimeHHMM = Annotated[
	time,
	BeforeValidator(parse_time_hhmm),
	PlainSerializer(serialize_time_hhmm, return_type=str),
	# Field(..., pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
]

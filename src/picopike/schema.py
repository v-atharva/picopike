"""Vocabulary shared by the router, the API and the trace."""

from typing import Literal

Decision = Literal["ALLOW", "HOLD", "BLOCK"]
Mode = Literal["fast", "auto"]

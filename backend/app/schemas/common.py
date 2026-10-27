from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Money is stored/validated as Decimal and serialised to JSON as a number (INR values fit float exactly).
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]

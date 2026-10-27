from enum import Enum


class Role(str, Enum):
    user = "user"
    admin = "admin"


class PropertyType(str, Enum):
    apartment = "apartment"
    independent_house = "independent_house"
    villa = "villa"
    plot = "plot"
    commercial = "commercial"


class ListingType(str, Enum):
    buy = "buy"
    rent = "rent"


class Furnishing(str, Enum):
    furnished = "furnished"
    semi_furnished = "semi_furnished"
    unfurnished = "unfurnished"


class PropertyStatus(str, Enum):
    active = "active"
    sold = "sold"
    rented = "rented"
    inactive = "inactive"


class InquiryStatus(str, Enum):
    new = "new"
    contacted = "contacted"
    closed = "closed"


def sql_in(enum_cls: type[Enum]) -> str:
    return ", ".join(f"'{e.value}'" for e in enum_cls)

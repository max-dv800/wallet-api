from enum import StrEnum, auto


class TypeTransaction(StrEnum):
    TRANSFER = auto()
    DEPOSIT = auto()
    WITHDRAWAL = auto()
    EXCHANGE = auto()


class Currency(StrEnum):
    USD = auto()
    EUR = auto()
    RUB = auto()


class Status(StrEnum):
    PENDING = auto()
    COMPLETED = auto()
    FAILED = auto()
    REVERSED = auto()

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PersonType(Enum):
    CUSTOMER = "customer"
    WAITER = "waiter"
    CELEBRITY = "celebrity"


@dataclass
class FaceLocation:
    top: int
    right: int
    bottom: int
    left: int


@dataclass
class FaceAnalysis:
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None

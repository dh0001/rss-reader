from typing import Any, Type, TypeVar
from typeguard import check_type as typeguard_check_type

T = TypeVar('T')

def check_str(item: Any) -> str:
    if isinstance(item, str):
        return item
    raise Exception("")


def check_type(check: Type[T], item: Any) -> T:
    typeguard_check_type(str(check), item, check)
    return item


def check_val(check: Any, val: Any):
    if check == val:
        raise ValueError
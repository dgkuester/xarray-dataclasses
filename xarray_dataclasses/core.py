__all__ = ["dataarrayclass", "is_dataarrayclass", "to_dataarray"]


# standard library
from dataclasses import asdict, dataclass, Field, _DataclassParams
from inspect import signature
from typing import Any, Callable, Dict


# third-party packages
import numpy as np
from typing_extensions import Protocol, TypeAlias


# sub-modules/packages
from .methods import new
from .typing import DataArray, Dims, Dtype
from .utils import copy_wraps


# constants
DEFAULT_CREATOR = new


# type hints
DataArrayCreator: TypeAlias = Callable[..., DataArray]


class DataArrayClass(Protocol):
    """Type hint for DataArray classes."""

    # special attributes of dataclass
    __dataclass_fields__: Dict[str, Field]
    __dataclass_params__: _DataclassParams

    # special attributes of DataArray class
    __dataarray_creator__: DataArrayCreator


# main features
def dataarrayclass(
    dims: Dims = None,
    dtype: Dtype = None,
    creator: Callable = DEFAULT_CREATOR,
) -> Callable[type, DataArrayClass]:
    """Create a decorator to convert a class to a DataArray class.

    Args:
        dims: Dimensions to be fixed in a DataArray instance.
        dtype: Datatype to be fixed in a DataArray instance.
        creator: Function to create an initial DataArray instance.

    Returns:
        A decorator to convert a class to a DataArray class.

    """

    def wrapper(cls: type) -> type:
        dataarray_creator = get_creator(creator, dims, dtype)

        cls.__dataarray_creator__ = staticmethod(dataarray_creator)
        update_annotations(cls, dataarray_creator)
        update_defaults(cls, dataarray_creator)

        return dataclass(cls)

    return wrapper


def is_dataarrayclass(inst: Any) -> bool:
    """Check if an instance is DataArray class."""
    return isinstance(inst, DataArrayClass)


def to_dataarray(inst: DataArrayClass) -> DataArray:
    """Convert a DataArray class instance to a DataArray."""
    dataarray = inst.__dataarray_creator__(**asdict(inst))

    for field in inst.__dataclass_fields__.values():
        if not isinstance(field.type, type):
            continue

        if not issubclass(field.type, DataArray):
            continue

        value = getattr(inst, field.name)
        set_coord(dataarray, field, value)

    return dataarray


# helper features
def get_creator(creator: Callable, dims: Dims, dtype: Dtype) -> DataArrayCreator:
    """Create a DataArray creator with fixed dims and dtype."""
    sig = signature(creator)
    TypedArray = DataArray[dims, dtype]

    for par in sig.parameters.values():
        if par.annotation == par.empty:
            raise ValueError("Type hint must be specified for all args.")

        if par.kind == par.VAR_POSITIONAL:
            raise ValueError("Variadic positional args cannot be used.")

        if par.kind == par.VAR_KEYWORD:
            raise ValueError("Variadic keyword args cannot be used.")

    @copy_wraps(creator)
    def wrapper(*args, **kwargs) -> TypedArray:
        for key in tuple(kwargs.keys()):
            if key not in sig.parameters:
                kwargs.pop(key)

        return TypedArray(creator(*args, **kwargs))

    wrapper.__annotations__["return"] = TypedArray
    return wrapper


def update_annotations(cls: type, based_on: Callable) -> None:
    """Update class annotations based on a DataArray initializer."""
    leading_annotations = {}
    trailing_annotations = {}

    for par in signature(based_on).parameters.values():
        if par.kind == par.KEYWORD_ONLY:
            trailing_annotations[par.name] = par.annotation
        else:
            leading_annotations[par.name] = par.annotation

    cls.__annotations__ = {
        **leading_annotations,
        **cls.__annotations__,
        **trailing_annotations,
    }


def update_defaults(cls: type, based_on: Callable) -> None:
    """Update class defaults based on a DataArray initializer."""
    for par in signature(based_on).parameters.values():
        if not par.default == par.empty:
            setattr(cls, par.name, par.default)


def set_coord(dataarray: DataArray, field: Field, value: Any) -> None:
    """Set a coord to a DataArray based on field information."""
    dims = field.type.dims
    shape = tuple(dataarray.sizes[dim] for dim in dims)
    dataarray.coords[field.name] = dims, field.type(np.full(shape, value))

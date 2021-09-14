__all__ = ["asdataarray", "AsDataArray"]


# standard library
from dataclasses import dataclass, Field
from functools import wraps
from typing import Any, Callable, Dict, overload, Sequence, Type, TypeVar, Union


# third-party packages
import numpy as np
import xarray as xr
from typing_extensions import Literal, ParamSpec, Protocol


# submodules
from .parser import parse
from .utils import copy_class


# type hints
Order = Literal["C", "F"]
Shape = Union[Sequence[int], int]
P = ParamSpec("P")
R = TypeVar("R", bound=xr.DataArray)
DataArrayFactory = Callable[..., R]


class DataClass(Protocol[P]):
    """Type hint for dataclass objects."""

    __init__: Callable[P, None]
    __dataclass_fields__: Dict[str, Field[Any]]


class DataClassWithFactory(Protocol[P, R]):
    """Type hint for dataclass objects."""

    __init__: Callable[P, None]
    __dataclass_fields__: Dict[str, Field[Any]]
    __dataarray_factory__: DataArrayFactory[R]


# runtime functions
@overload
def asdataarray(
    inst: DataClassWithFactory[P, R],
    dataarray_factory: DataArrayFactory[Any] = xr.DataArray,
) -> R:
    ...


@overload
def asdataarray(
    inst: DataClass[P],
    dataarray_factory: DataArrayFactory[R] = xr.DataArray,
) -> R:
    ...


def asdataarray(inst: Any, dataarray_factory: Any = xr.DataArray) -> Any:
    """Convert a DataArray-class instance to DataArray one."""
    try:
        dataarray_factory = inst.__dataarray_factory__
    except AttributeError:
        pass

    return parse(inst).to_dataarray(dataarray_factory=dataarray_factory)


# mix-in class
class AsDataArray:
    """Mix-in class that provides shorthand methods."""

    __dataarray_factory__ = xr.DataArray

    @classmethod
    def new(
        cls: Type[DataClassWithFactory[P, R]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """Create a DataArray instance."""
        raise NotImplementedError

    @classmethod
    def empty(
        cls: Type[DataClassWithFactory[P, R]],
        shape: Shape,
        order: Order = "C",
        **kwargs: Any,
    ) -> R:
        """Create a DataArray instance without initializing data.

        Args:
            shape: Shape of the new DataArray instance.
            order: Whether to store data in row-major (C-style)
                or column-major (Fortran-style) order in memory.
            kwargs: Args of the DataArray class except for data.

        Returns:
            DataArray instance filled without initializing data.

        """
        name = parse(cls).data[0].name
        data = np.empty(shape, order=order)
        return asdataarray(cls(**{name: data}, **kwargs))

    @classmethod
    def zeros(
        cls: Type[DataClassWithFactory[P, R]],
        shape: Shape,
        order: Order = "C",
        **kwargs: Any,
    ) -> R:
        """Create a DataArray instance filled with zeros.

        Args:
            shape: Shape of the new DataArray instance.
            order: Whether to store data in row-major (C-style)
                or column-major (Fortran-style) order in memory.
            kwargs: Args of the DataArray class except for data.

        Returns:
            DataArray instance filled with zeros.

        """
        name = parse(cls).data[0].name
        data = np.zeros(shape, order=order)
        return asdataarray(cls(**{name: data}, **kwargs))

    @classmethod
    def ones(
        cls: Type[DataClassWithFactory[P, R]],
        shape: Shape,
        order: Order = "C",
        **kwargs: Any,
    ) -> R:
        """Create a DataArray instance filled with ones.

        Args:
            shape: Shape of the new DataArray instance.
            order: Whether to store data in row-major (C-style)
                or column-major (Fortran-style) order in memory.
            kwargs: Args of the DataArray class except for data.

        Returns:
            DataArray instance filled with ones.

        """
        name = parse(cls).data[0].name
        data = np.ones(shape, order=order)
        return asdataarray(cls(**{name: data}, **kwargs))

    @classmethod
    def full(
        cls: Type[DataClassWithFactory[P, R]],
        shape: Shape,
        fill_value: Any,
        order: Order = "C",
        **kwargs: Any,
    ) -> R:
        """Create a DataArray instance filled with given value.

        Args:
            shape: Shape of the new DataArray instance.
            fill_value: Value for the new DataArray instance.
            order: Whether to store data in row-major (C-style)
                or column-major (Fortran-style) order in memory.
            kwargs: Args of the DataArray class except for data.

        Returns:
            DataArray instance filled with given value.

        """
        name = parse(cls).data[0].name
        data = np.full(shape, fill_value, order=order)
        return asdataarray(cls(**{name: data}, **kwargs))

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Update new() based on the dataclass definition."""
        super().__init_subclass__(**kwargs)

        # temporary class only for getting dataclass __init__
        try:
            Temp = dataclass(copy_class(cls))
        except RuntimeError:
            return

        init = Temp.__init__
        init.__annotations__["return"] = R

        # create a concrete new method and bind
        @classmethod
        @wraps(init)
        def new(
            cls: Type[DataClassWithFactory[P, R]],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            return asdataarray(cls(*args, **kwargs))

        cls.new = new  # type: ignore

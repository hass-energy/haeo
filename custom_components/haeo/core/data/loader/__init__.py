"""Loader type alias for field type-specific data loading.

Loader instances are created from LoaderMeta markers via compose_field().
Individual loaders are defined in their respective modules and should not be imported directly.
"""

from typing import Any

from .constant_loader import ConstantLoader as ConstantLoader
from .scalar_loader import ScalarLoader as ScalarLoader
from .time_series_loader import TimeSeriesLoader as TimeSeriesLoader

# Union of all concrete loader types
Loader = ConstantLoader[Any] | ScalarLoader | TimeSeriesLoader

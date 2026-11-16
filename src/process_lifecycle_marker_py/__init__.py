"""Process lifecycle marker package.

Exports the public API for emitting startup and shutdown log records
with a boot id and uptime so log queries can bound sessions.
"""

from .core import LifecycleMarker, MarkerRecord

__all__ = ["LifecycleMarker", "MarkerRecord"]

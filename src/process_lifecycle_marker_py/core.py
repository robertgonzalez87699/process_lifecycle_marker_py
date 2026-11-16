"""Core implementation of process lifecycle markers.

A marker emits two log records per process session: one at startup and
one at shutdown. Each record carries a boot id (stable for the life of
the process) and an uptime in seconds measured from the moment the
marker was created. Log queries can therefore bound a session by
the pair of records sharing a boot id.

The clock is injectable so tests are deterministic and never depend on
wall-clock time.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class MarkerRecord:
    """A single lifecycle log record.

    Attributes:
        event: Either ``"startup"`` or ``"shutdown"``.
        boot_id: Identifier shared by every record in one process session.
        uptime: Seconds between marker creation and this record, as a float.
        pid: Operating system process id at the time of the record.
    """

    event: str
    boot_id: str
    uptime: float
    pid: int

    def to_json(self) -> str:
        """Serialise the record to a compact JSON object.

        JSON is used because log pipelines commonly accept structured
        lines and it keeps the record self-describing without a schema.
        """
        return json.dumps(
            {
                "event": self.event,
                "boot_id": self.boot_id,
                "uptime": self.uptime,
                "pid": self.pid,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


@dataclass
class LifecycleMarker:
    """Emits startup and shutdown records for one process session.

    The marker captures a boot id and a monotonic start time when it is
    constructed. Calling :meth:`startup` and :meth:`shutdown` produces
    records with uptimes measured against that start time.

    The clock is a callable returning a float; it defaults to
    :func:`time.monotonic` so uptime is immune to system clock changes.
    Tests pass a fake clock to avoid wall-clock dependence.

    Only one startup and one shutdown record are emitted per marker.
    Calling either method a second time raises :class:`RuntimeError`;
    silently emitting duplicates would make session bounds ambiguous.
    """

    boot_id: str
    clock: Callable[[], float] = time.monotonic
    _start: float = field(init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)
    _stopped: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._start = self.clock()

    def _uptime(self) -> float:
        return self.clock() - self._start

    def _make_record(self, event: str) -> MarkerRecord:
        import os

        return MarkerRecord(
            event=event,
            boot_id=self.boot_id,
            uptime=self._uptime(),
            pid=os.getpid(),
        )

    def startup(self) -> MarkerRecord:
        """Emit the startup record.

        Raises:
            RuntimeError: If startup was already emitted.
        """
        if self._started:
            raise RuntimeError("startup record already emitted")
        self._started = True
        return self._make_record("startup")

    def shutdown(self) -> MarkerRecord:
        """Emit the shutdown record.

        Raises:
            RuntimeError: If startup has not been emitted or shutdown was
                already emitted.
        """
        if not self._started:
            raise RuntimeError("cannot emit shutdown before startup")
        if self._stopped:
            raise RuntimeError("shutdown record already emitted")
        self._stopped = True
        return self._make_record("shutdown")

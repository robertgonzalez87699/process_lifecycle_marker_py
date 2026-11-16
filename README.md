# process_lifecycle_marker_py

Emits startup and shutdown log records with a boot id and uptime so log queries can bound sessions by process boundary markers.

## Usage

```python
from process_lifecycle_marker_py import LifecycleMarker

marker = LifecycleMarker(boot_id="host-7-2024-06-01T12:00:00Z")
startup = marker.startup()
print(startup.to_json())
# {"boot_id":"host-7-2024-06-01T12:00:00Z","event":"startup","pid":1234,"uptime":0.0}

# ... run the process ...

shutdown = marker.shutdown()
print(shutdown.to_json())
# {"boot_id":"host-7-2024-06-01T12:00:00Z","event":"shutdown","pid":1234,"uptime":42.5}
```

## Why this exists

Logs from a long-running process are hard to bound: a query for "everything since the last restart" has no reliable anchor if restarts are only visible as an absence of lines. The marker writes two structured records per session, both carrying the same `boot_id` and an `uptime` measured from the moment the marker was constructed. A query can then select the pair of records with a given `boot_id` and take everything between them.

The trade-off is that the marker does not generate `boot_id` for you. The caller supplies it, because the useful value depends on the surrounding system: a container id, a hostname plus start timestamp, or a UUID minted by the supervisor. Generating one internally would be convenient but would hide the identity that makes the records joinable across log sources.

## Edge cases

Uptime uses `time.monotonic` by default, so it is unaffected by system clock adjustments. If you inject a clock that can go backwards, uptime can be negative; the library reports the raw difference rather than clamping, so a non-monotonic clock is visible in the logs instead of silently hidden.

Only one startup and one shutdown record are emitted per marker. A second call to either method raises `RuntimeError`; duplicate boundary records would make session bounds ambiguous.

## API

- `LifecycleMarker(boot_id, clock=time.monotonic)` — construct with a boot id and an optional zero-argument clock returning a float. Captures the start time immediately.
  - `.startup() -> MarkerRecord` — emit the startup record. Raises `RuntimeError` if already emitted.
  - `.shutdown() -> MarkerRecord` — emit the shutdown record. Raises `RuntimeError` if startup was not emitted or shutdown was already emitted.
- `MarkerRecord` — frozen dataclass with fields `event` (`"startup"` or `"shutdown"`), `boot_id`, `uptime` (float seconds), and `pid` (int).
  - `.to_json() -> str` — compact JSON object with those four keys.

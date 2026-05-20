# Project Hyperion — Pipeline API Specification

Documentation for ingestion gates, schema validation rules,
and telemetry output routing.

---

## Ingestion Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v5/telemetry/submit` | Boundary gateway for low-latency telemetry packets |
| `GET`  | `/api/v5/orchestrator/status` | Real-time lane pool metrics and health snapshot |
| `GET`  | `/api/v5/health` | Lightweight liveness probe (returns 200 or 503) |
| `GET`  | `/metrics` | Prometheus scrape endpoint (port 9090) |

## Packet Schema (JSON Schema draft-07)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema",
  "title": "HyperionTelemetryPacket",
  "type": "object",
  "properties": {
    "packet_id": {
      "type": "string",
      "description": "Unique packet identifier (UUID v4 or synthetic)"
    },
    "lane_hint": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20,
      "description": "Preferred lane for routing (1-20)"
    },
    "payload": {
      "type": "object",
      "description": "Arbitrary telemetry payload (synthetic in test harness)"
    }
  },
  "required": ["packet_id", "lane_hint", "payload"]
}
```

## Rate-Limiting Headers

Every response from `/api/v5/telemetry/submit` includes:

| Header | Description |
|---|---|
| `X-RateLimit-Remaining` | Tokens remaining in the current bucket window |
| `X-RateLimit-Limit` | Maximum burst capacity (token bucket) |
| `X-RateLimit-Reset` | Unix timestamp when the bucket fully refills |

## Compliance

All schemas adhere to strict telemetry data transfer regulations.
Sub-second buffer flushing (250 ms) maintains a low memory footprint
under sustained 20× concurrent load.

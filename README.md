# hass-autoscan

CUDA-accelerated license-plate recognition for CCTV gate control. Watches an
RTSP camera stream, reads vehicle number plates (optimized for
Russian/CIS-format plates), and — when a plate matches an allowed list —
calls a Home Assistant service (e.g. a switch or script) to open a gate.

## How it works

```
RTSP camera → Frame Reader → Nomeroff-Net (YOLOv8 detect + RNN OCR, GPU)
   → Normalizer → Cooldown check → Whitelist Matcher → HA REST API call
                                                       → Event Logger (SQLite + snapshot)
```

Frames are sampled at a low, configurable rate (a few fps by default) — a
vehicle takes several seconds to cross frame, so full camera fps isn't
needed. A plate only opens the gate if it's an **exact** whitelist match
**and** the OCR confidence is above a configurable threshold; a cooldown
window stops one passing car from re-triggering the gate repeatedly.

## Requirements

- A machine with an NVIDIA GPU, drivers, and
  [nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)
  installed (for Docker GPU access).
- Docker + Docker Compose v2.
- An RTSP-capable camera.
- A Home Assistant instance reachable from the container, with:
  - A long-lived access token (Profile → Security → Long-Lived Access Tokens).
  - A `switch` or `script` entity that opens your gate.

## Repo layout

```
app/
  main.py       # orchestrator / CLI entrypoint
  camera.py     # RTSP frame reader with reconnect/backoff
  anpr.py       # Nomeroff-Net wrapper (plate detection + OCR)
  normalize.py  # plate text normalization (Cyrillic/Latin confusables)
  whitelist.py  # exact-match plate whitelist
  cooldown.py   # per-plate repeat-trigger suppression
  ha_client.py  # Home Assistant REST client (retry/backoff)
  eventlog.py   # SQLite event log + JPEG snapshot persistence
  config.py     # config.yaml loading/validation
config/
  config.example.yaml   # copy to config.yaml and fill in your values
tests/                   # pytest unit tests, no GPU required
Dockerfile
docker-compose.prod.yml   # production run (whitelist + HA calls)
docker-compose.debug.yml  # debug run (camera/ANPR only, no HA calls)
```

## Configuration

Copy the example and fill in your values:

```
cp config/config.example.yaml config/config.yaml
```

| Field                   | Required          | Default | Description |
|-------------------------|--------------------|---------|-------------|
| `rtsp_url`               | always             | —       | RTSP stream URL, e.g. `rtsp://user:pass@camera-ip:554/stream1` |
| `ha_url`                 | production mode    | —       | Base URL of your Home Assistant instance |
| `ha_token`                | production mode    | —       | Long-lived access token |
| `ha_domain`               | production mode    | —       | Service domain to call, e.g. `switch` or `script` |
| `ha_service`              | production mode    | —       | Service to call, e.g. `turn_on` |
| `ha_entity_id`             | production mode    | —       | Entity to target, e.g. `switch.gate_relay` |
| `allowed_plates`           | production mode    | `[]`    | List of allowed plate numbers (any Cyrillic/Latin mix is normalized before matching) |
| `cooldown_seconds`         | no                 | `60`    | Suppresses repeat gate triggers for the same plate within this window |
| `confidence_threshold`     | no                 | `0.85`  | Minimum OCR confidence required to consider a plate a match |
| `sample_fps`               | no                 | `3`     | Frames per second pulled from the RTSP stream |
| `dry_run`                  | no                 | `true`  | If true, detects/matches/logs normally but never calls Home Assistant |

`config.yaml` is gitignored — it holds your HA token, don't commit it.

In `--debug` mode (see below), only `rtsp_url` is required; everything else
is optional.

## Quick start

**1. Test the camera + plate recognition first**, before touching Home
Assistant. This mode skips the whitelist/cooldown/HA logic entirely and just
logs every plate it sees:

```bash
docker compose -f docker-compose.debug.yml up --build
```

Watch the logs for lines like:

```
[debug] plate=A123BC777 confidence=0.93
```

and check `data/snapshots/` for the corresponding JPEGs, to confirm the
camera connection and plate recognition are working correctly.

**2. Fill in the rest of `config/config.yaml`** (HA fields, `allowed_plates`)
once step 1 looks right.

**3. Run in `dry_run` mode first** (the default) to validate whitelist
matching without actually opening the gate:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Check `data/events.sqlite3` and `data/snapshots/` for the events you'd
expect — a whitelisted vehicle should show `matched=1` with
`ha_call_result` still `NULL` (skipped because of `dry_run`).

**4. Go live**: set `dry_run: false` in `config/config.yaml` and restart:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

A whitelisted plate should now trigger the configured Home Assistant
service and open the gate.

## Manual Docker usage (without Compose)

```bash
docker build -t autoscan .

# debug
docker run --rm --gpus all \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  autoscan python3.11 -m app.main --config /app/config/config.yaml --debug

# production
docker run --rm --gpus all --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  autoscan
```

## Safety notes

- Gate control is fail-closed by design: ambiguous or low-confidence reads,
  and anything not an exact whitelist match, are logged but never trigger
  the gate.
- Every detection (matched or not) is recorded in `data/events.sqlite3` with
  a snapshot, so you can audit false negatives/positives after the fact.
- If the RTSP stream drops or the Home Assistant call fails, the service
  retries with backoff instead of crashing.

## Development

Unit tests cover all the pure logic (normalization, whitelist matching,
cooldown, config validation, the HA client's retry behavior, and event
logging) without needing a GPU:

```bash
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml requests requests-mock opencv-python-headless
.venv/bin/pytest tests/ -v
```

`app/anpr.py`'s parsing of Nomeroff-Net's actual output and `app/camera.py`'s
real RTSP behavior can only be fully verified on a machine with the GPU and
camera available — see the comments in `anpr.py` for what to double-check
on first real deployment.

## Known limitations / next steps

- Single camera, single gate — no multi-camera/multi-gate support yet.
- Whitelist is a static list in `config.yaml`; no hot-reload or HA-managed
  list yet.
- `NomeroffANPR`'s parsing of the pipeline output is based on Nomeroff-Net's
  documented API and hasn't been validated against a live model — verify
  this against your installed version's actual output before trusting it in
  production.

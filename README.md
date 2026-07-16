# hass-autoscan

**English** | [Русский](README.ru.md)

[![Open your Home Assistant instance and start setting up the MQTT integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=mqtt)

autoscan isn't a Home Assistant custom integration — it's a standalone pair
of Docker services that talk to HA over MQTT. The badge above just jumps to
HA's MQTT integration setup, the one manual prerequisite on the HA side;
once that's configured, the RTSP URL/ROI entities described below
[register themselves automatically](#live-control-from-home-assistant) via
MQTT Discovery — there's no separate "install" step for autoscan itself.

CUDA-accelerated license-plate recognition for CCTV gate control, split into
two independently-deployable services connected over MQTT — because the
GPU machine and the Home Assistant host are typically two different
physical machines:

- **`worker/`** — runs on the GPU machine. Watches an RTSP camera, runs
  Nomeroff-Net (YOLOv8 + RNN OCR, optimized for Russian/CIS-format plates)
  to detect and read plates, and publishes each raw detection to MQTT.
- **`client/`** — runs on/near your Home Assistant host, no GPU needed.
  Subscribes to those detections, checks them against a whitelist, and
  calls a Home Assistant service (e.g. a switch or script) to open the
  gate — plus logs every event (SQLite + JPEG snapshot) for audit.

## Architecture

```
[GPU machine]                                    [HA host machine]
worker/                                           client/
RTSP camera → FrameReader → NomeroffANPR    MQTT   → MQTTSubscriber → normalize
   → MQTTPublisher  ───────────────────────────────────→ confidence check
   (raw plate, confidence,                              → whitelist match
    ts, snapshot jpeg b64)                               → cooldown check
                                                         → HAClient.call_gate()
                                                         → EventLogger (SQLite+snapshot)
```

A plate only opens the gate if it's an **exact** whitelist match (after
normalizing Cyrillic/Latin lookalike characters) **and** the OCR confidence
is above a configurable threshold; a cooldown window stops one passing car
from re-triggering the gate repeatedly.

`worker` has a `--debug` mode that skips MQTT entirely — camera + ANPR
only, logging detected plates to the console and saving snapshots locally.
Use this to validate the camera/ANPR pipeline in isolation before wiring up
MQTT/HA at all.

## Requirements

**Worker machine:**
- NVIDIA GPU, drivers, and
  [nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)
  (for Docker GPU access).
- An RTSP-capable camera reachable from this machine.

**Client machine** (e.g. your Home Assistant host):
- Docker (no GPU needed).
- A Home Assistant instance reachable from here, with a long-lived access
  token (Profile → Security → Long-Lived Access Tokens) and a `switch` or
  `script` entity that opens your gate.

**Both machines:**
- Docker + Docker Compose v2.
- Network access to a shared **MQTT broker** (e.g. Home Assistant's
  Mosquitto add-on). This project doesn't run a broker itself — point both
  services' config at one you already have.

## Repo layout

```
worker/            # GPU machine
  app/
    camera.py       # RTSP frame reader with reconnect/backoff
    anpr.py         # Nomeroff-Net wrapper (plate detection + OCR)
    message.py      # builds the MQTT JSON detection payload
    mqtt_publisher.py
    snapshot.py     # local snapshot writer, used only by --debug
    config.py
    main.py
  config/config.example.yaml
  Dockerfile
  docker-compose.prod.yml    # normal run: publishes detections via MQTT
  docker-compose.debug.yml   # --debug run: camera+ANPR only, no MQTT

client/             # HA host, no GPU
  app/
    normalize.py    # plate text normalization (Cyrillic/Latin confusables)
    whitelist.py     # exact-match plate whitelist
    cooldown.py      # per-plate repeat-trigger suppression
    ha_client.py      # Home Assistant REST client (retry/backoff)
    eventlog.py       # SQLite event log + JPEG snapshot persistence
    message.py        # parses the MQTT JSON detection payload
    mqtt_subscriber.py
    config.py
    main.py
  config/config.example.yaml
  Dockerfile
  docker-compose.yml
```

Each side has its own `tests/` (pytest, no GPU or broker required) and
`requirements.txt`. They're fully independent — never run `pytest` across
both trees at once; test each with `(cd worker && pytest tests/)` and
`(cd client && pytest tests/)`.

## MQTT message schema

- **Topic**: `mqtt_topic` on both sides, default `autoscan/plates/detections`
  — must match on worker and client.
- **Payload** (JSON), one message per raw detection (unfiltered — the
  client does all the matching/thresholding):
  ```json
  {
    "schema_version": 1,
    "ts": 1752500000.123456,
    "plate_raw": "А123ВС777",
    "confidence": 0.93,
    "snapshot_jpeg_b64": "<base64 JPEG bytes>"
  }
  ```
- **QoS 1, retain false**. Both services use a fixed `mqtt_client_id` and a
  persistent session so the broker queues detections while either side is
  briefly offline.

## Live control from Home Assistant

The worker also publishes [MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
entities (enabled by default, `ha_discovery_enabled: true`) so two things
can be changed live, from the HA UI, without restarting anything:

- A **text** entity ("RTSP URL") — changing it makes the worker
  immediately reconnect to the new stream.
- Four **number** entities ("ROI x_min/y_min/x_max/y_max") — the
  recognition area, as fractions (0–1) of the frame. Only this rectangle
  is cropped out and fed to Nomeroff-Net, so pointing it at just your gate
  lane both improves accuracy (ignores irrelevant traffic/pedestrians) and
  speeds up detection. Defaults to the full frame (`0,0,1,1`).

These entities appear automatically in HA once the worker connects to the
same broker HA uses for discovery (`ha_discovery_prefix`, default
`homeassistant`). HA publishes value changes with `retain: true`, so if
the worker restarts, resubscribing immediately recovers the last values
you set in HA — no separate persistence needed on the worker side.

`--debug` mode still applies the ROI from `config.yaml` (useful for
visually checking your crop via the saved snapshots before going live),
but since it never connects to MQTT, it can't be adjusted live — only the
static config value applies there.

## ⚠️ Required security setup: broker ACLs

MQTT username/password alone is **not sufficient** once detections cross a
network boundary — anyone who can publish to the detections topic can
forge a message with a guessed whitelisted plate and a high confidence
value, bypassing the camera entirely and opening the gate.

**You must configure broker-side ACLs** restricting the topics: the
worker's credentials should only be allowed to **publish** to
`mqtt_topic`, and the client's credentials should only be allowed to
**subscribe** to it. The worker additionally needs read/write on its own
control-topic tree (`autoscan/<mqtt_client_id>/...`) and write access to
the HA discovery prefix (`<ha_discovery_prefix>/#`) if discovery is
enabled — but nothing else should be able to publish to either, since
anyone who could would be able to redirect the worker's camera or
recognition area. For Mosquitto, this means an
[ACL file](https://mosquitto.org/man/mosquitto-conf-5.html) like:

```
user autoscan-worker
topic write autoscan/plates/detections
topic readwrite autoscan/autoscan-worker/#
topic write homeassistant/#

user autoscan-client
topic read autoscan/plates/detections
```

(Home Assistant's own MQTT integration user also needs to reach
`autoscan/<mqtt_client_id>/+/set` to send commands and
`<ha_discovery_prefix>/#` to receive discovery — this is normally already
covered by HA's built-in Mosquitto add-on user having full broker access.)

TLS is not set up in this project — credentials and payloads travel in
plaintext on your LAN. That's an accepted tradeoff for a trusted home
network, not something this repo hides from you; add TLS yourself if your
broker isn't on a fully trusted network.

## Configuration

### Worker (`worker/config/config.example.yaml` → `config.yaml`)

| Field | Required | Default | Description |
|---|---|---|---|
| `rtsp_url` | always | — | RTSP stream URL |
| `sample_fps` | no | `3` | Frames per second pulled from the stream |
| `mqtt_broker_host` | non-debug mode | — | MQTT broker hostname/IP |
| `mqtt_broker_port` | no | `1883` | MQTT broker port |
| `mqtt_username` / `mqtt_password` | no | `null` | MQTT credentials (publish-only ACL) |
| `mqtt_topic` | no | `autoscan/plates/detections` | Must match the client's topic |
| `mqtt_client_id` | no | `autoscan-worker` | Fixed ID for persistent-session queuing |
| `roi_x_min` / `roi_y_min` / `roi_x_max` / `roi_y_max` | no | `0.0`/`0.0`/`1.0`/`1.0` | Recognition area, as fractions of frame size; live-adjustable from HA once discovery is on |
| `ha_discovery_enabled` | no | `true` | Publishes the HA MQTT Discovery entities described above |
| `ha_discovery_prefix` | no | `homeassistant` | Must match your HA MQTT integration's discovery prefix |

### Client (`client/config/config.example.yaml` → `config.yaml`)

| Field | Required | Default | Description |
|---|---|---|---|
| `mqtt_broker_host` | always | — | MQTT broker hostname/IP |
| `mqtt_broker_port` / `mqtt_username` / `mqtt_password` / `mqtt_topic` / `mqtt_client_id` | no | same defaults as worker (`autoscan-client` for client id) | Must point at the same broker/topic as the worker |
| `ha_url` | production mode | — | Base URL of your Home Assistant instance |
| `ha_token` | production mode | — | Long-lived access token |
| `ha_domain` / `ha_service` / `ha_entity_id` | production mode | — | e.g. `switch` / `turn_on` / `switch.gate_relay` |
| `allowed_plates` | production mode | `[]` | Allowed plate numbers (Cyrillic/Latin mix is normalized before matching) |
| `cooldown_seconds` | no | `60` | Suppresses repeat gate triggers for the same plate |
| `confidence_threshold` | no | `0.85` | Minimum OCR confidence to consider a match |
| `dry_run` | no | `true` | If true, matches/logs normally but never calls Home Assistant |

Both `config.yaml` files are gitignored — they hold credentials, don't
commit them.

## Quick start

**1. On the GPU machine, test the camera + plate recognition first**,
before touching MQTT/HA at all:

```bash
cd worker
cp config/config.example.yaml config/config.yaml   # fill in rtsp_url at least
docker compose -f docker-compose.debug.yml up --build
```

Watch for `[debug] plate=... confidence=...` log lines and check
`data/snapshots/` for the corresponding JPEGs.

**2. Set up your MQTT broker ACLs** (see the security section above), then
fill in the worker's `mqtt_*` fields and the client's full config.

**3. On the client machine, run in `dry_run` mode first** (the default):

```bash
cd client
cp config/config.example.yaml config/config.yaml   # fill in mqtt_*, ha_*, allowed_plates
docker compose up --build
```

**4. Start the worker for real** (publishing to MQTT instead of `--debug`):

```bash
cd worker
docker compose -f docker-compose.prod.yml up -d --build
```

Check the client's `data/events.sqlite3` and `data/snapshots/` for the
events you'd expect — a whitelisted vehicle should show `matched=1` with
`ha_call_result` still `NULL` (skipped because of `dry_run`).

**5. Go live**: set `dry_run: false` in the client's `config.yaml` and
restart it. A whitelisted plate should now trigger the configured Home
Assistant service and open the gate.

## Safety notes

- Gate control is fail-closed by design: ambiguous/low-confidence reads,
  and anything not an exact whitelist match, are logged but never trigger
  the gate.
- Every detection (matched or not) is recorded in the client's
  `data/events.sqlite3` with a snapshot, so you can audit false
  negatives/positives after the fact.
- If the RTSP stream drops, the worker retries with backoff. If the HA
  call fails, the client retries with backoff. Neither crashes the
  service.
- MQTT messages use QoS 1 + persistent sessions, so a brief network blip
  or client restart doesn't silently drop detections — see the broker ACL
  requirement above for why this still isn't a substitute for securing the
  topic.

## Development

Each service's pure logic is unit tested without needing a GPU, camera, or
broker:

```bash
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml requests requests-mock opencv-python-headless paho-mqtt

cd worker && ../.venv/bin/pytest tests/ -v && cd ..
cd client && ../.venv/bin/pytest tests/ -v && cd ..
```

`worker/app/anpr.py`'s parsing of Nomeroff-Net's actual output and
`worker/app/camera.py`'s real RTSP behavior can only be fully verified on
a machine with the GPU and camera available — see the comments in
`anpr.py` for what to double-check on first real deployment. For an
end-to-end transport smoke test without a GPU, point both services at a
throwaway local broker (`docker run -p 1883:1883 eclipse-mosquitto`) and
publish a canned detection through `MQTTPublisher` to confirm the full
parse → whitelist → dry-run HA call → SQLite/snapshot path works.

## If models.vsp.net.ua isn't reachable from your worker machine

Nomeroff-Net downloads its pretrained model weights from
`models.vsp.net.ua` (hardcoded into the library, not configurable to a
mirror — see [ria-com/nomeroff-net#315](https://github.com/ria-com/nomeroff-net/issues/315),
a widely-reported issue with that host). If your worker machine can't
reach it (blocked, filtered, or just flaky), pre-download the models
somewhere that can and copy them over — `worker/models/` is a bind-mounted
volume (`LOCAL_STORAGE=/app/models` in the container) exactly for this:

```bash
# On a machine that CAN reach models.vsp.net.ua:
cd worker
docker compose -f docker-compose.debug.yml build
mkdir -p models
docker compose -f docker-compose.debug.yml run --rm \
  -v "$(pwd)/models:/app/models" autoscan-worker-debug --debug
# ^ let it run long enough to finish downloading (Ctrl-C once you see it
#   start reading frames, or once GPU/network activity settles down),
#   then copy worker/models/ to the same path on your actual worker machine
#   (scp -r models/ user@worker-host:/opt/hass-autoscan/worker/) before
#   starting the real container there.
```

Once `worker/models/` is populated, the container finds everything cached
locally and never needs to reach `models.vsp.net.ua` again.

## Known limitations / next steps

- Single camera, single gate, single MQTT topic — no multi-camera
  namespacing yet.
- Whitelist is a static list in `client/config.yaml`; no hot-reload or
  HA-managed list yet.
- The ROI is a single rectangle, not an arbitrary polygon/mask.
- No TLS on the MQTT connection (see security section).
- `NomeroffANPR`'s parsing of the pipeline output is based on
  Nomeroff-Net's documented API and hasn't been validated against a live
  model — verify this against your installed version's actual output
  before trusting it in production.

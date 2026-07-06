# Capsule skeleton: inject-at-start cold-start on a real Runpod LB endpoint

## What we tested

The capsule "inject at container start" backend (spec §3 backend A): a plain
base image plus a `dockerArgs` command that downloads the supervisor binary and
the language pack from public URLs, extracts them, and `exec`s the supervisor,
which serves `/ping` (LB health) and `/invoke`.

| Parameter | Value |
|-----------|-------|
| Base image | `python:3.11-slim` |
| Supervisor binary size (static linux/amd64) | 6,168,738 bytes (~6.2 MB) |
| Pack tarball size (`python-echo-pack.tar.gz`) | 6,649 bytes (~6.6 KB) |
| Supervisor URL | GitHub release `capsule-skeleton-spike/supervisor` |
| Pack URL | GitHub release `capsule-skeleton-spike/python-echo-pack.tar.gz` |
| Endpoint type | `CpuLiveLoadBalancer` (live-provisioned, `workersMin=1`) |
| Container disk | 10 GB |
| `dockerArgs` | `build_capsule_injection_cmd(supervisor_url, pack_url, "python3 /opt/flash/pack/pack.py")` |

## What we observed

**Deploy path: works.** The SDK path is proven end-to-end for provisioning:

- `PodTemplate(name=..., imageName="python:3.11-slim", dockerArgs=<capsule cmd>, containerDiskInGb=10)`
  passed to `CpuLiveLoadBalancer(..., template=template)` persisted the
  `dockerArgs` through `_configure_existing_template()` and `saveTemplate`
  (which allow-lists the `dockerArgs` field), and `saveEndpoint` accepted it.
- The endpoint was created (id `h4weyjww9j9okj`, name `capsule-spike-59767b96`)
  and a worker started (independently confirmed running).

**Latency numbers: not captured.** The measurement harness buffered stdout to a
pipe and was killed at its wall-clock timeout before the buffer flushed and
before a healthy `/ping` was recorded; no `/ping` or `/invoke` result was
captured in the ~3.5 min the endpoint was live (deployed 14:42:36, torn down
14:46:10). A clean re-run with unbuffered output would be required to record the
cold-start and first-invoke figures — this was deliberately **not** re-run to
avoid provisioning a second paid endpoint after the teardown directive.

| Metric | Result |
|--------|--------|
| Cold-start (container start → first healthy `/ping`) | not captured (harness buffering + kill) |
| First `/invoke` latency | not captured |
| Injection mechanism (dockerArgs → saveTemplate → deploy) | verified working |

## Teardown

- `flash undeploy capsule-spike-59767b96 --force` → "deleted capsule-spike-59767b96".
- Account-level check via the `runpod` SDK (`runpod.get_endpoints()`): no
  `capsule-*`/`spike-*` endpoint remains. No paid endpoint left running.

## Verdict

**Inconclusive on latency; the inject-at-start injection+deploy mechanism itself
is viable.** The `dockerArgs` injection contract is confirmed on real Runpod
infrastructure — a plain `python:3.11-slim` image plus the capsule command
deploys and boots a worker. The cold-start budget question (spec §8 risk 1 —
does download-at-start meet a viable budget, or does it argue for the
OCI-overlay backend?) remains **open** and needs one clean, unbuffered
measurement run before the inject-vs-overlay decision can be made on data.

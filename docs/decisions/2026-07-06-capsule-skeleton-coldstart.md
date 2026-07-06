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

Two runs. The first (endpoint `h4weyjww9j9okj` / `capsule-spike-59767b96`)
proved the deploy path but lost its latency numbers to a probe stdout-buffering
+ timeout-kill bug. A second, clean, controller-driven run (endpoint
`jcayit2o58b3bm` / `capsule-probe-rerun1`, timings written to a file, teardown
via a shell trap) captured the measurement.

**Deploy path: works.** `PodTemplate(name=..., imageName="python:3.11-slim",
dockerArgs=<capsule cmd>, containerDiskInGb=10)` passed to
`CpuLiveLoadBalancer(..., template=template)` persists `dockerArgs` through
`_configure_existing_template()` and `saveTemplate` (which allow-lists the
`dockerArgs` field); `saveEndpoint` accepted it on both runs.

**Capsule runs on real Runpod.** On the clean run the injected supervisor came
up and served the LB health check, and a job round-tripped
HTTP → supervisor `/invoke` → Unix-socket IPC → Python pack → back, with the
payload returned intact.

| Metric | Result |
|--------|--------|
| Cold-start (deploy → first healthy `/ping`) | **39.4 s** |
| First `/invoke` round-trip | **720 ms** |
| Injection mechanism (dockerArgs → saveTemplate → deploy) | verified working |
| Capsule serves on real Runpod (supervisor + pack) | verified (echo round-tripped) |

Note: the probe's `/invoke` body was the IPC-framed `{id,method,input}` envelope
rather than a bare job input, so the pack correctly echoed that whole object
back nested under `result.input` — a probe payload-shape artifact, **not** a
capsule defect. The data returned intact, which is the round-trip proof.

The 39.4 s is dominated by Runpod worker provisioning + base-image pull, not by
the capsule download itself (supervisor 6.2 MB + pack 6.6 KB is a small fraction
of that time). This is consistent with previously observed Runpod live-provision
cold starts (~40 s).

## Teardown

- Run 1: `flash undeploy capsule-spike-59767b96 --force` → "deleted".
- Run 2: shell-trap `flash undeploy capsule-probe-rerun1 --force` →
  `CpuLiveLoadBalancer:jcayit2o58b3bm successfully undeployed` → "✓ deleted".
- Account-level check via `runpod.get_endpoints()` after each run: **no
  `capsule-*`/`probe-*`/`spike-*` endpoint remains.** No paid endpoint left
  running.

## Verdict

**Inject-at-start is functionally viable and the injection overhead is small,
but total serverless cold start (~40 s) is provisioning-dominated.** The
`dockerArgs` injection contract works on real Runpod: a plain
`python:3.11-slim` image plus the capsule command deploys, boots the supervisor,
and serves jobs. For latency-sensitive workloads the ~40 s cold start argues for
keeping workers warm (`workersMin>=1`) and/or the OCI-overlay backend (spec §3
backend B) that removes even the small download-at-start step — but the download
itself is not the bottleneck at this pack size. Larger packs (CUDA-flavored
Python, spec §8 risk 1) still need their own measurement before the
inject-vs-overlay decision generalizes.

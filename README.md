# pray

A simple way to run local Python scripts on a remote Kubernetes cluster.

## Running locally

```sh
BAZEL_REMOTE_SERVICE_HOST="localhost" BAZEL_REMOTE_SERVICE_PORT="8000" \
    python runner.py bundle_id script.py
```

## Building on Mac

```sh
podman build --platform linux/amd64 -f Containerfile --layers --tag "april.dev/pray/runner"
```

```sh
podman run \
    -e BAZEL_REMOTE_SERVICE_HOST="192.168.1.75" \
    -e BAZEL_REMOTE_SERVICE_PORT="8000" \
    0ea1d5b1e870d502c8fe9d4bef64f6afe1013584c6e4762776e9c1aae1ef7eb1 \
    python ./runner.py bundle_id script.py
```

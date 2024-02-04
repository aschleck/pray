# pray

A simple way to run local Python scripts on a remote Kubernetes cluster.

## Launcher

The launcher is responsible for building the archive, uploading it, and executing it.

### Running locally

Port-forward into the Kind cluster with

```sh
kubectl port-forward svc/remote-cache http 8080:80
```

```sh
REMOTE_CACHE_ADDRESS="http://localhost:8080" ./launch.py pray moo.py
```

## Runner

The runner is responsible for downloading an archive and executing it.

### Running locally

```sh
BAZEL_REMOTE_SERVICE_HOST="localhost" BAZEL_REMOTE_SERVICE_PORT="8000" \
    python runner/runner.py bundle_id script.py
```

### Building the container

```sh
podman build --platform linux/amd64 -f runner/Containerfile --layers --tag "april.dev/pray/runner"
```

```sh
podman run \
    -e BAZEL_REMOTE_SERVICE_HOST="192.168.1.75" \
    -e BAZEL_REMOTE_SERVICE_PORT="8000" \
    "april.dev/pray/runner" \
    python ./runner.py bundle_id script.py
```


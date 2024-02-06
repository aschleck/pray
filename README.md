# pray

A simple way to run local Python scripts on a remote Kubernetes cluster.

* The launcher is responsible for building the archive, uploading it, and executing it.
* The runner is responsible for downloading an archive and executing it.

## Launcher

By default it will request 1 Nvidia A10G.

```sh
./launch.py your_repo_root some/amazing/script.py --some_flag_for_your_script another_arg
```

You can request a different GPU like so.

```
./launch.py your_repo_root some/amazing/script.py --accelerator=nvidia-t4-16gb \
    --some_flag_for_your_script another_arg
```

Or more GPUs.

```
./launch.py your_repo_root some/amazing/script.py --accelerator_count=4
```

Or no GPUs.

```
./launch.py your_repo_root some/amazing/script.py --accelerator=none
```

## Developing locally

### Launcher

Port-forward into the Kind cluster with

```sh
kubectl port-forward svc/remote-cache http 8080:80
```

```sh
REMOTE_CACHE_ADDRESS="http://localhost:8080" ./launch.py pray moo.py
```

### Runner

```sh
BAZEL_REMOTE_SERVICE_HOST="localhost" BAZEL_REMOTE_SERVICE_PORT="8000" \
    python runner/runner.py bundle_id script.py
```

Build the container like so.

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


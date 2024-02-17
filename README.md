# pray

A simple way to run local Python scripts on a remote Kubernetes cluster.

* The launcher is responsible for building the archive, uploading it, and executing it.
* The runner is responsible for downloading an archive and executing it.

## Launcher

By default it will request no GPUs.

```sh
./launch.py your_repo_root some/amazing/script.py --some_flag_for_your_script another_arg
```

You can request a default GPU like so (defaults to Nvidia A10G.)

```
./launch.py your_repo_root some/amazing/script.py --accelerator_count=4
```

Or a specific GPU.

```
./launch.py your_repo_root some/amazing/script.py --accelerator=nvidia-t4-16gb \
    --some_flag_for_your_script another_arg
```

## Setting defaults

There are a number of environment variables that control defaults for pray. The intention is for
you to write your own wrapper script that sets the defaults appropriate for your environment.

For example, you might use it in your monorepo with path `repo` and want to specify a default image
and always default to using GPUs.

```sh
#!/usr/bin/env bash

DEFAULT_ACCELERATOR="nvidia-a10g-24gb" \
    DEFAULT_ACCELERATOR_COUNT=1 \
    DEFAULT_IMAGE="yourdomain.com/pray/runner:latest" \
    "$(dirname "$0")/launch.py" repo "$@"
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


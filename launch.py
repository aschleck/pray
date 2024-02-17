#!/usr/bin/env python3

# TODO(april): it'd be nice if the runner had some image version information. Is there anything we
# can do?

import argparse
import getpass
import hashlib
import io
import logging
from netrc import netrc
import os
from pathlib import Path
import random
import sys
import tarfile
import urllib.request

from kubernetes import client, config
from yarl import URL


ACCELERATORS = ("nvidia-a10g-24gb", "nvidia-t4-16gb")
BAZEL_REMOTE_NAME = "remote-cache"
WANDB_HOST = "api.wandb.ai"

DEFAULT_ACCELERATOR = os.environ.get("DEFAULT_ACCELERATOR")
DEFAULT_ACCELERATOR_COUNT = int(os.environ.get("DEFAULT_ACCELERATOR_COUNT", "0"))
DEFAULT_CPU_COUNT = float(os.environ.get("DEFAULT_CPU_COUNT", "1"))
DEFAULT_GLOB = os.environ.get("DEFAULT_GLOB", "**/*.py")
# TODO(april): ?
DEFAULT_IMAGE = os.environ.get("DEFAULT_IMAGE", "april.dev/pray/runner:latest")
DEFAULT_MEMORY_GB = float(os.environ.get("DEFAULT_MEMORY_GB", "0.5"))


def find_bazel_remote() -> URL:
    v1 = client.CoreV1Api()
    endpoints: client.V1Endpoints = v1.read_namespaced_endpoints(
           name=BAZEL_REMOTE_NAME, namespace="default")
    endpoint = None
    for subset in endpoints.subsets:
        http_port = None
        for port in subset.ports:
            if port.name == "http":
                http_port = port.port

        if not http_port:
            continue

        ip = random.choice(subset.addresses).ip
        endpoint = URL.build(scheme="http", host=ip, port=http_port)
        break

    if not endpoint:
        raise Exception(f"Unable to find any available endpoints for {BAZEL_REMOTE_NAME}")
    return endpoint


def find_root(path: Path, needle: str) -> Path:
    parts = path.parts
    for i, part in reversed(list(enumerate(parts))):
        if part == needle:
            return Path(*parts[:i + 1])
    raise Exception(f"Unable to find {needle} in any ancestor of {path}")


def get_wandb_token() -> str|None:
    try:
        if auth := netrc().authenticators(WANDB_HOST):
            return auth[2]
        else:
            return None
    except FileNotFoundError:
        return None


def upload_archive(root: Path, globs: list[str], bazel_remote: URL) -> str:
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:bz2") as tar:
        for glob in globs:
            for p in root.glob(glob):
                tar.add(p, arcname=str(p)[len(str(root)) + 1:])

    tar_bytes = tar_io.getvalue()
    key = hashlib.sha256(tar_bytes).hexdigest()
    request = urllib.request.Request(bazel_remote / "cas" / key, data=tar_bytes, method="PUT")
    with urllib.request.urlopen(request) as f:
        if f.status != 200:
            raise Exception(f"Upload failed: {f.status} {f.reason}\n\n{f.read()}")
    return key


def create_pod(key: str, script: Path, args, pass_through_args: list[str]) -> client.V1Pod:
    user = getpass.getuser()
    v1 = client.CoreV1Api()

    env = {}
    node_selector = {}
    requests = {
        "cpu": args.cpu_count,
        "memory": f"{args.memory_gb}Gi",
    }
    limits = {}
    volumes = {}
    volume_mounts = {}

    if args.accelerator and args.accelerator_count > 0:
        node_selector["april.dev/accelerator"] = args.accelerator
        limits["nvidia.com/gpu"] = args.accelerator_count

    if token := get_wandb_token():
        env["WANDB_API_KEY"] = token

    for mount in args.mount:
        for arg in mount.split(","):
            id = f"mount-{len(volumes)}"
            (key, value) = arg.split("=")
            if key == "pvc":
                volumes[id] = value
            elif key == "target":
                volume_mounts[id] = value
            else:
                raise Exception(f"Unknown mount key {key} with value {value}")

    return v1.create_namespaced_pod(namespace="default", body=client.V1Pod(
        metadata=client.V1ObjectMeta(
            generate_name=f"pray-{user}-",
            namespace="default",
            annotations={"karpenter.sh/do-not-evict": "true"},
            labels={"app.kubernetes.io/name": "pray-runner"},
        ),
        spec=client.V1PodSpec(
            node_selector=node_selector,
            restart_policy="Never",
            containers=[
                client.V1Container(
                    args=[key, str(script)] + pass_through_args,
                    image=args.image,
                    name="runner",
                    env=[client.V1EnvVar(name=k, value=v) for k, v in env.items()],
                    resources=client.V1ResourceRequirements(
                        limits=limits,
                        requests=requests,
                    ),
                    volume_mounts=[
                        client.V1VolumeMount(name=k, mount_path=v) for k, v in volume_mounts.items()
                    ],
                ),
            ],
            volumes=[
                client.V1Volume(
                    name=k,
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=v),
                ) for k, v in volumes.items()
            ],
        ),
    ))


def main(unparsed_args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    parser = argparse.ArgumentParser(prog=unparsed_args[0])
    parser.add_argument("repository_root")
    parser.add_argument("script")
    parser.add_argument("--accelerator", choices=ACCELERATORS, default=DEFAULT_ACCELERATOR)
    parser.add_argument("--accelerator_count", type=int, default=DEFAULT_ACCELERATOR_COUNT)
    parser.add_argument("--cpu_count", type=float, default=DEFAULT_CPU_COUNT)
    parser.add_argument("--glob", default=DEFAULT_GLOB)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--memory_gb", type=float, default=DEFAULT_MEMORY_GB)
    parser.add_argument("--mount", action="append")
    args, unknown_args = parser.parse_known_args(unparsed_args[1:])

    if args.accelerator_count > 0 and not args.accelerator:
        args.accelerator = ACCELERATORS[0]
    elif args.accelerator_count == 0 and args.accelerator:
        args.accelerator_count = 1

    root = find_root(Path(os.getcwd()), args.repository_root)
    config.load_kube_config()
    
    if address := os.environ.get("REMOTE_CACHE_ADDRESS"):
        bazel_remote = address
    else:
        bazel_remote = find_bazel_remote()
    # TODO(april): note that if bazel-remote is replicated than there's no reason to expect that the
    # runner will pick the correct one to fetch this file. The obvious thing to do is pass the IP
    # and port but then we need to check in the launcher that we're not being scroogled.
    key = upload_archive(root, args.glob.split(os.pathsep), bazel_remote)

    script = (root.Path.cwd() / args.script).relative_to(root)
    pod = create_pod(key, script, args, unknown_args)
    print(f"Created {pod.metadata.name}")


if __name__ == "__main__":
    main(sys.argv)

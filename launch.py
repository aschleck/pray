#!/usr/bin/env python3

import argparse
import getpass
import hashlib
import io
import logging
import os
from pathlib import Path
import random
import sys
import tarfile
import urllib.request

from kubernetes import client, config
from yarl import URL


BAZEL_REMOTE_NAME = "remote-cache"


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


def upload_archive(root: Path, bazel_remote: URL) -> str:
    # TODO(april): remove this
    bazel_remote = URL("http://localhost:8080")
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:bz2") as tar:
        for p in root.glob("**/*.py"):
            tar.add(p, arcname=str(p)[len(str(root)) + 1:])

    tar_bytes = tar_io.getvalue()
    key = hashlib.sha256(tar_bytes).hexdigest()
    request = urllib.request.Request(bazel_remote / "cas" / key, data=tar_bytes, method="PUT")
    with urllib.request.urlopen(request) as f:
        if f.status != 200:
            raise Exception(f"Upload failed: {f.status} {f.reason}\n\n{f.read()}")
    return key


def create_manifest(key: str, args, pass_through_args: list[str]) -> client.V1Pod:
    user = getpass.getuser()
    v1 = client.CoreV1Api()

    node_selector = {}
    requests = {
        "cpu": args.cpu_count,
    }
    limits = {}

    if args.accelerator != "none":
        # TODO(april): kind of awkward to use nvidia.com/gpu since we're prefixing with nvidia
        # anyway but since we don't populate the resource count of nvidia.com/gpu I guess we might
        # as well just go with it for now.
        node_selector["nvidia.com/gpu"] = "nvidia-a10g-24gb"
        limits["nvidia.com/gpu"] = args.accelerator_count

    return v1.create_namespaced_pod(namespace="default", body=client.V1Pod(
        metadata=client.V1ObjectMeta(
            generate_name=f"pray-{user}-",
            namespace="default",
            labels={"app.kubernetes.io/name": "pray-runner"},
        ),
        spec=client.V1PodSpec(
            node_selector=node_selector,
            containers=[
                client.V1Container(
                    args=[key, args.script] + pass_through_args,
                    # TODO(april): ?
                    image="april.dev/pray/runner:latest",
                    image_pull_policy="Never",
                    name="runner",
                    resources=client.V1ResourceRequirements(
                        limits=limits,
                        requests=requests,
                    ),
                ),
            ],
        ),
    ))


def main(unparsed_args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    parser = argparse.ArgumentParser(prog=unparsed_args[0])
    parser.add_argument("repository_root")
    parser.add_argument("script")
    parser.add_argument("--accelerator", default="nvidia-a10g-24gb")
    parser.add_argument("--accelerator_count", type=int, default=1)
    parser.add_argument("--cpu_count", type=float, default=1)
    args, unknown_args = parser.parse_known_args(unparsed_args[1:])

    root = find_root(Path(os.getcwd()), args.repository_root)
    config.load_kube_config()
    
    if address := os.environ.get("REMOTE_CACHE_ADDRESS"):
        bazel_remote = address
    else:
        bazel_remote = find_bazel_remote()
    key = upload_archive(root, bazel_remote)

    # TODO(april): note that if bazel-remote is replicated than there's no reason to expect that the
    # runner will pick the correct one to fetch this file. The obvious thing to do is pass the IP
    # and port but then we need to check in the launcher that we're not being scroogled.
    pod = create_manifest(key, args, unknown_args)
    print(f"Created {pod.metadata.name}")


if __name__ == "__main__":
    main(sys.argv)

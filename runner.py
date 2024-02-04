import logging
import os
from pathlib import Path
import shlex
import sys
import tarfile
import urllib.request

from yarl import URL

BAZEL_REMOTE_BASE = URL.build(
    scheme="http",
    host=os.environ.get("BAZEL_REMOTE_SERVICE_HOST", "unknown"),
    port=int(os.environ.get("BAZEL_REMOTE_SERVICE_PORT", "0")),
)


def main(args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if len(args) < 3:
        print(f"Usage: {sys.argv[0]} <bundle-id> <script> {{ args }}", file=sys.stderr)
        sys.exit(1)

    if str(BAZEL_REMOTE_BASE) == "http://unknown:0":
        print("BAZEL_REMOTE_SERVICE_{HOST,PORT} environment variables aren't set", file=sys.stderr)
        sys.exit(1)

    bundle_id = sys.argv[1]
    bundle_url = BAZEL_REMOTE_BASE / "cas" / bundle_id
    output_file = Path("/tmp/bundle.tar.bz2")
    logging.info(f"Fetching {bundle_url} to {output_file}")
    urllib.request.urlretrieve(str(bundle_url), output_file)

    output_path = Path("/tmp/bundle")
    output_path.mkdir()
    logging.info(f"Extracting {output_file} to {output_path}")
    with tarfile.open(output_file) as tar:
        tar.extractall(path=output_path)

    args = [sys.executable] + sys.argv[2:]
    quoted_args = " ".join([shlex.quote(a) for a in args])
    logging.info(f"Executing {quoted_args}")

    sys.stderr.flush()
    sys.stdout.flush()
    os.execv(sys.executable, args)


if __name__ == "__main__":
    main(sys.argv)

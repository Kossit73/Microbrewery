from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download project dependencies to a local directory for offline installation."
    )
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to a requirements file (default: requirements.txt)",
    )
    parser.add_argument(
        "--dest",
        default="vendor",
        help="Destination directory for downloaded wheels (default: vendor)",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Optional proxy URL passed to pip (e.g., http://proxy:port)",
    )
    parser.add_argument(
        "--index-url",
        default=None,
        help="Optional custom package index URL (passed to pip as --index-url)",
    )
    parser.add_argument(
        "--extra-index-url",
        default=None,
        help="Optional extra package index URL (passed to pip as --extra-index-url)",
    )

    args, unknown = parser.parse_known_args()

    req_path = pathlib.Path(args.requirements).resolve()
    dest_dir = pathlib.Path(args.dest).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--no-cache-dir",
        "-d",
        str(dest_dir),
        "-r",
        str(req_path),
    ]

    if args.proxy:
        cmd.extend(["--proxy", args.proxy])
    if args.index_url:
        cmd.extend(["--index-url", args.index_url])
    if args.extra_index_url:
        cmd.extend(["--extra-index-url", args.extra_index_url])

    cmd.extend(unknown)

    print(f"Downloading dependencies from {req_path} into {dest_dir}...\n")
    subprocess.run(cmd, check=True)
    print("\nDownload complete.")


if __name__ == "__main__":
    main()

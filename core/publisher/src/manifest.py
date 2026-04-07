"""Manifest writer.

Produces `manifest.json` (machine-readable index of every artifact in a
published package), `sha256sum.txt` (line-per-file hashes), and a detached
signature using the configured signing key.
"""


async def write(package_dir: str) -> None:
    """Write manifest.json, sha256sum.txt, and signature for `package_dir`."""
    # TODO: walk package_dir, hash each file, emit manifest.json with
    # {path, size, sha256, content_type, layer}, sign manifest with the
    # configured key, and write the detached signature alongside.
    raise NotImplementedError

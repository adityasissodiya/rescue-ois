"""Local PMTiles / attachment cache management.

Responsible for atomic swap of incoming package files into the live cache
directory consumed by Martin and ops-api.
"""


async def install(staged_path: str, target_path: str) -> None:
    """Atomically move a freshly downloaded package file into place."""
    # TODO: verify sha256 against the manifest, fsync, rename(staged_path, target_path).
    raise NotImplementedError


async def list_packages() -> list[dict]:
    """Return descriptors of every package currently installed in the cache."""
    # TODO: walk CACHE_DIR, return [{name, sha256, size, installed_at}, ...]
    raise NotImplementedError

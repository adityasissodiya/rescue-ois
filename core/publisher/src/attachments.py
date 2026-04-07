"""Attachment bundler.

Packages plan PDFs, hazard data sheets, and site photos into tar.zst archives
that the edge `package-cache` can pull and unpack.
"""


async def bundle(plan_id: str, output_path: str) -> None:
    """Bundle all attachments for `plan_id` into a tar.zst at `output_path`."""
    # TODO: query master.attachments for plan_id, stream files into a
    # tar.zst archive, write to output_path atomically.
    raise NotImplementedError

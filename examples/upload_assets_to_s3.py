import boto3
from pathlib import Path
from odootools.odoo import Environment
import mimetypes
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig(level='info')


s3 = boto3.client('s3')
S3_BUCKET = input("S3 Bucket: ")


# Prefix to store files into a specific folder
prefix_path = Path('public')


env = Environment()
# List all modules
for mod in env.modules.list():
    for module_path, full_path in mod.static_assets():
        # Create an object path that will be used as the object name
        object_path = prefix_path / module_path

        # Open a file handle
        with full_path.open('rb') as data:
            # Guess the mimetype
            mime, encoding = mimetypes.guess_type(str(module_path))

            # Prepare some config for s3 store
            extra_args = {
                "ContentType": mime or 'application/octet-stream',
                "CacheControl": 'public, max-age=84600',
                "ACL": 'public-read',
            }

            _logger.info(
                "Uploading object to s3://%s %s",
                S3_BUCKET,
                str(object_path)
            )

            # Upload the file to s3 with the proper settings
            s3.upload_fileobj(
                data,
                S3_BUCKET,
                str(object_path),
                ExtraArgs=extra_args
            )

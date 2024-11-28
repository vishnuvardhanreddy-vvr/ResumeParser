import logging
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from urllib.parse import urlparse

load_dotenv()


def upload_to_blob(data, blob_name):
    connection_string = os.getenv("blob-connection-string")
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(data, overwrite=True)
    logging.info(f"Uploaded file to blob {blob_name} in container {container_name}.")
    blob_url = blob_client.url
    path = urlparse(blob_url).path
    path = path.split('/',2)[-1]
    return path

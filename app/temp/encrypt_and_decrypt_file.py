import logging
import os
import shutil
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
import base64
from urllib.parse import urlparse
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential, ManagedIdentityCredential
from azure.core.exceptions import ClientAuthenticationError
from dotenv import load_dotenv
import time

load_dotenv()


def get_azure_credentials(max_retries=3, delay=2):
    credential = None
    attempts = 0

    while attempts < max_retries:
        try:
            # Get client credentials from environment variables
            client_id = os.getenv("azure-client-id")
            client_secret = os.getenv("azure-client-secret")
            tenant_id = os.getenv("azure-tenant-id")

            # Use ClientSecretCredential for authentication
            credential = ClientSecretCredential(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)

            return credential  # Return immediately if successful
        except ClientAuthenticationError as e:
            logging.error(f"Attempt {attempts + 1} failed: {str(e)}")
            attempts += 1
            time.sleep(delay)  # Wait before retrying
        except Exception as e:
            logging.error(f"Error occurred when fetching azure client secret credentials")

    logging.error("All attempts to get Azure credentials failed.")
    return credential  # Returns None if all attempts fail
    
    
def encrypt_and_upload_file(file_path):
    """
    Encrypts a file using AES-256-CBC and uploads it to Azure Blob Storage.
    
    :param file_path: Path to the input file to encrypt.
    :return: URL of the uploaded blob.
    """
    temp_folder = file_path.split("/")[0]
    try:
        # Load Azure configurations from environment variables
        connection_string = os.getenv("azure-blob-connection-string")
        container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
        aes_key_secret_name = os.getenv("aes-key-secret-name")
        
        key_vault=os.getenv("key-vault-url")
        
        # Extract key name and vault name from the Key Vault URL
        key_vault_name = key_vault.split("/")[2].split(".")[0]
        
        azure_auth = os.getenv("AZURE_AUTHENTICATION")
        
        if azure_auth and azure_auth.lower() in ["true","yes"]:
            azure_auth = True
        elif azure_auth is None:
            azure_auth = False
        else:
            azure_auth = False
        
        aes_key = None
        
        if azure_auth:
        
            # Get default Azure credentials for authentication
            credential = get_azure_credentials()
            
            if credential is None:
                logging.error(f"unable to fetch azure credentials - {str(e)}")
                return {}

            # Step 1: Retrieve the AES key from Azure Key Vault
            key_vault_uri = f"https://{key_vault_name}.vault.azure.net"

            # Create a SecretClient to interact with Azure Key Vault
            secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)

            
            # Fetch the AES key secret from the Key Vault
            aes_key_secret = secret_client.get_secret(aes_key_secret_name)

            # Generate the AES key by hashing the secret with SHA-256
            aes_key = SHA256.new(aes_key_secret.value.encode()).digest()
        else:
            passphrase = os.getenv("passphrase")
            aes_key = SHA256.new(passphrase.encode()).digest()


        # Step 2: Read the file to be encrypted
        with open(file_path, 'rb') as file:
            file_data = file.read()

        # Step 3: Encrypt the data using AES-256-CBC
        cipher = AES.new(aes_key, AES.MODE_CBC)
        iv = cipher.iv
        encrypted_data = iv + cipher.encrypt(pad(file_data, AES.block_size))

        # Generate the output file name by appending "encrypted_" and timestamp to the original file name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        encrypted_file_name = f'encrypted_{os.path.basename(file_path)}'

        # Get the temporary folder from the original file path
        with open(f"{temp_folder}/{encrypted_file_name}", 'wb') as outfile:
            outfile.write(encrypted_data)

        logging.info('File encrypted successfully.')

        # Upload the encrypted file to Azure Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container_name, encrypted_file_name)
        
        logging.info(f'Uploading to Azure storage as blob: {encrypted_file_name}')


        with open(f"{temp_folder}/{encrypted_file_name}", "rb") as data:
            blob_client.upload_blob(data=data, overwrite=True)
            logging.info(f'Upload block blob {encrypted_file_name} successfully.')
            
        blob_url = blob_client.url

        blob_path = urlparse(blob_url).path
        blob_path = blob_path.split('/',2)[-1]

        # Remove the encrypted file after upload (optional)
        shutil.rmtree(temp_folder)
        return {"message":f'Upload block blob {encrypted_file_name} successfully.',"file_name":encrypted_file_name,"blob_path":blob_path}
    except Exception as e:
        shutil.rmtree(temp_folder)
        logging.error(f"unable to encrypt file - {str(e)}")
        return {}

def decrypt_and_download_file(encrypted_file_name):
    """
    Decrypts a file using AES-256-CBC and downloads it from Azure Blob Storage.

    :param encrypted_file_name: Name of the encrypted file to decrypt.
    :return: Path to the decrypted file.
    """
    try:
        # Load Azure configurations from environment variables
        connection_string = os.getenv("azure-blob-connection-string")
        container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
        aes_key_secret_name = os.getenv("aes-key-secret-name")
        
        key_vault=os.getenv("key-vault-url")
        
        # Extract key name and vault name from the Key Vault URL
        key_vault_name = key_vault.split("/")[2].split(".")[0]

        
        azure_auth = os.getenv("AZURE_AUTHENTICATION")
        
        if azure_auth and azure_auth.lower() in ["true","yes"]:
            azure_auth = True
        elif azure_auth is None:
            azure_auth = False
        else:
            azure_auth = False
        
        aes_key = None
        
        if azure_auth:
        
            # Get default Azure credentials for authentication
            credential = get_azure_credentials()
            
            if credential is None:
                logging.error(f"unable to fetch azure credentials - {str(e)}")
                return {}

            # Step 1: Retrieve the AES key from Azure Key Vault
            key_vault_uri = f"https://{key_vault_name}.vault.azure.net"

            # Create a SecretClient to interact with Azure Key Vault
            secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)

            
            # Fetch the AES key secret from the Key Vault
            aes_key_secret = secret_client.get_secret(aes_key_secret_name)

            # Generate the AES key by hashing the secret with SHA-256
            aes_key = SHA256.new(aes_key_secret.value.encode()).digest()
        else:
            passphrase = os.getenv("passphrase")
            aes_key = SHA256.new(passphrase.encode()).digest()

        # Step 2: Download the encrypted file from Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=encrypted_file_name)

        logging.info(f'Downloading from Azure storage: {encrypted_file_name}')
        encrypted_file_data = blob_client.download_blob().readall()
        

        # Step 4: Decrypt the file data using the AES key
        iv = encrypted_file_data[:16]  # Extract the IV from the encrypted data
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_file_data[16:]), AES.block_size)  # Remove padding

        # Generate the output file name
        decrypted_file_name = encrypted_file_name.replace('encrypted_', 'decrypted_')

        # Save the decrypted file
        output_path = f"temp/{decrypted_file_name}"
        with open(output_path, 'wb') as outfile:
            outfile.write(decrypted_data)

        logging.info('File decrypted successfully.')

        # Optionally, remove the temp directory if not in testing environment
        environment = os.getenv("ENVIRONMENT")
        if environment.lower() != "testing":
            shutil.rmtree("temp/")
        return {"message": "File decrypted successfully.", "file_path": output_path}
    except Exception as e:
        shutil.rmtree("temp/")
        logging.error(f"unable to decrypt file - {str(e)}")
        return None
    
    
def delete_encrypted_blob_file(blob_url=None,blob_name=None):
    connection_string = os.getenv("azure-blob-connection-string")
    container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
    
    if blob_url is None and blob_name is None:
        return False
    if blob_url:
        blob_name = blob_url.split("/")[-1]
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    # Delete the blob
    try:
        blob_client.delete_blob()
        logging.info(f"Blob at '{blob_url}' deleted successfully.")
        return True
    except Exception as e:
        logging.error(f"Error occurred while deleting blob: {e}")
        return False

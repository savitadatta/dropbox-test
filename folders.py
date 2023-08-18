import os
import json
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage
from utils import parse_query, string_fits_query, format_datetime
from dropbox_lib import get_dropbox

def search(dir: str, query: str) -> None:
    include, exclude, optional = parse_query(query)
    for root, dirs, files in os.walk(dir):
        for file in files:
            if string_fits_query(file, include, exclude, optional):
                print(os.path.join(root, file))

### Files & metadata
# TODO find out metadata format
def get_filenames_from(dir: str) -> Dict[str, str]:
    all_file_paths = dict()
    for root, dirs, files, in os.walk(dir):
        for file in files:
            path = os.path.join(root, file)
            while '//' in path:
                path = path.replace('//', '/')
            all_file_paths[path] = file
    return all_file_paths

def add_metadata(existing_files: List[str]):
    for filename in existing_files:
        if not filename.endswith(".json"):
            # TODO look for metadata files that havent been moved with their base files
            # also if theres some stored already?
            if not (filename + ".json") in existing_files:
                metadata_path = filename + ".json"
                contents = {
                    "json_path": metadata_path,
                    "name": os.path.basename(filename),
                    "path": filename,
                    "file_last_modified": format_datetime(datetime.fromtimestamp(os.path.getmtime(filename))),
                    "file_created": format_datetime(datetime.fromtimestamp(os.path.getctime(filename))),
                    "topics": [],
                    "category": [],
                    "location": [],
                    "permissions": []
                }
                # with open(metadata_path, 'w', encoding='utf-8') as new_file:
                #     json.dump(contents, new_file, indent=2, default=str)

### Google Cloud Storage
buckets = {
    "STANDARD": "archive-0000-standard-bucket",
    "MONTHLY": "archive-0000-nearline-bucket",
    "QUARTERLY": "archive-0000-coldline-bucket",
    "ANNUAL": "archive-0000-archive-bucket",
}

def upload_file(source_file_name, destination_blob_name="", bucket_name=buckets["ANNUAL"]):
    """Uploads a file to the bucket."""
    if len(destination_blob_name) == 0:
        destination_blob_name = source_file_name

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def get_blob_name_from_filename(full_path, root):
    full_path = os.path.abspath(full_path)
    root = os.path.abspath(root)
    short = full_path.split(root)[-1]
    if short.startswith("/") or short.startswith("\\"):
        short = short[1:]
    return short

### General
def upload_to_gcloud_archive(files: Dict[str, str], bucket_name: str = buckets["ANNUAL"]):
    files = get_filenames_from(dir)

    for path, filename in files.items():
        blob_name = get_blob_name_from_filename(path, dir)
        print(f"path: {path}, filename: {filename}, blob: {blob_name}")
        upload_file(path, blob_name, bucket_name)

def upload_to_dropbox(dbx, files, destination=""):
    for path, filename in files.items():
        with open(path, 'rb') as file:
            # TODO FIX THIS
            contents = file.read()
            edited_path = path[1:] if path.startswith(".") else path
            dbx.files_upload(contents, os.path.join(destination, edited_path))

def download_file(query: str):
    pass

load_dotenv()
files = get_filenames_from(os.getenv("ARCHIVE_DIR"))
dbx = get_dropbox(os.getenv("APP_KEY"), os.getenv("REFRESH_TOKEN"))

# upload_to_gcloud_archive(files)
upload_to_dropbox(dbx, files, "C:\Users\Savita\Dropbox\Project\This")

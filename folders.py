import os
import json
from typing import List
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage
from utils import parse_query, string_fits_query, format_datetime

def search(dir: str, query: str) -> None:
    include, exclude, optional = parse_query(query)
    for root, dirs, files in os.walk(dir):
        for file in files:
            if string_fits_query(file, include, exclude, optional):
                print(os.path.join(root, file))

### Files & metadata
# TODO find out metadata format
def get_filenames_from(dir: str) -> List[str]:
    all_file_paths = []
    for root, dirs, files, in os.walk(dir):
        for file in files:
            filename = os.path.join(root, file)
            all_file_paths.append(filename)
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
def upload_file(source_file_name, destination_blob_name="", bucket_name="archive-0000-archive-bucket"):
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
def process_archive_folder(dir="./files/archive"):
    archive_dir = os.path.join(dir, "glacier")
    medium_files = get_filenames_from(os.path.join(dir, "dropbox"))
    archive_files = get_filenames_from(archive_dir)

    blob_name = get_blob_name_from_filename(archive_files[0], archive_dir)
    upload_file(archive_files[0], blob_name)
    # TODO upload to whatever relevant storage class
    # delete from folder?
    # do the same with dropbox? depends on how the files are currently being stored

load_dotenv()
process_archive_folder(os.getenv("ARCHIVE_DIR"))

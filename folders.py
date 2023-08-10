import os
import json
from typing import List
from datetime import datetime
from dotenv import load_dotenv
from utils import parse_query, string_fits_query, format_datetime

def search(dir: str, query: str) -> None:
    include, exclude, optional = parse_query(query)
    for root, dirs, files in os.walk(dir):
        for file in files:
            if string_fits_query(file, include, exclude, optional):
                print(os.path.join(root, file))

def get_filenames_from(dir: str) -> List[str]:
    all_file_paths = []
    for root, dirs, files, in os.walk(dir):
        for file in files:
            filename = os.path.abspath(os.path.join(root, file))
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

def process_archive_folder(dir="./files/archive"):
    existing_files = get_filenames_from(dir)
    add_metadata(existing_files)
    
    glacier_files = get_filenames_from(os.path.join(dir, "glacier"))
    print("\n".join(glacier_files))
    # TODO upload to whatever relevant storage class
    # delete from folder?
    # do the same with dropbox? depends on how the files are currently being stored

load_dotenv()
process_archive_folder(os.getenv("ARCHIVE_DIR"))

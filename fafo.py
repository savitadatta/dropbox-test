from typing import Dict, Tuple, List, Any
import json
import os
from datetime import datetime
from dotenv import load_dotenv, set_key

from dropbox import Dropbox
from dropbox.files import Metadata, FileMetadata, DeletedMetadata, WriteMode
from dropbox.exceptions import ApiError

# Env and dates
def format_datetime(value: datetime) -> str:
    return datetime.strftime(value, "%Y-%m-%d %H:%M:%S")

def process_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

def get_last_edited(default: datetime) -> datetime:
    env_datetime = os.getenv("LAST_EDITED")
    if not env_datetime:
        update_env("LAST_EDITED", format_datetime(default))
        return default
    return process_datetime(env_datetime)

def get_last_edited_or_now() -> datetime:
    last_checked_default = datetime.now()
    return get_last_edited(last_checked_default)

def update_env(key: str, value: str) -> str:
    set_key(".env", key, value)
    return value

# Dropbox processing
def process_folder_entries(current_state: Dict[str, Metadata], entries) -> Dict[str, FileMetadata]:
    for entry in entries:
        if isinstance(entry, FileMetadata):
            current_state[entry.path_lower] = entry
        elif isinstance(entry, DeletedMetadata):
            current_state.pop(entry.path_lower, None)
    return current_state

def path_exists(path: str) -> bool:
    try:
        dbx.files_get_metadata(path)
        return True
    except ApiError as e:
        if e.error.get_path().is_not_found():
            return False
        raise

# File processing
def add_metadata(entry: FileMetadata):
    filename_split = entry.path_display.split(".")
    if len(filename_split) > 1:
        filename = ".".join(filename_split[:-1])
        extension = filename_split[-1]
    else:
        filename = entry.path_display
        extension = ""

    metadata_path = filename + ".json"
    if not path_exists(metadata_path):
        contents = {
            "id": entry.id,
            "name": entry.name,
            "file type": extension,
            "path_display": entry.path_display,
            "size": entry.size,
            "client_modified_datetime": format_datetime(entry.client_modified)
        }

        encoded = json.dumps(contents, indent=2, default=str).encode('utf-8')

        dbx.files_upload(
            encoded, metadata_path
        )
        print("Creating " + metadata_path)

# General functionality
def dropbox_init() -> Tuple[Dropbox, Dict[str, FileMetadata]]:
    print("Initialising Dropbox API")
    dbx = Dropbox(os.getenv("ACCESS_TOKEN"))

    print("Scanning for files")
    result = dbx.files_list_folder(path="")
    files = process_folder_entries({}, result.entries)

    while result.has_more:
        print("Collecting additional files")
        result = dbx.files_list_folder_continue(result.cursor)
        files = process_folder_entries(files, result.entries)
    return dbx, files

def download_json(entry: FileMetadata) -> Dict[Any, Any]:
    if "json" in entry.path_lower:
        if entry.is_downloadable:
            metadata, response = dbx.files_download(entry.path_lower)
        else:
            # TODO test this (?)
            export_result, response = dbx.files_export(entry.path_lower)
        content = json.loads(response.content)
        return content
    return {}

def add_metadata_to_files(files: Dict[str, FileMetadata]):
    for entry in files.values():
        add_metadata(entry)

def search_for(path: str, query: str) -> List[Metadata]:
    done = False
    start = 0
    result = []
    while not done:
        search_result = dbx.files_search(path, query, start=start)
        result.extend([match.metadata for match in search_result.matches])
        start = search_result.start
        if not search_result.more:
            done = True
    return result


load_dotenv()
dbx, files = dropbox_init()
add_metadata_to_files(files)
# print(str(get_last_edited_or_now()))
# print(str([file.name for file in search_for("", "invoice json")]))

invoice_json = search_for("", "invoice json")
for file in invoice_json:
    print(file)
    d = download_json(file)
    print(d)
    d["last_edited"] = datetime.now()
    encoded = json.dumps(d, indent=2, default=str).encode('utf-8')
    dbx.files_upload(
        encoded, file.path_lower,
        mode=WriteMode.overwrite
    )

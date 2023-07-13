from typing import Dict, Tuple, List, Any
import json
import os
from datetime import datetime
from dotenv import load_dotenv, set_key

from dropbox import Dropbox
from dropbox.files import Metadata, FileMetadata, DeletedMetadata, SearchMode, WriteMode
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

def path_exists(dbx: Dropbox, path: str) -> bool:
    try:
        dbx.files_get_metadata(path)
        return True
    except ApiError as e:
        if e.error.get_path().is_not_found():
            return False
        raise

def get_files(dbx: Dropbox, path="", recursive=True) -> Dict[str, FileMetadata]:
    print("Scanning for files")
    result = dbx.files_list_folder(path, recursive)
    files = process_folder_entries({}, result.entries)

    while result.has_more:
        print("Collecting additional files")
        result = dbx.files_list_folder_continue(result.cursor)
        files = process_folder_entries(files, result.entries)
    return files

# File processing + metadata
def add_metadata(dbx: Dropbox, entry: FileMetadata) -> None:
    filename_split = entry.path_lower.split(".")
    if len(filename_split) > 1:
        filename = ".".join(filename_split[:-1])
        extension = filename_split[-1]
    else:
        filename = entry.path_lower
        extension = ""

    metadata_path = filename + ".json"
    if not path_exists(dbx, metadata_path):
        contents = {
            "json_path": metadata_path,
            "id": entry.id,
            "name": entry.name,
            "file type": extension,
            "path_lower": entry.path_lower,
            "path_display": entry.path_display,
            "size": entry.size,
            "client_modified_datetime": format_datetime(entry.client_modified)
        }

        encoded = json.dumps(contents, indent=2, default=str).encode('utf-8')

        dbx.files_upload(
            encoded, metadata_path
        )
        print("Creating " + metadata_path)

def add_metadata_to_files(dbx: Dropbox, all_files=None, path="", recursive=False) -> None:
    if not all_files:
        all_files = get_files(dbx, path, recursive)

    for entry in all_files.values():
        add_metadata(dbx, entry)

def update_metadata(dbx: Dropbox, metadata: Dict[str, Any], key: str, value: Any) -> None:
    metadata[key] = value
    encoded = json.dumps(metadata, indent=2, default=str).encode('utf-8')
    dbx.files_upload(
        encoded,
        metadata.get(
            "json_path",
            ".".join(metadata["path_lower"].split(".")[:-1] + ["json"])),
        mode=WriteMode.overwrite
    )

# General functionality
def dropbox_init() -> Dropbox:
    print("Initialising Dropbox API")
    dbx = Dropbox(os.getenv("ACCESS_TOKEN"))
    return dbx

def get_metadata_json(dbx: Dropbox, query: str, all_files=None, has_run=False) -> Dict[str, Any]:
    if not ("+json" in query or "+.json" in query):
        query += " +.json"
    if not all_files:
        all_files = get_files(dbx)
    files = search_files(dbx, query, all_files)

    if len(files) == 1:
        entry = files[0]
        print('Downloading json: ' + entry.path_lower)
        if entry.is_downloadable:
            metadata, response = dbx.files_download(entry.path_lower)
        else:
            # TODO test this (?)
            export_result, response = dbx.files_export(entry.path_lower)
        content = json.loads(response.content)
        return content
    else:
        if len(files) > 1:
            if has_run:
                print("Too many files found. Please try again with a more specific query")
                return {}
            print("Too many files: " + str([f.path_lower for f in files]))

            new_query = []
            for q in query.split(" "):
                if not ((q.startswith("+") or q.startswith("-")) and len(q) > 1):
                    new_query.append("+" + q)
                elif q not in new_query:
                    new_query.append(q)

            print("Searching with updated query: " + " ".join(new_query))
            return get_metadata_json(dbx, " ".join(new_query), all_files, True)

        print("No results found")
        # TODO throw exception? return None?
        return {}

def search_files(dbx: Dropbox, query: str, all_files=None, path="", recursive=True) -> List[Metadata]:
    query_terms = query.split(" ")
    include = [s[1:] for s in query_terms if s.startswith("+") and len(s) > 1]
    exclude = [s[1:] for s in query_terms if s.startswith("-") and len(s) > 1]
    optional = [s for s in query_terms if not ((s.startswith("+") or s.startswith("-")) and len(s) > 1)]
    
    # saves having to get all files every time
    if not all_files:
        all_files = get_files(dbx, path, recursive)
    result = []

    for path_lower, metadata in all_files.items():
        if (not any(e in path_lower for e in exclude)) and all(i in path_lower for i in include) \
                and (any(o in path_lower for o in optional) or all(o in path_lower for o in optional)):
            result.append(metadata)
    return result


load_dotenv()
dbx = dropbox_init()
# get_metadata_json(dbx, "+json")
# print([f.path_lower for f in search_files(dbx, "jpg +training -airfare")])
# add_metadata_to_files(dbx)

# d = get_metadata_json(dbx, "invoice json")
# print(d)


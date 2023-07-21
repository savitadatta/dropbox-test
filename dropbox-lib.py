from typing import Dict, Tuple, List, Any
import json
import os
from datetime import datetime
from dotenv import load_dotenv, set_key

from dropbox import Dropbox
from dropbox.files import Metadata, FileMetadata, DeletedMetadata, WriteMode
from dropbox.exceptions import ApiError


class NewMetadata(FileMetadata):
    last_updated: datetime


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
    if not "json" in query:
        query += " +.json"
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

def parse_query(query: str) -> Tuple[List[str], List[str], List[str]]:
    query_terms = query.split(" ")
    include = []
    exclude = []
    optional = []

    phrases = []
    phrase_indices = []
    phrase_indices_all = []
    
    # find out which parts are in phrases
    for i in range(len(query_terms) - 1):
        if query_terms[i].startswith('"') or \
            (any(query_terms[i].startswith(inc_ex) for inc_ex in ["+", "-"]) and query_terms[i][1] == '"'):
            for j in range(i, len(query_terms)):
                if query_terms[j].endswith('"'):
                    phrases.append(" ".join(query_terms[i:j+1]).strip('+-"'))
                    phrase_indices.append([n for n in range(i, j+1)])
                    phrase_indices_all.extend(range(i, j+1))
                    break

    # get indices of which parts to include or exclude
    include_indices = [i for i in range(len(query_terms)) \
                       if query_terms[i].startswith("+") and len(query_terms[i]) > 1]
    exclude_indices = [i for i in range(len(query_terms)) \
                       if query_terms[i].startswith("-") and len(query_terms[i]) > 1]
    
    # add phrases and single terms to include/exclude
    for i in include_indices:
        added = False
        for phrase in range(len(phrases)):
            if i == phrase_indices[phrase][0]:
                include.append(phrases[phrase])
                added = True
                break
        if not added:
            include.append(query_terms[i].strip("+"))
                
    for i in exclude_indices:
        added = False
        for phrase in range(len(phrases)):
            if i == phrase_indices[phrase][0]:
                exclude.append(phrases[phrase])
                added = True
                break
        if not added:
            include.append(query_terms[i].strip("-"))

    for ph in phrases:
        if ph not in include + exclude:
            optional.append(ph)

    # add everything else
    for i in range(len(query_terms)):
        if i not in phrase_indices_all:
            term = query_terms[i].strip('+-')
            if len(term) <= 1 or term not in include + exclude + optional:
                optional.append(term)

    return include, exclude, optional

def search_files(dbx: Dropbox, query: str, all_files=None, path="", recursive=True) -> List[Metadata]:
    include, exclude, optional = parse_query(query)

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

# search_files(dbx, 'json +"the cat" -"sat on" +mats -"carpet" turkey "optional phrase"')

files = search_files(dbx, "json", recursive=False)
print([f.path_lower for f in files])
d = {}
for f in files:
    d[f.path_lower] = f

recently_edited = []
for path, file in d.items():
    meta = get_metadata_json(dbx, path, d)
    if len(meta) > 0:
        if process_datetime(meta["client_modified_datetime"]) > datetime(2023, 6, 26, 5, 58, 52):
            recently_edited.append(meta["path_lower"])

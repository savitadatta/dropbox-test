import os
from datetime import datetime

from utils import parse_query, string_fits_query

def search(dir, query):
    include, exclude, optional = parse_query(query)
    for root, dirs, files in os.walk(dir):
        for file in files:
            if string_fits_query(file, include, exclude, optional):
                print(os.path.join(root, file))

def list_files(dir="./files"):
    for root, dirs, files, in os.walk(dir):
        if not "archive" in root:
            continue
        print("root: {}, dirs: {}, files: {}".format(root, dirs, files))
        for file in files:
            filename = os.path.join(root, file)
            file_size = os.path.getsize(filename) # File size, in bytes.
            file_last_modified = datetime.fromtimestamp(os.path.getmtime(filename))
            file_created = datetime.fromtimestamp(os.path.getctime(filename))

list_files()

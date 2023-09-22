from datetime import datetime
from typing import List, Tuple
from dotenv import set_key

def update_env(key: str, value: str) -> str:
    set_key(".env", key, value)
    return value

# datetimes
def format_datetime(value: datetime) -> str:
    return datetime.strftime(value, "%Y-%m-%d %H:%M:%S")

def process_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

# search
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
            exclude.append(query_terms[i].strip("-"))

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

def string_fits_query(test: str, include: List[str],
                      exclude: List[str], optional: List[str]) -> bool:
    return (not any(e in test for e in exclude)) and all(i in test for i in include) \
                and (any(o in test for o in optional) or len(optional) == 0)

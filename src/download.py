from luxy import PeopleGroups
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import List, Dict


def get_priority_uri(uris, uri_priority):
    """
    Returns the highest-priority URI based on the defined hierarchy.
    If multiple URIs match the same priority level, returns the first.
    """
    for base in uri_priority:
        for uri in uris:
            if uri.startswith(base):
                return uri
    # If no matches, return the first URI or None
    return uris[0] if uris else None

def process_page(args: tuple) -> List[Dict]:
    """
    Processes a single page of results with its own progress bar.

    Args:
        args (tuple): A tuple containing the PeopleGroups object, the page data, and the page number.

    Returns:
        List[Dict]: A list of dictionaries containing the processed data for each item on the page.
    """
    pg, page, page_num = args
    entries = []
    

    uri_priority = [
        "https://linked-art.library.yale.edu/",
        "https://images.peabody.yale.edu/"
        "https://media.art.yale.edu/",
        "https://ycba-lux.s3.amazonaws.com/",
        "https://data.paul-mellon-center.ac.uk/",
        "http://id.loc.gov/",
        "http://vocab.getty.edu/",
        "http://www.wikidata.org/",
        "http://data.bnf.fr/",
        "https://d-nb.info/",
        "http://viaf.org",
        "https://orcid.org/",
        "https://ror.org/"
    ]

    items = pg.get_items(page)
    filename = f"Page {page_num}"
    
    pbar = tqdm(
        total=len(items),
        desc=filename,
        unit='it',
        unit_scale=True,
        position=page_num,  # Each thread gets its own position
        leave=True,        # Keep the bar visible after completion
        ncols=80,         # Fixed width
        mininterval=0.1   # Update more frequently
    )
    
    try:
        for j, item in enumerate(items, 1):
            item_data = pg.get_item_data(item)
            
            # Extract birth and death years
            birth_year = None
            death_year = None
            if 'born' in item_data and 'timespan' in item_data['born']:
                birth_ts = item_data['born']['timespan']
                if 'identified_by' in birth_ts and birth_ts['identified_by']:
                    birth_year = birth_ts['identified_by'][0]['content'][:4]
            if 'died' in item_data and 'timespan' in item_data['died']:
                death_ts = item_data['died']['timespan'] 
                if 'identified_by' in death_ts and death_ts['identified_by']:
                    death_year = death_ts['identified_by'][0]['content'][:4]

            equivalents = item_data.get('equivalent', [])
            equivalent_ids = [equiv['id'] for equiv in equivalents if 'id' in equiv]
            priority_uri = get_priority_uri(equivalent_ids, uri_priority)
            id_equivilant = "http://vocab.getty.edu/aat/300404670"
            primary_name = None
            for name in item_data["identified_by"]:
                content = name["content"]
                for classified_as in name.get("classified_as", []):
                    # Check if equivalent exists before accessing
                    if "equivalent" in classified_as:
                        equiv = classified_as["equivalent"]
                        if isinstance(equiv, list):
                            # Handle case where equivalent is a list
                            for eq in equiv:
                                if eq["id"] == id_equivilant:
                                    primary_name = content
                                    break
                        else:
                            # Handle case where equivalent is a single object
                            if equiv["id"] == id_equivilant:
                                primary_name = content
                                break
            if not primary_name:
                print("No primary name found")
                break
                
            entry = {
                'name': primary_name, #change this to primary english name, then primary name, then _label
                'birth_year': birth_year,
                'death_year': death_year,
                'id': item_data.get('id', None),
                'equivalent': priority_uri if priority_uri else "",
                'page_number': page_num,
                'item_number': j,
                "type": "person"
            }
            entries.append(entry)
            pbar.update(1)
            
    except Exception as e:
        pbar.set_description(f"{filename} (error: {str(e)})")
        raise e
    finally:
        pbar.close()
    
    return entries

def extract_luxy_entries(luxy_query, max_workers: int = 20):
    """
    Extracts entries from the Luxy API using a PeopleGroups object.

    Args:
        luxy_query (LuxY Class): The LuxY object to use for querying.
        max_workers (int): The maximum number of threads to use for processing.

    Returns:
        List[Dict]: A list of dictionaries containing the processed data for each item on the page.
    """
    # Initialize tqdm for parallel bars
    tqdm.set_lock(threading.RLock())
    
    # Remove terminal clearing commands
    print(f"Processing {luxy_query.num_results} results from {luxy_query.view_url}")
    
    # Calculate required lines based on actual number of pages
    all_pages = list(luxy_query.get_page_data_all(start_page=0))
    num_pages = len(all_pages)
    
    # Just add a single newline for spacing
    print()
    
    # Prepare arguments for each thread
    thread_args = [(luxy_query, page, i) for i, page in enumerate(all_pages, 0)]

    # Initialize results list
    all_entries = []
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Process pages in parallel with independent progress bars
            futures = [executor.submit(process_page, args) for args in thread_args]
            results = [f.result() for f in futures]
            
            # Flatten results
            all_entries = [entry for entries in results for entry in entries]
    finally:
        print("\033[?25h", end="")  # Show cursor
    
    return all_entries

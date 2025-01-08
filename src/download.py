from luxy import PeopleGroups
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import List, Dict

def process_page(args: tuple) -> List[Dict]:
    """Process a single page of results with its own progress bar"""
    pg, page, page_num = args
    entries = []
    
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
            
            entry = {
                'name': item_data["_label"],
                'birth_year': birth_year,
                'death_year': death_year,
                'id': item_data.get('id', None),
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

def extract_luxy_entries(query, max_workers: int = 20):
    # Initialize tqdm for parallel bars
    tqdm.set_lock(threading.RLock())
    
    # Clear screen and move cursor to top
    print("\033[2J\033[H", end="")
    print("\033[?25l", end="")  # Hide cursor
    
    pg = PeopleGroups().filter(name=query, recordType="person").get()
    print(f"Processing {pg.num_results} results from {pg.view_url}")
    
    # Create space for all progress bars
    required_lines = max_workers + 5  # Extra buffer for header and potential overflow
    print("\n" * required_lines)
    
    # Get all pages first
    all_pages = list(pg.get_page_data_all(start_page=0))
    
    # Prepare arguments for each thread
    thread_args = [(pg, page, i) for i, page in enumerate(all_pages, 0)]
    
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

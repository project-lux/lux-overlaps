from luxy import PeopleGroups
import tqdm

def extract_luxy_entries(query):
    pg = PeopleGroups().filter(name=query, recordType="person").get()
    print("Total results:", pg.num_results)
    print("View URL:", pg.view_url)
    entries = []
    for i, page in enumerate(tqdm.tqdm(pg.get_page_data_all(start_page=0), desc="Processing pages"), 1):
        for j, item in enumerate(tqdm.tqdm(pg.get_items(page), desc="Processing items"), 1):
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
            
            # Create entry dictionary
            entry = {
                'name': item_data["_label"],
                'birth_year': birth_year,
                'death_year': death_year,
                'id': item_data.get('id', None),  # Add ID if available
                'page_number': i,
                'item_number': j,
                "type": "person"
            }
            entries.append(entry)
    
    return entries

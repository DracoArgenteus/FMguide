import csv
import json
import hashlib
import os

def generate_id(row, row_num, source):
    """Generates a unique and stable ID for an event row."""
    key_string = f"{row.get('title', '')}{row.get('startTime', '')}{row.get('location', '')}{source}{row_num}"
    return hashlib.md5(key_string.encode()).hexdigest()[:12]

def process_csv(file_path, data_source, field_mappings):
    """Reads a CSV file, maps fields to the standard format, and generates IDs."""
    events = []
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            for i, row in enumerate(reader):
                # Create a new standardized event object
                standardized_event = {
                    'DataSource': data_source,
                    'id': generate_id(row, i, data_source)
                }
                # Map fields from the source CSV to the standard format
                for standard_key, source_key in field_mappings.items():
                    standardized_event[standard_key] = row.get(source_key, '') # Use .get for safety
                
                # Special handling for TimeRange if startTime and endTime exist
                if 'startTime' in row and 'endTime' in row:
                    start = row.get('startTime', '').replace('PT','').replace('H',':00').replace('M','')
                    end = row.get('endTime', '').replace('PT','').replace('H',':00').replace('M','')
                    if start and end:
                         standardized_event['TimeRange'] = f"{start}-{end}"
                
                # Special handling for Weekday if day_date exists
                if 'day_date' in row:
                    from datetime import datetime
                    try:
                        date_obj = datetime.strptime(row['day_date'], '%Y-%m-%d')
                        days_danish = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
                        standardized_event['Weekday'] = days_danish[date_obj.weekday()]
                    except ValueError:
                        standardized_event['Weekday'] = ''


                events.append(standardized_event)
    except FileNotFoundError:
        print(f"Warning: File not found at {file_path}. Skipping.")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return events

def main():
    # Define the standard fields the application expects
    standard_fields = [
        "EventTitle", "Weekday", "TimeRange", "Location", 
        "Description", "EventURL", "Organizers", "Theme", 
        "DataSource", "id"
    ]

    # Define the mappings from your source CSV headers to the standard fields
    # This allows flexibility if your CSV files have different column names
    official_mapping = {
        "EventTitle": "title",
        "Location": "location",
        "Description": "summary",
        "EventURL": "eventSlug", # Assuming you want to build the URL from this
        "Organizers": "organizers",
        "Theme": "theme"
    }
    
    # Assume private and social CSVs use the same headers as the official one for now
    # If they have different headers, you can create separate mapping dictionaries for them
    private_mapping = official_mapping
    social_mapping = official_mapping


    files_to_process = {
        'data/official_events_combined.csv': ('Official', official_mapping),
        'data/folkemoedet_private_events.csv': ('Private', private_mapping),
        'data/social_events.csv': ('Social', social_mapping)
    }

    all_events = []
    for file_path, (data_source, mapping) in files_to_process.items():
        all_events.extend(process_csv(file_path, data_source, mapping))

    # Post-process to build full EventURL if needed
    for event in all_events:
        if event.get('EventURL'):
            event['EventURL'] = f"https://program.folkemoedet.dk/event/{event['EventURL']}"


    output_dir = 'public'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, 'events.json')

    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(all_events, outfile, indent=2, ensure_ascii=False)

    print(f"Successfully merged {len(all_events)} events into {output_file}")

if __name__ == "__main__":
    main()

import csv
import json
import hashlib
import os

def generate_id(row, row_num, source):
    """Generates a unique and stable ID for an event row."""
    # Use a combination of key fields to create a stable hash.
    # The source and row number are used as a fallback for uniqueness.
    key_string = f"{row.get('EventTitle', '')}{row.get('TimeRange', '')}{row.get('Location', '')}{source}{row_num}"
    return hashlib.md5(key_string.encode()).hexdigest()[:12]

def process_csv(file_path, data_source):
    """Reads a CSV file, adds a DataSource, and generates unique IDs."""
    events = []
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            for i, row in enumerate(reader):
                # Assign the data source based on the file
                row['DataSource'] = data_source
                # Generate a unique and stable ID for each event
                row['id'] = generate_id(row, i, data_source)
                events.append(row)
    except FileNotFoundError:
        print(f"Warning: File not found at {file_path}. Skipping.")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return events

def main():
    # Define the files to process and their corresponding data sources
    files_to_process = {
        'data/official_events_combined.csv': 'Official',
        'data/folkemoedet_private_events.csv': 'Private',
        'data/social_events.csv': 'Social'
    }

    all_events = []
    for file_path, data_source in files_to_process.items():
        all_events.extend(process_csv(file_path, data_source))

    # Define the output path for the web app
    # This assumes the action runs from the repository root
    output_dir = 'public'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, 'events.json')

    # Write the combined data to a single JSON file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(all_events, outfile, indent=2, ensure_ascii=False)

    print(f"Successfully merged {len(all_events)} events into {output_file}")

if __name__ == "__main__":
    main()

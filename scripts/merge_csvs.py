import csv
import os

def merge_csv_files(output_filename, files_to_merge, target_directory="."):
    """
    Merges multiple CSV files from the target_directory into a single output CSV file
    also placed in the target_directory. Writes the header only once.

    Args:
        output_filename (str): The name of the merged output CSV file.
        files_to_merge (list): A list of CSV filenames to merge (in order).
        target_directory (str): The directory where source CSVs are located and 
                                 the output CSV will be saved.
    """
    wrote_header = False
    
    # Ensure the target directory exists for the output file
    if not os.path.exists(target_directory) and target_directory != ".":
        print(f"Creating target directory: {target_directory}")
        os.makedirs(target_directory)
        
    output_filepath = os.path.join(target_directory, output_filename)

    with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:
        csv_writer_obj = None 

        for filename in files_to_merge:
            filepath = os.path.join(target_directory, filename)
            if not os.path.exists(filepath):
                print(f"Warning: File '{filepath}' not found. Skipping.")
                continue

            print(f"Processing file: {filepath}...")
            try:
                with open(filepath, 'r', newline='', encoding='utf-8') as infile:
                    sample = infile.read(2048) 
                    infile.seek(0) 
                    
                    if not sample.strip(): # Check if file (or sample) is empty or just whitespace
                        print(f"Warning: File '{filepath}' appears to be empty or contains no actual data. Skipping.")
                        continue
                    
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                    except csv.Error:
                        print(f"Warning: Could not determine CSV dialect for '{filepath}'. Using default comma delimiter.")
                        # Fallback to default dialect if sniffing fails
                        class DefaultDialect(csv.excel):
                            delimiter = ','
                            quotechar = '"'
                            quoting = csv.QUOTE_MINIMAL
                        dialect = DefaultDialect()

                    csv_reader = csv.reader(infile, dialect)
                    
                    try:
                        header = next(csv_reader) 
                    except StopIteration:
                        print(f"Warning: File '{filepath}' is empty (no header row). Skipping.")
                        continue # Skip to next file if current one is empty

                    if not wrote_header:
                        csv_writer_obj = csv.writer(outfile, dialect=dialect) # Use dialect from first valid file
                        csv_writer_obj.writerow(header)
                        wrote_header = True
                        print(f"Header written from {filename}: {header}")
                    else:
                        # Optional: Add header consistency check here if needed
                        print(f"Skipping header for {filename}")
                        pass 

                    for row_number, row in enumerate(csv_reader, 1): # Start row_number from 1 for data rows
                        if not any(field.strip() for field in row): # Skip entirely blank rows
                            print(f"Skipping blank row {row_number} in {filename}")
                            continue
                        if len(row) != len(header):
                            print(f"Warning: Row {row_number} in {filename} has {len(row)} fields, header has {len(header)}. Row: {row}. Skipping this row.")
                            continue
                        csv_writer_obj.writerow(row)
                print(f"Finished processing {filename}.")
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    if wrote_header:
        print(f"\nSuccessfully merged files into '{output_filepath}'")
    else:
        print(f"\nNo files were successfully processed or no headers found. Output file '{output_filepath}' might be empty or incomplete.")

if __name__ == "__main__":
    # --- Configuration ---
    # Source CSVs are expected to be in this directory, relative to where the script is run.
    # The GitHub Action will run this script from the repo root, so 'data' is correct.
    DATA_SUBDIRECTORY = "data" 

    thursday_file = "folkemoedet_program_torsdag.csv"
    friday_file = "folkemoedet_program_fredag.csv"
    saturday_file = "folkemoedet_program_lørdag.csv"
    
    # List of files to merge (these will be prefixed with DATA_SUBDIRECTORY)
    files_to_merge_basenames = [thursday_file, friday_file, saturday_file]
    
    # Name of the combined output file (this will also be placed in DATA_SUBDIRECTORY)
    combined_output_filename = "official_events_combined.csv"
    
    print("Starting CSV merge process...")
    # The merge_csv_files function will handle joining DATA_SUBDIRECTORY with the filenames
    merge_csv_files(combined_output_filename, files_to_merge_basenames, DATA_SUBDIRECTORY)
    print("Merge process finished.")

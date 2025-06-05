import csv
import os
import re # For parsing the URL

def parse_event_url(url_string):
    """
    Parses a Folkemødet event URL to extract year, crmId, and slug.
    Example URL: https://programoversigt.folkemoedet.dk/events/2025/26536/vaagn-op-med-morgenyoga
    """
    if not url_string or not url_string.startswith("https://programoversigt.folkemoedet.dk/events/"):
        return None, None, None
    
    match = re.search(r'/events/(\d{4})/(\d+)/([^/?#]+)', url_string)
    if match:
        year = match.group(1)
        crm_id = match.group(2)
        slug = match.group(3)
        return year, crm_id, slug
    else:
        print(f"Warning: Could not parse URL: {url_string}")
        return None, None, None

def merge_csv_files(output_filename, files_to_merge_basenames, target_directory="."):
    """
    Merges multiple official event CSV files from the target_directory into a single 
    output CSV file, also placed in the target_directory. 
    It extracts year, crmId, and slug from the 'url' column and omits the original 'url' column.
    Writes the header only once.
    """
    wrote_header = False
    files_processed_count = 0
    
    if not os.path.exists(target_directory) and target_directory != ".":
        print(f"Attempting to create target directory: {os.path.abspath(target_directory)}")
        try:
            os.makedirs(target_directory)
            print(f"Successfully created target directory: {os.path.abspath(target_directory)}")
        except OSError as e:
            print(f"Error: Could not create target directory {os.path.abspath(target_directory)}. {e}")
            return
        
    output_filepath = os.path.join(target_directory, output_filename)
    print(f"Output file will be: {os.path.abspath(output_filepath)}")

    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as outfile_test:
            pass
        print(f"Successfully tested write access for output file: {os.path.abspath(output_filepath)}")
    except IOError as e:
        print(f"Error: Cannot open or write to output file {os.path.abspath(output_filepath)}. {e}")
        return

    with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as outfile:
        csv_writer_obj = None
        print(f"Attempting to merge and trim {len(files_to_merge_basenames)} specified files.")

        for basename_index, filename_basename in enumerate(files_to_merge_basenames):
            filepath = os.path.join(target_directory, filename_basename)
            print(f"\n--- Processing input file #{basename_index + 1}: {filename_basename} (at: {os.path.abspath(filepath)}) ---")
            
            if not os.path.exists(filepath):
                print(f"Status: File NOT FOUND. Skipping.")
                continue
            
            try:
                file_size = os.path.getsize(filepath)
                print(f"Status: File found. Size: {file_size} bytes.")
                if file_size == 0:
                    print(f"Warning: File is 0 bytes. Skipping.")
                    continue
            except OSError as e:
                print(f"Warning: Could not get size for file. {e}.")

            files_processed_count += 1
            try:
                with open(filepath, 'r', newline='', encoding='utf-8-sig') as infile:
                    print(f"Successfully opened: {filepath}")
                    
                    # Define expected dialect based on Userscript output
                    dialect = csv.excel # Default dialect should work, Userscript quotes all fields
                    dialect.delimiter = ','
                    dialect.quotechar = '"'
                    dialect.quoting = csv.QUOTE_MINIMAL # Reader handles if fields are over-quoted
                    dialect.doublequote = True
                    dialect.skipinitialspace = True
                    
                    csv_reader = csv.reader(infile, dialect=dialect)
                    
                    try:
                        original_header = next(csv_reader)
                        # Clean BOM if present, and strip quotes from headers
                        if original_header and original_header[0].startswith('\ufeff'):
                            original_header[0] = original_header[0][1:]
                        original_header = [h.strip().strip('"') for h in original_header]
                        print(f"Original header from {filename_basename}: {original_header}")
                        
                        if 'url' not in original_header:
                            print(f"Warning: 'url' column not found in header of {filename_basename}. Cannot trim URL. Skipping file.")
                            continue
                        url_col_index = original_header.index('url')
                        
                        # Define new header: exclude 'url', add 'eventYear', 'eventCrmId', 'eventSlug'
                        new_header = [h for h in original_header if h != 'url'] + ['eventYear', 'eventCrmId', 'eventSlug']
                        
                    except StopIteration:
                        print(f"Status: File '{filename_basename}' has no header row. Skipping.")
                        continue
                    except ValueError:
                        print(f"Warning: 'url' column not found in {filename_basename}. Skipping file.")
                        continue


                    if not wrote_header:
                        csv_writer_obj = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                        csv_writer_obj.writerow(new_header)
                        wrote_header = True
                        print(f"WRITTEN: New header to output: {new_header}")
                    else:
                        print(f"SKIPPED WRITING HEADER for {filename_basename}.")
                        # Could add a check here if new_header matches the first_header_written
                        # but since we define it, it should be consistent.
                    
                    rows_written_from_this_file = 0
                    for row_number, original_row in enumerate(csv_reader, 1):
                        if not any(field.strip() for field in original_row):
                            continue
                        if len(original_row) != len(original_header):
                            print(f"Warning: Data row {row_number} in {filename_basename} has {len(original_row)} fields, expected {len(original_header)}. Row: {original_row}. Skipping.")
                            continue
                        
                        url_to_parse = original_row[url_col_index]
                        year, crm_id, slug = parse_event_url(url_to_parse)
                        
                        new_row = [original_row[i] for i, h in enumerate(original_header) if h != 'url']
                        new_row.extend([year if year else '', crm_id if crm_id else '', slug if slug else ''])
                        
                        if csv_writer_obj:
                            csv_writer_obj.writerow(new_row)
                            rows_written_from_this_file += 1
                        else:
                            print(f"CRITICAL ERROR: csv_writer_obj is None. Cannot write rows for {filename_basename}.")
                            break
                    print(f"Finished processing {filename_basename}. {rows_written_from_this_file} data rows written.")
            except Exception as e:
                print(f"Error processing file {filename_basename}: {e}")

    print("\n--- Merge Summary ---")
    if wrote_header:
        print(f"Successfully merged and trimmed content into '{os.path.abspath(output_filepath)}'")
        print(f"{files_processed_count} files were found and had content processed from.")
    else:
        print(f"No headers were written to the output file '{os.path.abspath(output_filepath)}'.")
        print(f"{files_processed_count} files were found (check logs above for individual file status).")

if __name__ == "__main__":
    DATA_SUBDIRECTORY = "data" 
    print(f"Script current working directory: {os.path.abspath(os.getcwd())}")
    print(f"Target data subdirectory (relative to CWD): {DATA_SUBDIRECTORY}")
    
    full_data_path = os.path.abspath(DATA_SUBDIRECTORY)
    print(f"Absolute path to target data subdirectory: {full_data_path}")
    if not os.path.isdir(full_data_path):
        print(f"CRITICAL WARNING: Data subdirectory '{full_data_path}' does NOT exist.")

    # These are the files generated by your Userscript
    thursday_file = "folkemoedet_program_torsdag.csv"
    friday_file = "folkemoedet_program_fredag.csv"
    saturday_file = "folkemoedet_program_lørdag.csv"
    
    files_to_merge_basenames = [thursday_file, friday_file, saturday_file]
    print(f"Basenames of files to merge: {files_to_merge_basenames}")
    
    combined_output_filename = "official_events_combined.csv"
    
    print("\nStarting CSV merge and trim process...")
    merge_csv_files(combined_output_filename, files_to_merge_basenames, DATA_SUBDIRECTORY)
    print("\nMerge and trim process finished.")


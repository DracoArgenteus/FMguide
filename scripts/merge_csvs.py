import csv
import os

def merge_csv_files(output_filename, files_to_merge_basenames, target_directory="."): # Changed files_to_merge to files_to_merge_basenames for clarity
    """
    Merges multiple CSV files from the target_directory into a single output CSV file
    also placed in the target_directory. Writes the header only once.
    """
    wrote_header = False
    files_processed_count = 0 # Counter for files that were actually opened and attempted to read
    first_header_written = [] # Store the first header to compare (optional)

    # Ensure the target directory exists for the output file
    if not os.path.exists(target_directory) and target_directory != ".": # Avoid creating "." if it's the current dir
        print(f"Attempting to create target directory: {os.path.abspath(target_directory)}")
        try:
            os.makedirs(target_directory)
            print(f"Successfully created target directory: {os.path.abspath(target_directory)}")
        except OSError as e:
            print(f"Error: Could not create target directory {os.path.abspath(target_directory)}. {e}")
            return # Cannot proceed if output directory cannot be made
        
    output_filepath = os.path.join(target_directory, output_filename)
    print(f"Output file will be: {os.path.abspath(output_filepath)}")

    # Try to open the output file first to catch permission issues early
    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile_test:
            pass # Just test opening and closing
        print(f"Successfully tested write access for output file: {os.path.abspath(output_filepath)}")
    except IOError as e:
        print(f"Error: Cannot open or write to output file {os.path.abspath(output_filepath)}. Check permissions. {e}")
        return

    with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:
        csv_writer_obj = None 
        print(f"Attempting to merge {len(files_to_merge_basenames)} specified files.")

        for basename_index, filename_basename in enumerate(files_to_merge_basenames):
            filepath = os.path.join(target_directory, filename_basename)
            print(f"\n--- Processing input file #{basename_index + 1}: {filename_basename} (resolved to: {os.path.abspath(filepath)}) ---")
            
            if not os.path.exists(filepath):
                print(f"Status: File NOT FOUND at '{os.path.abspath(filepath)}'. Skipping.")
                continue
            
            # Check file size
            try:
                file_size = os.path.getsize(filepath)
                print(f"Status: File found. Size: {file_size} bytes.")
                if file_size == 0:
                    print(f"Warning: File '{filepath}' is 0 bytes. Skipping content processing.")
                    continue
            except OSError as e:
                print(f"Warning: Could not get size for file '{filepath}'. {e}. Attempting to process anyway.")


            files_processed_count += 1
            try:
                with open(filepath, 'r', newline='', encoding='utf-8') as infile:
                    print(f"Successfully opened: {filepath}")
                    # Read a sample for dialect sniffing, be careful with very small files
                    try:
                        sample = infile.read(2048) 
                        infile.seek(0) # Rewind
                    except Exception as e_read_sample:
                        print(f"Warning: Could not read sample from '{filepath}'. {e_read_sample}. Skipping this file.")
                        continue
                    
                    if not sample.strip():
                        print(f"Status: File content (first 2048 bytes) is empty or whitespace only after stripping. Skipping content.")
                        continue
                    else:
                        # Ensure not to print too much if sample is binary or very long
                        print(f"Status: File has content. First 50 chars of sample (escaped): {sample[:50].encode('unicode_escape')}")
                    
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                        print(f"CSV dialect sniffed for {filename_basename}: delimiter='{dialect.delimiter}', quotechar='{dialect.quotechar}', quoting={dialect.quoting}")
                    except csv.Error as e_sniff:
                        print(f"Warning: Could not determine CSV dialect for '{filename_basename}' from sample. {e_sniff}. Using default comma delimiter.")
                        class DefaultDialect(csv.excel): # Define fallback dialect
                            delimiter = ','
                            quotechar = '"'
                            quoting = csv.QUOTE_MINIMAL
                        dialect = DefaultDialect()

                    csv_reader = csv.reader(infile, dialect)
                    
                    try:
                        header = next(csv_reader)
                        print(f"Header extracted from {filename_basename}: {header}") 
                    except StopIteration:
                        print(f"Status: File '{filename_basename}' has no header row (or no rows at all after sniffing). Skipping.")
                        continue

                    if not wrote_header:
                        if csv_writer_obj is None: 
                             csv_writer_obj = csv.writer(outfile, dialect=dialect)
                        csv_writer_obj.writerow(header)
                        wrote_header = True
                        first_header_written = header # Store the first written header
                        print(f"WRITTEN: Header from {filename_basename} to output.")
                    else:
                        print(f"SKIPPED WRITING HEADER for {filename_basename} (header already written).")
                        if header != first_header_written:
                             print(f"Warning: Header for {filename_basename} ({header}) differs from first header written ({first_header_written}). Using first header's column count for subsequent row validation.")
                        # Use first_header_written for column count consistency check
                        header_for_validation = first_header_written
                        pass 
                    
                    header_for_validation = first_header_written if wrote_header else header

                    rows_written_from_this_file = 0
                    for row_number, row in enumerate(csv_reader, 1): 
                        if not any(field.strip() for field in row):
                            # print(f"Skipping blank data row {row_number} in {filename_basename}") # Can be too verbose
                            continue
                        if len(row) != len(header_for_validation):
                            print(f"Warning: Data row {row_number} in {filename_basename} has {len(row)} fields, expected {len(header_for_validation)} based on header. Row: {row}. Skipping this row.")
                            continue
                        if csv_writer_obj: 
                            csv_writer_obj.writerow(row)
                            rows_written_from_this_file += 1
                        else:
                            print(f"CRITICAL ERROR: csv_writer_obj is None but trying to write rows for {filename_basename}.")
                            break 
                    print(f"Finished processing {filename_basename}. {rows_written_from_this_file} data rows written.")
            except Exception as e:
                print(f"Error processing file {filename_basename}: {e}")

    print("\n--- Merge Summary ---")
    if wrote_header:
        print(f"Successfully merged content into '{os.path.abspath(output_filepath)}'")
        print(f"{files_processed_count} files were found and attempted to process content from.")
    else:
        print(f"No headers were written to the output file '{os.path.abspath(output_filepath)}'.")
        print(f"This means either no input files were found, all found files were empty/headerless, or another issue prevented header processing.")
        print(f"{files_processed_count} files were found and attempted to process (check logs above for individual file status).")
        if not files_to_merge_basenames:
            print("The list of files to merge was empty.")

if __name__ == "__main__":
    DATA_SUBDIRECTORY = "data" 
    print(f"Script current working directory: {os.path.abspath(os.getcwd())}")
    print(f"Target data subdirectory (relative to CWD): {DATA_SUBDIRECTORY}")
    
    full_data_path = os.path.abspath(DATA_SUBDIRECTORY)
    print(f"Absolute path to target data subdirectory: {full_data_path}")
    if not os.path.isdir(full_data_path):
        print(f"CRITICAL WARNING: Data subdirectory '{full_data_path}' does NOT exist. This script will likely find no input files.")
        # Script will continue and attempt to create for output, but input files will be missing.

    thursday_file = "folkemoedet_program_torsdag.csv"
    friday_file = "folkemoedet_program_fredag.csv"
    saturday_file = "folkemoedet_program_lørdag.csv"
    
    files_to_merge_basenames = [thursday_file, friday_file, saturday_file]
    print(f"Basenames of files to merge: {files_to_merge_basenames}")
    
    combined_output_filename = "official_events_combined.csv"
    
    print("\nStarting CSV merge process...")
    merge_csv_files(combined_output_filename, files_to_merge_basenames, DATA_SUBDIRECTORY)
    print("\nMerge process finished.")

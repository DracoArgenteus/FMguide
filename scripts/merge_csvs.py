import csv
import os

def merge_csv_files(output_filename, files_to_merge_basenames, target_directory="."):
    """
    Merges multiple CSV files from the target_directory into a single output CSV file
    also placed in the target_directory. Writes the header only once.
    Explicitly handles quoting and BOM.
    """
    wrote_header = False
    files_processed_count = 0
    first_header_written = []

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
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as outfile_test: # utf-8-sig for BOM in output
            pass
        print(f"Successfully tested write access for output file: {os.path.abspath(output_filepath)}")
    except IOError as e:
        print(f"Error: Cannot open or write to output file {os.path.abspath(output_filepath)}. Check permissions. {e}")
        return

    with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as outfile: # utf-8-sig for BOM in output
        csv_writer_obj = None
        print(f"Attempting to merge {len(files_to_merge_basenames)} specified files.")

        for basename_index, filename_basename in enumerate(files_to_merge_basenames):
            filepath = os.path.join(target_directory, filename_basename)
            print(f"\n--- Processing input file #{basename_index + 1}: {filename_basename} (resolved to: {os.path.abspath(filepath)}) ---")
            
            if not os.path.exists(filepath):
                print(f"Status: File NOT FOUND at '{os.path.abspath(filepath)}'. Skipping.")
                continue
            
            try:
                file_size = os.path.getsize(filepath)
                print(f"Status: File found. Size: {file_size} bytes.")
                if file_size == 0:
                    print(f"Warning: File '{filepath}' is 0 bytes. Skipping.")
                    continue
            except OSError as e:
                print(f"Warning: Could not get size for file '{filepath}'. {e}.")


            files_processed_count += 1
            try:
                # Open with 'utf-8-sig' to handle potential BOM transparently on read
                with open(filepath, 'r', newline='', encoding='utf-8-sig') as infile:
                    print(f"Successfully opened: {filepath}")
                    
                    # Explicitly define the dialect since we know how the Userscript creates it
                    # Userscript uses comma delimiter, quotes all fields, and escapes quotes with double quotes.
                    # Python's csv module default for excel dialect handles doublequote=True.
                    # QUOTE_ALL means all fields are quoted.
                    csv_reader = csv.reader(infile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, doublequote=True, skipinitialspace=True)
                    # Note: QUOTE_ALL might be more accurate if your userscript literally quotes every field.
                    # QUOTE_MINIMAL with doublequote=True should still work if fields are "over-quoted".
                    # The error "need to escape, but no escapechar set" suggests sniffer might be setting escapechar to None.
                    # Forcing doublequote=True is key.
                    # skipinitialspace=True can help if there are spaces after delimiters.

                    try:
                        header = next(csv_reader)
                        # Clean BOM from the first header field if it was manually read (utf-8-sig should handle it)
                        # However, the log showed '\ufeff"title"'. Let's ensure it's clean.
                        if header and header[0].startswith('\ufeff'):
                            header[0] = header[0][1:] # Remove BOM
                        # Also remove potential surrounding quotes if they were part of the field due to BOM issue
                        header = [h.strip('"') for h in header] 
                        print(f"Header extracted from {filename_basename}: {header}") 
                    except StopIteration:
                        print(f"Status: File '{filename_basename}' has no header row (or no rows at all). Skipping.")
                        continue

                    if not wrote_header:
                        # Use the dialect settings that match our reader for the writer
                        csv_writer_obj = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True)
                        csv_writer_obj.writerow(header)
                        wrote_header = True
                        first_header_written = header
                        print(f"WRITTEN: Header from {filename_basename} to output.")
                    else:
                        print(f"SKIPPED WRITING HEADER for {filename_basename} (header already written).")
                        if header != first_header_written:
                             print(f"Warning: Header for {filename_basename} ({header}) differs from first header written ({first_header_written}).")
                        header_for_validation = first_header_written # Use first header for consistency
                    
                    header_for_validation = first_header_written if wrote_header else header

                    rows_written_from_this_file = 0
                    for row_number, row in enumerate(csv_reader, 1): 
                        if not any(field.strip() for field in row):
                            continue
                        if len(row) != len(header_for_validation):
                            print(f"Warning: Data row {row_number} in {filename_basename} has {len(row)} fields, expected {len(header_for_validation)}. Row: {row}. Skipping.")
                            continue
                        if csv_writer_obj: 
                            csv_writer_obj.writerow(row)
                            rows_written_from_this_file += 1
                        else: # Should not happen if header was written
                            print(f"CRITICAL ERROR: csv_writer_obj is None. Cannot write rows for {filename_basename}.")
                            break 
                    print(f"Finished processing {filename_basename}. {rows_written_from_this_file} data rows written.")
            except Exception as e:
                print(f"Error processing file {filename_basename}: {e}")

    print("\n--- Merge Summary ---")
    if wrote_header:
        print(f"Successfully merged content into '{os.path.abspath(output_filepath)}'")
        print(f"{files_processed_count} files were found and had content processed from.")
    else:
        print(f"No headers were written to the output file '{os.path.abspath(output_filepath)}'.")
        print(f"{files_processed_count} files were found (check logs above for individual file status).")
        if not files_to_merge_basenames:
            print("The list of files to merge was empty.")

if __name__ == "__main__":
    DATA_SUBDIRECTORY = "data" 
    print(f"Script current working directory: {os.path.abspath(os.getcwd())}")
    print(f"Target data subdirectory (relative to CWD): {DATA_SUBDIRECTORY}")
    
    full_data_path = os.path.abspath(DATA_SUBDIRECTORY)
    print(f"Absolute path to target data subdirectory: {full_data_path}")
    if not os.path.isdir(full_data_path):
        print(f"CRITICAL WARNING: Data subdirectory '{full_data_path}' does NOT exist. Input files will not be found.")

    thursday_file = "folkemoedet_program_torsdag.csv"
    friday_file = "folkemoedet_program_fredag.csv"
    saturday_file = "folkemoedet_program_lørdag.csv"
    
    files_to_merge_basenames = [thursday_file, friday_file, saturday_file]
    print(f"Basenames of files to merge: {files_to_merge_basenames}")
    
    combined_output_filename = "official_events_combined.csv"
    
    print("\nStarting CSV merge process...")
    merge_csv_files(combined_output_filename, files_to_merge_basenames, DATA_SUBDIRECTORY)
    print("\nMerge process finished.")

# work_order_util.py
import os
import datetime

def create_work_order_file(auto_doc_ref):
    """
    Creates a text file named 'work_order_<auto_doc_ref>.txt'
    in a folder structure: work_orders/YYYY-MM-DD/work_order_<auto_doc_ref>.txt
    
    Currently writes a fixed text string into the file:
    'test complete, work order written to successfully'
    """
    # 1. Generate today's date string (e.g. '2025-01-08')
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # 2. Construct the parent folder paths
    work_orders_folder = os.path.join(os.getcwd(), 'work_orders')
    date_folder_path = os.path.join(work_orders_folder, date_str)

    # 3. Create the date folder if it doesn't exist
    if not os.path.exists(date_folder_path):
        os.makedirs(date_folder_path)

    # 4. Build the file name, e.g. "work_order_02342.txt"
    file_name = f"work_order_{auto_doc_ref}.txt"
    file_path = os.path.join(date_folder_path, file_name)

    # 5. Write our fixed text into the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("test complete, work order written to successfully")

    # 6. (Optional) Print a message or return the file path
    print(f"Work order file created at: {file_path}")

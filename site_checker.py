import gspread
from google.oauth2.service_account import Credentials
import requests
import time
from datetime import datetime
import tkinter as tk # NEW: Import the GUI library
from tkinter import messagebox # NEW: For displaying messages

# --- Configuration (Remains the same) ---
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1xAAKZIMmNQZR7o4Twb_WengPe6IeoUH-zq6L6gKkHps' 
SHEET_NAME = 'Sheet1' 
URL_RANGE = 'C2:C' 
STATUS_COLUMN = 'D' 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
}
FORBIDDEN_KEYWORDS = [
    "account suspended", 
    "domain parking", 
    "suspended page", 
    "default web page",
    "web host default page"
]

# --- Core Logic Functions (Retained) ---

def authenticate_and_open_sheet():
    """Authenticates using service account and returns the worksheet."""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        return worksheet
    except Exception as e:
        # Display authentication error in a GUI pop-up
        messagebox.showerror("Authentication Error", f"Failed to connect to Google Sheets.\nError: {e}.\n\nEnsure 'service_account.json' is present and the sheet is shared.")
        return None

def check_website_status(url, session):
    """Checks a single website's status using a requests Session and checks page content for suspension."""
    if not url or url.isspace():
        return "⚠️ Empty URL"

    url = url.strip()
    if not url.startswith('http'):
        url = 'https://' + url 

    try:
        # Use session.get() and stream=True to check content without downloading the whole page
        with session.get(url, timeout=10, allow_redirects=True, headers=HEADERS, stream=True) as response: 
            
            # 1. Check HTTP Status Code
            if not 200 <= response.status_code < 300:
                if 300 <= response.status_code < 400:
                     return "🟡 Redirect (Status: {})".format(response.status_code)
                else:
                    return "❌ Broken (Status: {})".format(response.status_code)
            
            # 2. Check Page Content (Only if status is 200-299)
            content_chunk = response.content[:102400].decode('utf-8', errors='ignore').lower()

            for keyword in FORBIDDEN_KEYWORDS:
                if keyword in content_chunk:
                    return "⚠️ Content Error (Status: 200 but Suspended/Parked Content)"

            # If status is 2xx and no forbidden content is found
            return "✅ Working (Status: {})".format(response.status_code)
            
    except requests.exceptions.Timeout:
        return "⚠️ Timeout"
    except requests.exceptions.ConnectionError:
        return "⚠️ Connection Error (Blocked or DNS Fail)" 
    except Exception as e:
        return f"❌ Unknown Error: {e.__class__.__name__}"

def generate_html_report(report_data):
    """Creates a beautiful, self-contained HTML file to display the results with filtering."""
    
    filename = "site_check_report.html"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate summary statistics
    total_sites = len(report_data)
    working_sites = sum(1 for item in report_data if "✅ Working" in item['status'])
    broken_sites = sum(1 for item in report_data if "❌ Broken" in item['status'])
    connection_errors = sum(1 for item in report_data if "Connection Error" in item['status'] or "Timeout" in item['status'] or "Content Error" in item['status'] or "🟡 Redirect" in item['status'])

    # JavaScript filtering logic (The interactive part of the interface)
    js_script = """
    function filterTable(statusType) {
        const rows = document.querySelectorAll('#detailed-table-body tr');
        
        rows.forEach(row => {
            const rowStatus = row.getAttribute('data-status');
            
            if (statusType === 'all') {
                row.style.display = '';
            } else if (rowStatus === statusType) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    """

    # --- HTML Structure and Styling ---
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Status Checker Report</title>
    <!-- Load Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #f7fafc; }}
        .working-row {{ background-color: #ecfdf5; border-left: 4px solid #10b981; }}
        .broken-row {{ background-color: #fef2f2; border-left: 4px solid #ef4444; }}
        .warning-row {{ background-color: #fffbeb; border-left: 4px solid #f59e0b; }}
        .summary-card {{ transition: transform 0.1s; cursor: pointer; }}
        .summary-card:hover {{ transform: scale(1.02); }}
    </style>
</head>
<body class="p-4 sm:p-8">
    <div class="max-w-6xl mx-auto bg-white shadow-xl rounded-xl p-6 sm:p-10">
        <header class="mb-8 border-b pb-4">
            <h1 class="text-4xl font-extrabold text-gray-900 mb-2">Website Health Check</h1>
            <p class="text-gray-500">Report Generated: {timestamp} | Source Sheet ID: <code class="bg-gray-100 p-1 rounded text-sm text-indigo-600">{SPREADSHEET_ID}</code></p>
        </header>

        <!-- Summary Cards (Interactive buttons) -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
            <div onclick="filterTable('all')" class="summary-card bg-indigo-50 p-4 rounded-lg shadow-md border-b-4 border-indigo-500">
                <p class="text-sm font-medium text-indigo-600">Total Sites</p>
                <p class="text-3xl font-bold text-indigo-900">{total_sites}</p>
            </div>
            <div onclick="filterTable('working')" class="summary-card bg-green-50 p-4 rounded-lg shadow-md border-b-4 border-green-500">
                <p class="text-sm font-medium text-green-600">Working (2xx)</p>
                <p class="text-3xl font-bold text-green-900">{working_sites}</p>
            </div>
            <div onclick="filterTable('warning')" class="summary-card bg-yellow-50 p-4 rounded-lg shadow-md border-b-4 border-yellow-500">
                <p class="text-sm font-medium text-yellow-600">Errors/Redirects/Content</p>
                <p class="text-3xl font-bold text-yellow-900">{connection_errors}</p>
            </div>
            <div onclick="filterTable('broken')" class="summary-card bg-red-50 p-4 rounded-lg shadow-md border-b-4 border-red-500">
                <p class="text-sm font-medium text-red-600">Broken (4xx/5xx)</p>
                <p class="text-3xl font-bold text-red-900">{broken_sites}</p>
            </div>
        </div>

        <!-- Detailed Table -->
        <h2 class="text-2xl font-semibold text-gray-800 mb-4 border-b pb-2">Detailed Status Log</h2>
        <div class="overflow-x-auto rounded-lg shadow-lg">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">#</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">URL</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status & Details</th>
                    </tr>
                </thead>
                <tbody id="detailed-table-body" class="bg-white divide-y divide-gray-200">
"""
    
    for i, item in enumerate(report_data):
        url = item['url']
        status = item['status']
        
        # Determine row class and data-status attribute for filtering
        row_class = 'bg-white'
        data_status = 'all' # Default
        if "✅ Working" in status:
            row_class = 'working-row'
            data_status = 'working'
        elif "❌ Broken" in status:
            row_class = 'broken-row'
            data_status = 'broken'
        elif "⚠️ Connection" in status or "⚠️ Timeout" in status or "🟡 Redirect" in status or "Content Error" in status:
            # All non-fatal issues (warnings) are grouped here
            row_class = 'warning-row'
            data_status = 'warning'
        
        html_content += f"""
                    <tr data-status="{data_status}" class="{row_class} hover:bg-gray-50 transition duration-150 ease-in-out">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{i + 1}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:text-blue-800"><a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a></td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{status}</td>
                    </tr>
        """

    html_content += f"""
                </tbody>
            </table>
        </div>
    </div>
    <!-- JavaScript for filtering -->
    <script>
        {js_script}
    </script>
</body>
</html>
"""

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        # Instead of printing, we'll show a GUI message
        return filename
    except Exception as e:
        messagebox.showerror("File Error", f"Failed to write HTML report: {e}")
        return None

# --- Main Application Logic (Triggered by Button) ---

def start_scan_and_report(root_window, status_label, scan_button):
    """
    Executes the entire scanning and reporting process,
    updating the GUI status and disabling the button during the run.
    """
    scan_button.config(state=tk.DISABLED, text="Scanning... Do not close")
    root_window.update() # Update the GUI immediately

    try:
        status_label.config(text="1/5: Authenticating with Google Sheets...")
        root_window.update()

        worksheet = authenticate_and_open_sheet()
        if not worksheet:
            scan_button.config(state=tk.NORMAL, text="Start Scan")
            return

        status_label.config(text="2/5: Successfully connected. Reading URLs...")
        root_window.update()
        
        session = requests.Session() 

        # 1. Read all URLs from the specified range
        url_data = worksheet.get(URL_RANGE, value_render_option='UNFORMATTED_VALUE')
        urls = [str(row[0]).strip() for row in url_data if row and str(row[0]).strip()]
        
        if not urls:
            messagebox.showinfo("Scan Complete", "No valid URLs found in the specified range.")
            scan_button.config(state=tk.NORMAL, text="Start Scan")
            return

        total_urls = len(urls)
        results_for_sheet = []
        results_for_report = []
        
        # 2. Check the status of each URL
        for i, url in enumerate(urls):
            status_label.config(text=f"3/5: Checking {i+1} of {total_urls}: {url}")
            root_window.update()
            status = check_website_status(url, session) 
            
            results_for_sheet.append([status])
            results_for_report.append({'url': url, 'status': status})
            
            time.sleep(0.5) 

        # 3. Write results back to the sheet
        if results_for_sheet:
            status_label.config(text="4/5: Writing results back to Google Sheet...")
            root_window.update()
            start_row = int(URL_RANGE[1:].split(':')[0]) 
            range_to_update = f"{STATUS_COLUMN}{start_row}:{STATUS_COLUMN}{start_row + len(results_for_sheet) - 1}"
            worksheet.update(range_to_update, results_for_sheet)
            
            # 4. Generate the HTML Report (Interface)
            status_label.config(text="5/5: Generating HTML Report Interface...")
            root_window.update()
            report_filename = generate_html_report(results_for_report)
            
            if report_filename:
                messagebox.showinfo("Scan Complete", 
                                    f"Scan finished successfully!\n\nResults saved to Google Sheet.\nInteractive Report file created: {report_filename}\n\nDouble-click the HTML file to view.")
        else:
            messagebox.showinfo("Scan Complete", "No results were processed.")
        
        session.close() 

    except Exception as e:
        messagebox.showerror("Runtime Error", f"An unexpected error occurred during the scan: {e}")
        
    finally:
        scan_button.config(state=tk.NORMAL, text="Start Scan")
        status_label.config(text="Ready to scan again.")
        root_window.update()

# --- NEW GUI SETUP ---
def main():
    root = tk.Tk()
    root.title("Python Website Scanner")
    root.geometry("450x200")
    root.resizable(False, False)

    # Styling and Layout
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(expand=True, fill='both')

    # Title
    title_label = tk.Label(main_frame, text="Google Sheet Website Monitor (Python)", font=("Inter", 12, "bold"))
    title_label.pack(pady=(0, 10))

    # Status Label
    status_label = tk.Label(main_frame, text="Ready. Click 'Start Scan' to begin.", fg="gray")
    status_label.pack(pady=(5, 15))

    # Scan Button
    scan_button = tk.Button(main_frame, text="Start Scan", command=lambda: start_scan_and_report(root, status_label, scan_button), 
                            bg="#4f46e5", fg="white", font=("Inter", 11, "bold"), height=2)
    scan_button.pack(fill='x', padx=50)

    # Note
    note_label = tk.Label(main_frame, text="Uses service_account.json. Do not close this window during scan.", font=("Inter", 8))
    note_label.pack(pady=(10, 0))

    root.mainloop()

if __name__ == '__main__':
    main()

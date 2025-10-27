from PyInstaller.utils.hooks import collect_data_files

# This tells PyInstaller to collect the 'data' directory (which contains 
# public_suffix_list.dat) from the 'whois' module and bundle it.
# This fixes the FileNotFoundError you encountered.
datas = collect_data_files('whois')
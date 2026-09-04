import os
import sys
import webbrowser
from django.core.management import execute_from_command_line

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billmanageement.settings')
    
    # Run migrations
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Start the server
    port = 8000
    webbrowser.open(f'http://127.0.0.1:{port}')
    execute_from_command_line(['manage.py', 'runserver', f'127.0.0.1:{port}'])

if __name__ == '__main__':
    main() 
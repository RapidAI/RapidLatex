#!/usr/bin/env python
"""
Script to run translate_arxiv.py with proper path setup
"""
import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import and run the main function
from translate_arxiv import main

if __name__ == "__main__":
    # Pass command line arguments to main function
    if len(sys.argv) < 2:
        print("Usage: python run_arxiv.py <arxiv_id>")
        sys.exit(1)

    main(sys.argv[1:])
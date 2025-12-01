"""
Damage Lab ADK Web Runner
=========================
Run the Damage Lab agent with Google ADK's web interface.

Usage:
    # Option 1: Using ADK CLI
    adk web damage_lab_agent
    
    # Option 2: Direct Python execution
    python adk_runner.py
    
    # Option 3: With custom port
    adk web damage_lab_agent --port 8080

The web interface will be available at http://localhost:8000 (or your specified port).
"""

import os
import sys

# Ensure the module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point for ADK web interface."""
    try:
        from google.adk.cli import main as adk_main
        
        # Set default arguments for web interface
        if len(sys.argv) == 1:
            sys.argv = ["adk", "web", "damage_lab_agent"]
        
        adk_main()
        
    except ImportError as e:
        print("Error: Google ADK not installed.")
        print("Install with: pip install google-adk")
        print(f"\nDetails: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting ADK web interface: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

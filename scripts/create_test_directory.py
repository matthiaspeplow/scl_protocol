#!/usr/bin/env python3
"""
Create P99 test directory on LED controller.

This script creates a test directory (P99) on the LED controller's A: drive
for safe testing without affecting production directory (P00).

Usage:
    python3 scripts/create_test_directory.py [--ip IP] [--port PORT] [--name NAME]
    
Examples:
    # Use default settings from environment
    python3 scripts/create_test_directory.py
    
    # Specify controller IP
    python3 scripts/create_test_directory.py --ip 172.31.16.25
    
    # Create different test directory
    python3 scripts/create_test_directory.py --name P98
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scl_protocol import SCLController, SCLControllerError


def main():
    parser = argparse.ArgumentParser(
        description="Create test directory on LED controller"
    )
    parser.add_argument(
        "--ip",
        default="172.31.16.25",
        help="Controller IP address (default: 172.31.16.25)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1024,
        help="Controller port (default: 1024)"
    )
    parser.add_argument(
        "--name",
        default="P99",
        help="Test directory name, max 3 chars (default: P99)"
    )
    parser.add_argument(
        "--driver",
        default="A",
        choices=["A", "B", "C"],
        help="Drive letter (default: A)"
    )
    
    args = parser.parse_args()
    
    # Validate directory name
    if len(args.name) > 3:
        print(f"✗ Error: Directory name '{args.name}' too long (max 3 characters)")
        return 1
    
    print("=" * 70)
    print("LED Controller Test Directory Setup")
    print("=" * 70)
    print(f"Controller: {args.ip}:{args.port}")
    print(f"Directory:  {args.driver}:/{args.name}")
    print()
    
    try:
        with SCLController(args.ip, port=args.port, scl2008=True, timeout=5.0) as controller:
            # Check if directory already exists
            print("Checking existing directories...")
            files = controller.list_files(args.driver, '')
            dirs = [f for f in files if f['is_dir']]
            
            print(f"Found {len(dirs)} directories on {args.driver}:")
            for d in dirs:
                marker = " ← TEST DIR" if d['name'] == args.name else ""
                print(f"  - {d['name']}{marker}")
            
            dir_exists = any(d['name'] == args.name for d in dirs)
            
            if dir_exists:
                print(f"\n✓ Directory {args.name} already exists")
                
                # List contents
                contents = controller.list_files(args.driver, args.name)
                print(f"  Contains {len(contents)} items:")
                for item in contents[:10]:  # Show first 10
                    icon = "📁" if item['is_dir'] else "📄"
                    print(f"    {icon} {item['name']} ({item['size']} bytes)")
                if len(contents) > 10:
                    print(f"    ... and {len(contents) - 10} more")
                    
            else:
                print(f"\nCreating {args.name} directory...")
                controller.create_subdirectory(args.name, args.driver)
                print(f"✓ Successfully created {args.driver}:/{args.name}")
                
                # Verify
                files = controller.list_files(args.driver, '')
                dirs = [f for f in files if f['is_dir']]
                if any(d['name'] == args.name for d in dirs):
                    print(f"✓ Verified: {args.name} is accessible")
                else:
                    print(f"⚠ Warning: Could not verify {args.name} creation")
        
        print()
        print("=" * 70)
        print("✓ Setup complete")
        print()
        print("You can now safely test uploads to this directory:")
        print(f"  remote_path = '{args.name}/test_file.png'")
        print(f"  controller.upload_file('local.png', '{args.driver}', remote_path)")
        
        return 0
        
    except SCLControllerError as e:
        print(f"\n✗ Controller error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

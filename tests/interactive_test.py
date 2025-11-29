#!/usr/bin/env python3
"""
Interactive test script for SCL Protocol module.

This script provides a menu-driven interface to test all functionality
of the SCL Protocol library, including connection, file operations,
and image conversion.

Usage:
    python interactive_test.py
"""

import sys
import os
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scl_protocol import (
    SCLController,
    SCLProtocolError,
    SCLControllerError,
    SCLConnectionError,
    SCLTimeoutError,
    ImageConversionError,
    convert_to_xmp,
    needs_conversion,
    DRIVER_NAMES,
    DEFAULT_UDP_PORT,
)


class InteractiveTest:
    """Interactive test interface for SCL Protocol."""
    
    def __init__(self):
        self.controller_ip = None
        self.controller_port = DEFAULT_UDP_PORT
        self.protocol = 'scl2008'
        self.timeout = 5.0
        self.controller = None
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def print_header(self, title):
        """Print a formatted section header."""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def print_separator(self):
        """Print a separator line."""
        print("-" * 70)
    
    def format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def format_datetime(self, entry):
        """Format directory entry date/time."""
        return (f"{entry['year']:04d}-{entry['month']:02d}-{entry['day']:02d} "
                f"{entry['hour']:02d}:{entry['minute']:02d}:{entry['second']:02d}")
    
    def get_input(self, prompt, default=None):
        """Get user input with optional default value."""
        if default is not None:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        return value
    
    def setup_connection(self):
        """Prompt for connection parameters."""
        self.print_header("Connection Setup")
        
        print("Enter controller connection details:\n")
        
        self.controller_ip = self.get_input("Controller IP address", self.controller_ip)
        
        port_str = self.get_input(f"Controller port", str(self.controller_port))
        try:
            self.controller_port = int(port_str)
        except ValueError:
            print(f"Invalid port, using default: {DEFAULT_UDP_PORT}")
            self.controller_port = DEFAULT_UDP_PORT
        
        protocol = self.get_input("Protocol (scl2008/supercomm)", self.protocol)
        if protocol.lower() in ['scl2008', 'supercomm']:
            self.protocol = protocol.lower()
        
        timeout_str = self.get_input(f"Timeout in seconds", str(self.timeout))
        try:
            self.timeout = float(timeout_str)
        except ValueError:
            print(f"Invalid timeout, using default: {self.timeout}")
        
        print(f"\n✓ Connection parameters set:")
        print(f"  IP: {self.controller_ip}")
        print(f"  Port: {self.controller_port}")
        print(f"  Protocol: {self.protocol}")
        print(f"  Timeout: {self.timeout}s")
        
        input("\nPress Enter to continue...")
    
    def test_connection(self):
        """Test basic connection to the controller."""
        self.print_header("Test Connection")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        print(f"Testing connection to {self.controller_ip}:{self.controller_port}...")
        
        try:
            scl2008 = (self.protocol == 'scl2008')
            with SCLController(self.controller_ip, self.controller_port, 
                             scl2008, self.timeout) as controller:
                print("✓ Socket created successfully")
                print("✓ Connection established")
                
                # Try to get status
                status = controller.check_status()
                print("✓ Controller responding")
                
            print("\n✓ Connection test successful!")
            
        except SCLConnectionError as e:
            print(f"\n❌ Connection failed: {e}")
        except SCLTimeoutError as e:
            print(f"\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n❌ Controller error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def check_status(self):
        """Check controller status."""
        self.print_header("Check Controller Status")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        try:
            scl2008 = (self.protocol == 'scl2008')
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                print(f"Querying controller at {self.controller_ip}...\n")
                
                # Get status
                status = controller.check_status()
                print("Controller Status:")
                print(f"  Connected: {status.get('connected', 'Unknown')}")
                print(f"  Data size: {status.get('data_size', 0)} bytes")
                
                if 'parse_error' in status:
                    print(f"  Warning: {status['parse_error']}")
                
                # Get free space for each driver
                print("\nDisk Space:")
                for driver in ['A', 'B', 'C']:
                    try:
                        free = controller.get_free_space(driver)
                        print(f"  Driver {driver}: {self.format_size(free)} free")
                    except SCLControllerError:
                        print(f"  Driver {driver}: Not available")
                
                print("\n✓ Status check successful")
                
        except SCLTimeoutError as e:
            print(f"\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n❌ Error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def list_files(self):
        """List files on controller."""
        self.print_header("List Files")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        print("Enter parameters:\n")
        driver = self.get_input("Driver (A/B/C)", "A").upper()
        if driver not in ['A', 'B', 'C']:
            print("Invalid driver. Using A.")
            driver = 'A'
        
        subdir = self.get_input("Subdirectory (max 3 chars, leave empty for root)", "")
        if len(subdir) > 3:
            print("Warning: Subdirectory name truncated to 3 characters")
            subdir = subdir[:3]
        
        try:
            scl2008 = (self.protocol == 'scl2008')
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                print(f"\nListing files on driver {driver}" +
                      (f" in subdirectory '{subdir}'" if subdir else ""))
                print()
                
                files = controller.list_files(driver, subdir)
                
                if not files:
                    print("No files found.")
                else:
                    # Print table header
                    print(f"{'Name':<20} {'Size':>12} {'Type':>6} {'Date/Time':<20}")
                    self.print_separator()
                    
                    # Sort: directories first, then by name
                    files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
                    
                    # Print files
                    file_count = 0
                    dir_count = 0
                    total_size = 0
                    
                    for entry in files:
                        name = entry['name'][:20]
                        file_type = "DIR" if entry['is_dir'] else "FILE"
                        
                        if entry['is_dir']:
                            size_str = ""
                            dir_count += 1
                        else:
                            size_str = self.format_size(entry['size'])
                            total_size += entry['size']
                            file_count += 1
                        
                        datetime_str = self.format_datetime(entry)
                        
                        print(f"{name:<20} {size_str:>12} {file_type:>6} {datetime_str:<20}")
                    
                    # Summary
                    self.print_separator()
                    print(f"{file_count} file(s), {dir_count} directory(ies), "
                          f"total size: {self.format_size(total_size)}")
                
                print("\n✓ File listing successful")
                
        except SCLTimeoutError as e:
            print(f"\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n❌ Error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def upload_file(self):
        """Upload file to controller."""
        self.print_header("Upload File")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        print("Enter parameters:\n")
        local_file = self.get_input("Local file path")
        
        if not local_file or not Path(local_file).exists():
            print(f"❌ File not found: {local_file}")
            input("\nPress Enter to continue...")
            return
        
        driver = self.get_input("Destination driver (A/B/C)", "A").upper()
        if driver not in ['A', 'B', 'C']:
            print("Invalid driver. Using A.")
            driver = 'A'
        
        local_path = Path(local_file)
        
        # Check if conversion will occur
        will_convert = needs_conversion(str(local_path))
        default_remote = local_path.stem + '.xmp' if will_convert else local_path.name
        
        remote_name = self.get_input(f"Remote filename", default_remote)
        
        pause = self.get_input("Pause controller during upload? (y/n)", "n").lower() == 'y'
        
        print(f"\nUploading: {local_file}")
        if will_convert:
            print("Note: Converting monochrome image to XMP format")
        print(f"       To: Driver {driver}:{remote_name}")
        print(f"   Target: {self.controller_ip}:{self.controller_port}")
        
        try:
            file_size = local_path.stat().st_size
            print(f"\nOriginal file size: {self.format_size(file_size)}")
            
            if pause:
                print("Will pause controller during upload")
            
            print("\nUploading...", end='', flush=True)
            
            scl2008 = (self.protocol == 'scl2008')
            start_time = time.time()
            
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                controller.upload_file(
                    str(local_path),
                    driver,
                    remote_name,
                    pause_controller=pause
                )
            
            elapsed = time.time() - start_time
            speed = file_size / elapsed if elapsed > 0 else 0
            
            print(" Done!")
            print(f"\n✓ Upload successful!")
            print(f"  Time elapsed: {elapsed:.2f} seconds")
            print(f"  Transfer speed: {self.format_size(speed)}/s")
            
        except SCLTimeoutError as e:
            print(f"\n\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n\n❌ Error: {e}")
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def download_file(self):
        """Download file from controller."""
        self.print_header("Download File")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        print("Enter parameters:\n")
        remote_file = self.get_input("Remote filename")
        
        driver = self.get_input("Source driver (A/B/C)", "A").upper()
        if driver not in ['A', 'B', 'C']:
            print("Invalid driver. Using A.")
            driver = 'A'
        
        local_path = self.get_input("Local destination path", remote_file)
        
        print(f"\nDownloading: Driver {driver}:{remote_file}")
        print(f"         To: {local_path}")
        print(f"     Target: {self.controller_ip}:{self.controller_port}")
        
        try:
            print("\nDownloading...", end='', flush=True)
            
            scl2008 = (self.protocol == 'scl2008')
            start_time = time.time()
            
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                controller.download_file(remote_file, local_path, driver)
            
            elapsed = time.time() - start_time
            downloaded_size = Path(local_path).stat().st_size
            speed = downloaded_size / elapsed if elapsed > 0 else 0
            
            print(" Done!")
            print(f"\n✓ Download successful!")
            print(f"  Downloaded: {self.format_size(downloaded_size)}")
            print(f"  Time elapsed: {elapsed:.2f} seconds")
            print(f"  Transfer speed: {self.format_size(speed)}/s")
            
        except SCLTimeoutError as e:
            print(f"\n\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n\n❌ Error: {e}")
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def download_directory(self):
        """Download directory from controller."""
        self.print_header("Download Directory")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        print("Enter parameters:\n")
        
        driver = self.get_input("Source driver (A/B/C)", "A").upper()
        if driver not in ['A', 'B', 'C']:
            print("Invalid driver. Using A.")
            driver = 'A'
        
        remote_dir = self.get_input("Remote directory (max 3 chars, empty for root)", "")
        if len(remote_dir) > 3:
            print("Warning: Directory name truncated to 3 characters")
            remote_dir = remote_dir[:3]
        
        local_dir = self.get_input("Local destination directory", "./download")
        
        print(f"\nDownloading directory: Driver {driver}:{remote_dir or '(root)'}")
        print(f"                   To: {local_dir}")
        print(f"               Target: {self.controller_ip}:{self.controller_port}")
        
        try:
            print("\nFetching file list...", end='', flush=True)
            
            scl2008 = (self.protocol == 'scl2008')
            
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                downloaded = controller.download_directory(
                    remote_dir,
                    local_dir,
                    driver
                )
            
            print(" Done!")
            print(f"\n✓ Downloaded {downloaded} file(s) successfully")
            
        except SCLTimeoutError as e:
            print(f"\n\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n\n❌ Error: {e}")
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def get_free_space(self):
        """Get free space on controller disk."""
        self.print_header("Get Free Space")
        
        if not self.controller_ip:
            print("❌ No IP address configured. Please setup connection first.")
            input("\nPress Enter to continue...")
            return
        
        driver = self.get_input("Driver (A/B/C)", "A").upper()
        if driver not in ['A', 'B', 'C']:
            print("Invalid driver. Using A.")
            driver = 'A'
        
        try:
            scl2008 = (self.protocol == 'scl2008')
            with SCLController(self.controller_ip, self.controller_port,
                             scl2008, self.timeout) as controller:
                print(f"\nQuerying driver {driver}...")
                
                free = controller.get_free_space(driver)
                
                print(f"\n✓ Driver {driver} free space: {self.format_size(free)}")
                
        except SCLTimeoutError as e:
            print(f"\n❌ Timeout: {e}")
        except SCLControllerError as e:
            print(f"\n❌ Error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def test_image_conversion(self):
        """Test image conversion without uploading."""
        self.print_header("Test Image Conversion")
        
        print("This test converts an image to XMP format locally (no upload).\n")
        
        image_file = self.get_input("Image file path (BMP/GIF/PNG)")
        
        if not image_file or not Path(image_file).exists():
            print(f"❌ File not found: {image_file}")
            input("\nPress Enter to continue...")
            return
        
        if not needs_conversion(image_file):
            print(f"❌ File does not need conversion (not BMP/GIF/PNG)")
            input("\nPress Enter to continue...")
            return
        
        output_file = self.get_input("Output XMP file path", 
                                     Path(image_file).stem + ".xmp")
        
        print("\nXMP Type:")
        print("  1. Type 1 (4-color grayscale, 2 bits/pixel) - Default")
        print("  2. Type 2 (monochrome, 1 bit/pixel)")
        xmp_type_str = self.get_input("Select XMP type (1/2)", "1")
        xmp_type = 1 if xmp_type_str == "1" else 2
        
        print(f"\nConverting: {image_file}")
        print(f"        To: {output_file}")
        print(f"  XMP Type: {xmp_type} ({'4-color grayscale' if xmp_type == 1 else 'monochrome'})")
        
        try:
            print("\nConverting...", end='', flush=True)
            
            converted_path, is_temp = convert_to_xmp(image_file, output_file, xmp_type)
            
            print(" Done!")
            
            input_size = Path(image_file).stat().st_size
            output_size = Path(converted_path).stat().st_size
            
            print(f"\n✓ Conversion successful!")
            print(f"  Input size:  {self.format_size(input_size)}")
            print(f"  Output size: {self.format_size(output_size)}")
            print(f"  Output file: {converted_path}")
            print(f"  XMP Type:    Type {xmp_type}")
            
        except ImageConversionError as e:
            print(f"\n\n❌ Conversion error: {e}")
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
        
        input("\nPress Enter to continue...")
    
    def show_menu(self):
        """Display the main menu."""
        self.clear_screen()
        self.print_header("SCL Protocol - Interactive Test")
        
        print("\nConnection:")
        if self.controller_ip:
            print(f"  IP: {self.controller_ip}:{self.controller_port}")
            print(f"  Protocol: {self.protocol}")
            print(f"  Timeout: {self.timeout}s")
        else:
            print("  Not configured")
        
        print("\nMenu:")
        print("  1. Setup Connection")
        print("  2. Test Connection")
        print("  3. Check Controller Status")
        print("  4. List Files")
        print("  5. Upload File")
        print("  6. Download File")
        print("  7. Download Directory")
        print("  8. Get Free Space")
        print("  9. Test Image Conversion (offline)")
        print("  0. Exit")
        print()
    
    def run(self):
        """Run the interactive test loop."""
        while True:
            self.show_menu()
            choice = input("Enter choice: ").strip()
            
            if choice == '1':
                self.setup_connection()
            elif choice == '2':
                self.test_connection()
            elif choice == '3':
                self.check_status()
            elif choice == '4':
                self.list_files()
            elif choice == '5':
                self.upload_file()
            elif choice == '6':
                self.download_file()
            elif choice == '7':
                self.download_directory()
            elif choice == '8':
                self.get_free_space()
            elif choice == '9':
                self.test_image_conversion()
            elif choice == '0':
                print("\nExiting... Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
                input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    print("=" * 70)
    print("  SCL Protocol - Interactive Test Script")
    print("=" * 70)
    print("\nThis script allows you to interactively test all functionality")
    print("of the SCL Protocol library.")
    print("\nPress Ctrl+C at any time to exit.")
    print()
    
    try:
        test = InteractiveTest()
        test.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        return 0
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

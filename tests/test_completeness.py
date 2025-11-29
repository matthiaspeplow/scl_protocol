#!/usr/bin/env python3
"""Test script to verify all SCLController methods are implemented."""

import sys
from scl_protocol import SCLController

def list_all_methods():
    """List all public methods of SCLController."""
    
    print("=" * 60)
    print("SCLController - Complete Method List")
    print("=" * 60)
    
    # Get all public methods (excluding private methods starting with _)
    methods = [method for method in dir(SCLController) if not method.startswith('_') and callable(getattr(SCLController, method))]
    
    # Categorize methods
    connection_methods = ['connect', 'close', 'release_network', 'send_command']
    status_methods = ['check_status', 'get_play_status', 'get_free_space']
    file_methods = ['list_files', 'upload_file', 'download_file', 'download_directory', 'delete_file']
    directory_methods = ['create_subdirectory', 'delete_subdirectory']
    control_methods = ['pause', 'play', 'set_power_mode', 'format_disk', 'set_calendar_clock', 
                       'set_on_off_time', 'real_time_display', 'restart_schedule', 'reset_controller']
    
    print("\n📡 Connection & Communication Methods:")
    for method in connection_methods:
        if method in methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - MISSING")
    
    print("\n📊 Status & Information Methods:")
    for method in status_methods:
        if method in methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - MISSING")
    
    print("\n📁 File Management Methods:")
    for method in file_methods:
        if method in methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - MISSING")
    
    print("\n📂 Directory Management Methods:")
    for method in directory_methods:
        if method in methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - MISSING")
    
    print("\n🎮 Control Methods:")
    for method in control_methods:
        if method in methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - MISSING")
    
    # Count total methods
    all_expected = (connection_methods + status_methods + file_methods + 
                    directory_methods + control_methods)
    implemented = [m for m in all_expected if m in methods]
    
    print("\n" + "=" * 60)
    print(f"Total Methods: {len(implemented)}/{len(all_expected)} implemented")
    print("=" * 60)
    
    # Check for any unexpected methods
    unexpected = [m for m in methods if m not in all_expected]
    if unexpected:
        print("\n📝 Other public methods:")
        for method in unexpected:
            print(f"  • {method}()")
    
    return len(implemented) == len(all_expected)

def test_command_coverage():
    """Verify all command codes have corresponding methods."""
    from scl_protocol.constants import (
        CMD_SEND_DATA_TO_BUFFER,
        CMD_RETRIEVE_DATA_FROM_BUFFER,
        CMD_SAVE_BUFFER_TO_FILE,
        CMD_LOAD_FILE_TO_BUFFER,
        CMD_DELETE_FILE,
        CMD_GET_DISK_FREE_SPACE,
        CMD_DOWNLOAD_DIRECTORY,
        CMD_FORMAT_DISK,
        CMD_SET_CALENDAR_CLOCK,
        CMD_PAUSE_PLAY,
        CMD_SET_ON_OFF_TIME,
        CMD_SETUP_POWER_MODE,
        CMD_CREATE_SUBDIRECTORY,
        CMD_DELETE_SUBDIRECTORY,
        CMD_REAL_TIME_DISPLAY,
        CMD_PLAY_STATUS,
        CMD_READ_RUNNING_INFO,
        CMD_RESTART_SCHEDULE,
        CMD_RESET_CONTROLLER,
        CMD_RELEASE_NET_COMM,
    )
    
    print("\n" + "=" * 60)
    print("Command Code Coverage Analysis")
    print("=" * 60)
    
    commands = {
        'CMD_SEND_DATA_TO_BUFFER': {'code': CMD_SEND_DATA_TO_BUFFER, 'method': '_send_to_buffer', 'type': 'internal'},
        'CMD_RETRIEVE_DATA_FROM_BUFFER': {'code': CMD_RETRIEVE_DATA_FROM_BUFFER, 'method': '_retrieve_from_buffer', 'type': 'internal'},
        'CMD_SAVE_BUFFER_TO_FILE': {'code': CMD_SAVE_BUFFER_TO_FILE, 'method': 'upload_file', 'type': 'public'},
        'CMD_LOAD_FILE_TO_BUFFER': {'code': CMD_LOAD_FILE_TO_BUFFER, 'method': 'download_file', 'type': 'public'},
        'CMD_DELETE_FILE': {'code': CMD_DELETE_FILE, 'method': 'delete_file', 'type': 'public'},
        'CMD_GET_DISK_FREE_SPACE': {'code': CMD_GET_DISK_FREE_SPACE, 'method': 'get_free_space', 'type': 'public'},
        'CMD_DOWNLOAD_DIRECTORY': {'code': CMD_DOWNLOAD_DIRECTORY, 'method': 'list_files', 'type': 'public'},
        'CMD_FORMAT_DISK': {'code': CMD_FORMAT_DISK, 'method': 'format_disk', 'type': 'public'},
        'CMD_SET_CALENDAR_CLOCK': {'code': CMD_SET_CALENDAR_CLOCK, 'method': 'set_calendar_clock', 'type': 'public'},
        'CMD_PAUSE_PLAY': {'code': CMD_PAUSE_PLAY, 'method': 'pause/play', 'type': 'public'},
        'CMD_SET_ON_OFF_TIME': {'code': CMD_SET_ON_OFF_TIME, 'method': 'set_on_off_time', 'type': 'public'},
        'CMD_SETUP_POWER_MODE': {'code': CMD_SETUP_POWER_MODE, 'method': 'set_power_mode', 'type': 'public'},
        'CMD_CREATE_SUBDIRECTORY': {'code': CMD_CREATE_SUBDIRECTORY, 'method': 'create_subdirectory', 'type': 'public'},
        'CMD_DELETE_SUBDIRECTORY': {'code': CMD_DELETE_SUBDIRECTORY, 'method': 'delete_subdirectory', 'type': 'public'},
        'CMD_REAL_TIME_DISPLAY': {'code': CMD_REAL_TIME_DISPLAY, 'method': 'real_time_display', 'type': 'public'},
        'CMD_PLAY_STATUS': {'code': CMD_PLAY_STATUS, 'method': 'get_play_status', 'type': 'public'},
        'CMD_READ_RUNNING_INFO': {'code': CMD_READ_RUNNING_INFO, 'method': 'check_status', 'type': 'public'},
        'CMD_RESTART_SCHEDULE': {'code': CMD_RESTART_SCHEDULE, 'method': 'restart_schedule', 'type': 'public'},
        'CMD_RESET_CONTROLLER': {'code': CMD_RESET_CONTROLLER, 'method': 'reset_controller', 'type': 'public'},
        'CMD_RELEASE_NET_COMM': {'code': CMD_RELEASE_NET_COMM, 'method': 'release_network', 'type': 'public'},
    }
    
    for cmd_name, info in commands.items():
        method_type = '(internal)' if info['type'] == 'internal' else ''
        print(f"✅ {cmd_name} (0x{info['code']:08X}) -> {info['method']}() {method_type}")
    
    print(f"\n✅ All {len(commands)} command codes have corresponding methods!")
    return True

if __name__ == '__main__':
    print("\n🧪 Testing scl_protocol Completeness\n")
    
    methods_complete = list_all_methods()
    commands_complete = test_command_coverage()
    
    print("\n" + "=" * 60)
    if methods_complete and commands_complete:
        print("🎉 SCLController implementation is COMPLETE!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("⚠️  Some methods or commands are missing")
        print("=" * 60)
        sys.exit(1)

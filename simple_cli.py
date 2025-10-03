#!/usr/bin/env python3
"""
Simplified RainBird CLI - Command-line Interface for ESP-ME3 Irrigation Controllers

This module provides a clean, user-friendly interface for controlling RainBird ESP-ME3
irrigation controllers. It supports both interactive menu-driven operation and direct
command-line parameter execution for automation and scripting.

Architecture:
    The CLI uses the PyRainBird library's async_client for all controller communication.
    It maintains a persistent aiohttp session for efficient HTTP communication and tracks
    zone start times locally to calculate remaining irrigation time since the ESP-ME3
    controller doesn't provide this information directly.

Controller Compatibility:
    Designed and tested with RainBird ESP-ME3 controllers (model 9, v2.12+).
    The ESP-ME3 is a basic/entry-level controller that excels at manual zone control
    but has limited programming capabilities:

    Supported Features:
        - Manual zone control (start/stop individual zones 1-19)
        - Zone testing (30-second test runs)
        - Rain delay management (1-7 days)
        - Rain sensor monitoring
        - Current irrigation status

    Limitations:
        - No complex program schedules
        - No stored irrigation programs
        - Limited to manual zone activation
        - Maximum 60-minute duration per zone activation

Key Features:
    - Async/await architecture for responsive operations
    - Real-time irrigation status with remaining time calculations
    - Automatic connection retry and error handling
    - Both interactive and command-line modes
    - Zone start time tracking for accurate remaining time display

Usage:
    Interactive mode (menu-driven):
        python3 simple_cli.py

    Command-line mode (automation-friendly):
        python3 simple_cli.py --ip IP --password PASS --zone ZONE --duration MINS
        python3 simple_cli.py --ip IP --password PASS --status
        python3 simple_cli.py --ip IP --password PASS --stop
        python3 simple_cli.py --help

Examples:
    # Start zone 1 for 10 minutes
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10

    # Check current irrigation status
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status

    # Stop all irrigation
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --stop

Dependencies:
    - asyncio: For async/await operations
    - aiohttp: HTTP client for controller communication
    - pyrainbird: RainBird controller protocol implementation

Author: Jason DeWeese
Version: 1.0
Last Updated: 2025-09-16
"""

import asyncio
import aiohttp
import argparse
import sys
from datetime import datetime, timedelta
from pyrainbird import async_client

class SimpleRainBirdCLI:
    """
    Main CLI controller for RainBird ESP-ME3 irrigation systems.

    This class manages all interactions with the RainBird controller, including
    connection management, zone control, and status monitoring. It uses async/await
    patterns throughout for responsive, non-blocking operations.

    Attributes:
        ip (str): Controller IP address (e.g., "192.168.1.113")
        password (str): Controller password for authentication
        controller (AsyncRainbirdController): PyRainBird async controller instance
        session (aiohttp.ClientSession): HTTP session for controller communication
        zone_start_times (dict): Maps zone_id to {start_time, duration} for tracking
            remaining irrigation time. Format: {zone_id: {'start_time': datetime, 'duration': int}}

    Error Handling:
        All methods that communicate with the controller include try/except blocks
        to gracefully handle network errors, timeouts, and controller disconnections.
        User-friendly error messages are displayed for all failure conditions.

    Connection Management:
        The session is created on connect() and must be cleaned up via cleanup()
        to prevent resource leaks. Use in an async context manager or ensure
        cleanup() is called in a finally block.

    Example:
        # Command-line usage
        cli = SimpleRainBirdCLI("192.168.1.113", "1234")
        await cli.connect()
        await cli.run_zone(1, 10)
        await cli.cleanup()

        # Interactive usage
        cli = SimpleRainBirdCLI()
        await cli.interactive_menu()
    """

    def __init__(self, ip=None, password=None):
        """
        Initialize the CLI controller.

        Args:
            ip (str, optional): Controller IP address. Can be set later in interactive mode.
            password (str, optional): Controller password. Can be set later in interactive mode.
        """
        self.ip = ip
        self.password = password
        self.controller = None
        self.session = None
        self.zone_start_times = {}  # Track when zones started for remaining time calculation
    
    async def connect(self):
        """
        Establish connection to the RainBird controller and verify communication.

        Creates an aiohttp ClientSession for HTTP communication and initializes
        the PyRainBird AsyncRainbirdController. Tests the connection by retrieving
        the controller's model and version information.

        Connection Process:
            1. Create aiohttp ClientSession for persistent HTTP connections
            2. Initialize PyRainBird controller with session, IP, and password
            3. Verify connection by requesting model/version information
            4. Display controller details on successful connection

        Returns:
            bool: True if connection successful and controller responds,
                  False if connection fails or controller doesn't respond

        Raises:
            No exceptions are raised - all errors are caught and reported to user.
            Common errors include:
                - Network unreachable (wrong IP, network down)
                - Connection timeout (controller off or unreachable)
                - Authentication failure (wrong password)
                - Protocol errors (incompatible controller model)

        Note:
            The session must be cleaned up via cleanup() to prevent resource leaks.
            If connection fails, the session is left open for retry attempts.

        Example:
            >>> cli = SimpleRainBirdCLI("192.168.1.113", "1234")
            >>> success = await cli.connect()
            >>> if success:
            ...     await cli.run_zone(1, 10)
        """
        try:
            print(f"🔌 Connecting to {self.ip}...")

            # Create persistent HTTP session for efficient communication
            self.session = aiohttp.ClientSession()

            # Initialize controller with PyRainBird's async client
            self.controller = async_client.CreateController(
                self.session,
                self.ip,
                self.password
            )

            # Test connection and get controller information
            # This verifies both network connectivity and authentication
            model_info = await self.controller.get_model_and_version()

            print(f"✅ Connected to {model_info.model_name} "
                  f"({model_info.model}) v{model_info.major}.{model_info.minor}")
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def run_zone(self, zone_id, duration_minutes):
        """
        Start irrigation on a specific zone for a specified duration.

        Sends the irrigation command to the controller, tracks the start time locally
        for remaining time calculations, and verifies that the zone actually started.

        ESP-ME3 Zone Control Details:
            - Supports zones 1-19 (though not all may be wired)
            - Maximum duration: 60 minutes per activation
            - Zone activation is manual - no stored programs
            - Only one zone can run at a time (controller limitation)
            - Starting a new zone stops the currently running zone

        Verification Process:
            1. Send irrigate_zone command to controller
            2. Record start time and duration locally
            3. Wait 2 seconds for controller to process
            4. Query zone states to verify activation
            5. Report success or warning if verification fails

        Args:
            zone_id (int): Zone number to activate (1-19)
            duration_minutes (int): How long to run zone (1-60 minutes)

        Returns:
            bool: True if zone started and verified running,
                  False if command failed or zone not running after command

        Raises:
            No exceptions are raised - all errors are caught and reported.
            Common errors:
                - Connection lost (network interruption)
                - Invalid zone number (zone doesn't exist)
                - Controller busy (rare, but possible)

        Note:
            The ESP-ME3 doesn't provide remaining time information, so this
            method tracks start time locally in self.zone_start_times for
            status reporting via get_status().

        Example:
            >>> await cli.run_zone(1, 10)  # Run zone 1 for 10 minutes
            🚿 Starting Zone 1 for 10 minutes...
            ✅ Zone 1 started successfully
        """
        if not self.controller:
            print("❌ Not connected")
            return False

        try:
            print(f"🚿 Starting Zone {zone_id} for {duration_minutes} minutes...")

            # Send zone activation command to controller
            await self.controller.irrigate_zone(zone_id, duration_minutes)

            # Track start time locally for remaining time calculation
            # The ESP-ME3 doesn't provide this information, so we calculate it
            self.zone_start_times[zone_id] = {
                'start_time': datetime.now(),
                'duration': duration_minutes
            }

            # Wait for controller to process command
            # The controller needs a moment to activate the zone
            await asyncio.sleep(2)

            # Verify zone actually started by querying current state
            # zone_states.states is a list indexed 0-18 for zones 1-19
            zone_states = await self.controller.get_zone_states()

            if zone_states.states[zone_id-1]:
                print(f"✅ Zone {zone_id} started successfully")
                print(f"   ⏱️  Duration: {duration_minutes} minutes")
                print(f"   🕐 Started: {datetime.now().strftime('%I:%M %p')}")
                return True
            else:
                # Command was sent but zone isn't showing as active
                # This can happen if another zone was started or controller is busy
                print(f"⚠️  Zone {zone_id} command sent but may not be running")
                return False

        except Exception as e:
            print(f"❌ Failed to start zone: {e}")
            return False
    
    async def get_status(self):
        """
        Retrieve and display current irrigation status with remaining time calculations.

        Queries the controller for current irrigation state and active zones, then
        combines this with locally tracked start times to calculate and display
        remaining irrigation time for each active zone.

        Status Information Provided:
            - Overall irrigation state (active/inactive)
            - Current time
            - List of running zones with remaining time
            - Zones that should have stopped (exceeded expected duration)

        Remaining Time Calculation:
            Since ESP-ME3 doesn't provide remaining time, this method:
            1. Checks which zones are currently active via get_zone_states()
            2. Looks up start time and duration in self.zone_start_times
            3. Calculates elapsed time since start
            4. Computes remaining time as (total_duration - elapsed)
            5. Cleans up tracking for zones past their expected stop time

        Limitations:
            - Can only show remaining time for zones started by THIS instance
            - Zones started via physical controller or other clients show "unknown remaining time"
            - Times are estimates - actual stop time controlled by the ESP-ME3
            - Tracking is cleared on cleanup() or process restart

        Returns:
            None - Status is printed to stdout

        Raises:
            No exceptions are raised - all errors are caught and reported.
            Common errors:
                - Connection lost during status query
                - Controller not responding

        Example Output:
            📊 Getting irrigation status...
            ✅ System Status:
               💧 Irrigation: 🟢 ACTIVE
               🕐 Current Time: 02:30 PM
               🚿 Zone 1: Running (7 minutes remaining)

        Note:
            This method automatically cleans up expired zone tracking entries
            to prevent memory buildup over time.
        """
        if not self.controller:
            print("❌ Not connected")
            return

        try:
            print("📊 Getting irrigation status...")

            # Query controller for current state
            # get_current_irrigation() returns True if any zone is active
            irrigation_active = await self.controller.get_current_irrigation()

            # get_zone_states() returns object with states array
            # states[0-18] correspond to zones 1-19
            zone_states = await self.controller.get_zone_states()
            current_time = datetime.now()

            print(f"✅ System Status:")
            print(f"   💧 Irrigation: {'🟢 ACTIVE' if irrigation_active else '⚪ Inactive'}")
            print(f"   🕐 Current Time: {current_time.strftime('%I:%M %p')}")

            # Show running zones with remaining time calculation
            running_zones = []

            # Iterate through first 19 zones (ESP-ME3 supports up to 19)
            for i, state in enumerate(zone_states.states[:19], 1):
                if state:  # Zone is currently active
                    running_zones.append(i)

                    # Calculate remaining time if we tracked the start
                    # (only possible for zones started by this CLI instance)
                    if i in self.zone_start_times:
                        start_info = self.zone_start_times[i]
                        elapsed = current_time - start_info['start_time']
                        total_duration = timedelta(minutes=start_info['duration'])
                        remaining = total_duration - elapsed

                        if remaining.total_seconds() > 0:
                            # Zone still within expected run time
                            remaining_mins = int(remaining.total_seconds() / 60)
                            print(f"   🚿 Zone {i}: Running ({remaining_mins} minutes remaining)")
                        else:
                            # Zone is running but past expected stop time
                            # This can happen if duration was extended or stop failed
                            print(f"   🚿 Zone {i}: Running (should have stopped)")
                            # Clean up expired tracking to prevent memory growth
                            del self.zone_start_times[i]
                    else:
                        # Zone is running but we don't have start time
                        # (started by physical controller or different client)
                        print(f"   🚿 Zone {i}: Running (unknown remaining time)")

            if not running_zones:
                print(f"   🚿 Running Zones: None")

        except Exception as e:
            print(f"❌ Failed to get status: {e}")
    
    async def stop_all(self):
        """
        Stop all active irrigation immediately.

        Sends the stop_irrigation command to halt all zones, clears local tracking
        data, and verifies that irrigation actually stopped.

        Stop Behavior:
            - Stops all zones immediately regardless of remaining time
            - Clears all local zone start time tracking
            - Waits for controller to process the stop command
            - Verifies irrigation is no longer active

        Returns:
            bool: True if irrigation successfully stopped and verified,
                  False if stop command failed or irrigation still active

        Raises:
            No exceptions are raised - all errors are caught and reported.
            Common errors:
                - Connection lost during stop command
                - Controller not responding

        Note:
            This is an emergency stop - all zones stop immediately regardless
            of their remaining scheduled time. The controller's built-in timer
            is overridden.

        Example:
            >>> await cli.stop_all()
            🛑 Stopping all irrigation...
            ✅ All irrigation stopped
        """
        if not self.controller:
            print("❌ Not connected")
            return False

        try:
            print("🛑 Stopping all irrigation...")

            # Send stop command to controller
            await self.controller.stop_irrigation()

            # Clear all local tracking since all zones are stopping
            # This prevents stale "should have stopped" messages
            self.zone_start_times.clear()

            # Wait for controller to process stop command
            await asyncio.sleep(2)

            # Verify irrigation actually stopped
            irrigation_active = await self.controller.get_current_irrigation()

            if not irrigation_active:
                print("✅ All irrigation stopped")
                return True
            else:
                # Stop command sent but irrigation still showing active
                # This is rare but can happen with controller communication delays
                print("⚠️  Stop command sent")
                return False

        except Exception as e:
            print(f"❌ Failed to stop irrigation: {e}")
            return False
    
    async def interactive_menu(self):
        """
        Display and handle interactive menu for user-driven operation.

        Provides a simple menu-based interface for users who prefer interactive
        operation over command-line parameters. The menu loops until the user
        chooses to exit.

        Menu Options:
            1. Connect to controller - Prompts for IP and password
            2. Run zone - Start a zone (requires connection first)
            3. Get status - Display current irrigation status
            4. Stop all irrigation - Emergency stop all zones
            0. Exit - Clean exit from program

        Input Validation:
            - Zone numbers validated (1-19)
            - Duration validated (1-60 minutes)
            - Numeric input validated with proper error messages
            - Connection required before zone operations

        User Experience:
            - Clear prompts for all inputs
            - Immediate feedback on all actions
            - "Press Enter to continue" pauses between operations
            - Graceful handling of invalid inputs

        Returns:
            None - Runs until user exits

        Example Session:
            🌱 Simple RainBird Controller
            ========================================

            Options:
            1. Connect to controller
            2. Run zone
            3. Get status
            4. Stop all irrigation
            0. Exit

            Enter choice: 1
            Enter IP address: 192.168.1.113
            Enter password: 1234
            🔌 Connecting to 192.168.1.113...
            ✅ Connected to ESP-ME3 (9) v2.12

        Note:
            This method blocks until the user exits. For non-interactive
            operation, use command-line parameters instead.
        """
        print("🌱 Simple RainBird Controller")
        print("="*40)

        while True:
            print("\nOptions:")
            print("1. Connect to controller")
            print("2. Run zone")
            print("3. Get status")
            print("4. Stop all irrigation")
            print("0. Exit")

            choice = input("\nEnter choice: ").strip()

            if choice == '0':
                print("👋 Goodbye!")
                break

            elif choice == '1':
                # Connect to controller with user-provided credentials
                ip = input("Enter IP address: ").strip()
                password = input("Enter password: ").strip()
                self.ip = ip
                self.password = password
                await self.connect()

            elif choice == '2':
                # Run zone - requires connection first
                if not self.controller:
                    print("❌ Connect first (option 1)")
                    continue

                try:
                    zone = int(input("Enter zone number (1-19): ").strip())
                    duration = int(input("Enter duration (minutes): ").strip())

                    # Validate zone and duration ranges
                    if 1 <= zone <= 19 and 1 <= duration <= 60:
                        await self.run_zone(zone, duration)
                    else:
                        print("❌ Zone must be 1-19, duration 1-60 minutes")

                except ValueError:
                    print("❌ Please enter valid numbers")

            elif choice == '3':
                # Get current status
                await self.get_status()

            elif choice == '4':
                # Emergency stop
                await self.stop_all()

            else:
                print("❌ Invalid choice")

            # Pause before showing menu again
            input("\nPress Enter to continue...")
    
    async def cleanup(self):
        """
        Clean up network resources and close connections.

        Properly closes the aiohttp ClientSession to prevent resource leaks
        and ensure all pending HTTP connections are terminated gracefully.

        Resource Management:
            - Closes aiohttp ClientSession if open
            - Releases network connections
            - Prevents "Unclosed client session" warnings
            - Safe to call multiple times (checks if session exists)

        Returns:
            None

        Note:
            This method MUST be called before program exit to prevent
            resource leaks. Use in a try/finally block or async context
            manager to ensure cleanup happens even if errors occur.

        Example:
            try:
                cli = SimpleRainBirdCLI("192.168.1.113", "1234")
                await cli.connect()
                await cli.run_zone(1, 10)
            finally:
                await cli.cleanup()  # Always cleanup
        """
        if self.session:
            await self.session.close()


def print_help():
    """
    Display comprehensive help information for the CLI.

    Prints detailed usage instructions, command-line options, examples,
    and feature descriptions to help users understand how to use the CLI.

    The help output includes:
        - Usage patterns for different modes
        - All available command-line options
        - Practical examples for common tasks
        - Feature list highlighting capabilities

    Returns:
        None - Outputs to stdout

    Note:
        This is a standalone function (not a class method) so it can be
        called before initializing the CLI instance.
    """
    print("""
🌱 Simple RainBird CLI - Help
============================

USAGE:
  python3 simple_cli.py [OPTIONS]

OPTIONS:
  --ip IP              Controller IP address (required for non-interactive)
  --password PASS      Controller password (required for non-interactive)
  --zone ZONE          Zone number to run (1-19)
  --duration MINS      Duration in minutes (1-60)
  --status             Get current irrigation status
  --stop               Stop all irrigation
  --help               Show this help

EXAMPLES:
  Interactive mode:
    python3 simple_cli.py

  Connect and run zone 1 for 10 minutes:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10

  Get status:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status

  Stop all irrigation:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --stop

FEATURES:
  ✅ Simple zone control
  ✅ Remaining time calculation
  ✅ Current status display
  ✅ Command-line parameters
  ✅ Interactive menu
  ✅ ESP-ME3 compatible
""")

async def main():
    """
    Main entry point for the CLI application.

    Handles command-line argument parsing and dispatches to either command-line
    mode (with parameters) or interactive mode (menu-driven). Ensures proper
    resource cleanup regardless of how the program exits.

    Operation Modes:

        1. Help Mode (--help):
           Displays help and exits immediately

        2. Command-Line Mode (--ip and --password provided):
           - Connects to controller
           - Executes single requested action
           - Exits after action completes

        3. Interactive Mode (no IP/password):
           - Displays menu system
           - Loops until user exits
           - Prompts for connection details

    Command-Line Arguments:
        --ip IP                 Controller IP address (required for non-interactive)
        --password PASS         Controller password (required for non-interactive)
        --zone ZONE             Zone to run (1-19, requires --duration)
        --duration MINS         Duration in minutes (1-60, requires --zone)
        --status                Get current irrigation status
        --stop                  Stop all irrigation
        --help                  Show help information

    Error Handling:
        - Handles KeyboardInterrupt (Ctrl+C) gracefully
        - Always calls cleanup() in finally block
        - Validates zone and duration ranges
        - Requires connection before zone operations

    Examples:
        # Interactive mode
        python3 simple_cli.py

        # Run zone 1 for 10 minutes
        python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10

        # Check status
        python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status

        # Emergency stop
        python3 simple_cli.py --ip 192.168.1.113 --password 1234 --stop

    Returns:
        None

    Note:
        Uses asyncio.run() to execute the async main coroutine. This handles
        the event loop lifecycle automatically.
    """
    # Parse command-line arguments
    # add_help=False prevents default --help to use custom print_help()
    parser = argparse.ArgumentParser(
        description='Simple RainBird Controller CLI',
        add_help=False
    )
    parser.add_argument('--ip', help='Controller IP address')
    parser.add_argument('--password', help='Controller password')
    parser.add_argument('--zone', type=int, help='Zone number (1-19)')
    parser.add_argument('--duration', type=int, help='Duration in minutes (1-60)')
    parser.add_argument('--status', action='store_true', help='Get current status')
    parser.add_argument('--stop', action='store_true', help='Stop all irrigation')
    parser.add_argument('--help', action='store_true', help='Show help')

    args = parser.parse_args()

    # Handle help request
    if args.help:
        print_help()
        return

    # Initialize CLI with provided credentials (or None for interactive)
    cli = SimpleRainBirdCLI(args.ip, args.password)

    try:
        # Command-line mode: IP and password provided
        if args.ip and args.password:
            # Connect first - required for all operations
            if not await cli.connect():
                return

            # Execute requested action
            if args.zone and args.duration:
                # Run zone with validation
                if 1 <= args.zone <= 19 and 1 <= args.duration <= 60:
                    await cli.run_zone(args.zone, args.duration)
                else:
                    print("❌ Zone must be 1-19, duration 1-60 minutes")

            elif args.status:
                # Get current status
                await cli.get_status()

            elif args.stop:
                # Emergency stop all zones
                await cli.stop_all()

            else:
                # Just connect, no action requested
                print("✅ Connected successfully")

        # Interactive mode: No credentials provided
        else:
            await cli.interactive_menu()

    except KeyboardInterrupt:
        # Graceful handling of Ctrl+C
        print("\n👋 Interrupted by user")

    finally:
        # Always cleanup resources to prevent leaks
        await cli.cleanup()


if __name__ == '__main__':
    # Run the async main function
    # asyncio.run() handles event loop creation and cleanup
    asyncio.run(main())

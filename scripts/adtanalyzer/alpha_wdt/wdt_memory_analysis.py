import os
import sys
import subprocess
import time
import psutil
import logging
from datetime import datetime

def get_config():
    """Get or create configuration settings"""
    config_path = "wdt_analysis_config.txt"
    config = {}
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                key, value = line.strip().split('=', 1)
                config[key] = value
    else:
        # Default paths
        config['wow_path'] = r"H:\053-client\WoWClient.exe"
        config['x64dbg_path'] = r"C:\apps\x64dbg\release\x64\x64dbg.exe"
        
        # Save config
        with open(config_path, 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        
        print(f"Created default config file: {config_path}")
        print("Please edit the paths if they don't match your system configuration.")
    
    return config

def setup_logging():
    """Setup logging configuration"""
    log_filename = f"wdt_memory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return log_filename

def find_wow_process():
    """Find the WoW client process"""
    for proc in psutil.process_iter(['pid', 'name']):
        if 'WoWClient.exe' in proc.info['name']:
            return proc.info['pid']
    return None

def create_x64dbg_script(wdt_path, script_path):
    """
    Create an x64dbg script to analyze WDT loading
    """
    script_content = f"""
// X64DBG Script for WDT Analysis
msg "Starting WDT analysis..."

// Set breakpoints
bp CreateFileW
bp ReadFile
bp VirtualAlloc

// Main loop
loop:
    run
    
    // Check which breakpoint was hit
    rtu
    log "Hit breakpoint at " + mod
    
    // If CreateFileW, check filename
    cmp mod, "CreateFileW"
    jne checkread
    log "CreateFileW called with: "
    log arg1
    jmp continue
    
    // If ReadFile, check for WDT chunks
checkread:
    cmp mod, "ReadFile"
    jne checkmem
    log "ReadFile buffer at: "
    log arg2
    
    // Search for WDT signatures
    find arg2, #1000, "REVM"
    log "MVER at: "
    log $result
    
    find arg2, #1000, "DHPM"
    log "MPHD at: "
    log $result
    
    find arg2, #1000, "NIAM"
    log "MAIN at: "
    log $result
    
    // Dump if found
    cmp $result, 0
    je continue
    dump arg2, arg2+#1000, "chunk_dump.bin"
    jmp continue
    
    // If VirtualAlloc, log it
checkmem:
    cmp mod, "VirtualAlloc"
    jne continue
    log "Memory allocated at: "
    log $result
    
continue:
    jmp loop
"""
    with open(script_path, 'w') as f:
        f.write(script_content)

def analyze_wdt_in_memory(wdt_path):
    """
    Analyze WDT file loading in memory using x64dbg
    """
    logging.info(f"Starting WDT memory analysis for: {wdt_path}")
    
    # Get configuration
    config = get_config()
    
    # Validate paths
    if not os.path.exists(config['wow_path']):
        logging.error(f"WoWClient.exe not found at: {config['wow_path']}")
        print(f"Error: WoWClient.exe not found. Please update path in wdt_analysis_config.txt")
        return
        
    if not os.path.exists(config['x64dbg_path']):
        logging.error(f"x64dbg not found at: {config['x64dbg_path']}")
        print(f"Error: x64dbg not found. Please update path in wdt_analysis_config.txt")
        return
    
    # Create x64dbg script first
    script_path = "wdt_analysis_script.txt"
    create_x64dbg_script(wdt_path, script_path)
    
    try:
        # Launch WoWClient.exe and wait for it to start
        logging.info("Launching WoWClient.exe...")
        wow_process = subprocess.Popen([config['wow_path'], "-uptodate", "-windowed"])
        
        # Give the process time to initialize
        time.sleep(10)  # Increased wait time for proper initialization
        
        if wow_process.poll() is not None:
            logging.error("WoWClient.exe failed to start")
            return
            
        # Get the PID
        wow_pid = wow_process.pid
        logging.info(f"WoWClient.exe started with PID: {wow_pid}")
        
        # Launch x64dbg with the script
        logging.info("Launching x64dbg debugger...")
        x64dbg_process = subprocess.Popen([
            config['x64dbg_path'],
            "-p", str(wow_pid),
            "-s", script_path
        ])
        
        # Monitor for memory dumps
        logging.info("Monitoring for WDT chunks in memory...")
        dump_file = "chunk_dump.bin"
        timeout = 60  # seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(dump_file):
                logging.info(f"Found memory dump: {dump_file}")
                # Analyze the dump for WDT structures
                with open(dump_file, 'rb') as f:
                    dump_data = f.read()
                    # Look for chunk signatures
                    for chunk in ['MVER', 'MPHD', 'MAIN', 'MCNK', 'MDDF', 'MODF']:
                        pos = dump_data.find(chunk.encode()[::-1])  # Reverse for little-endian
                        if pos != -1:
                            size = int.from_bytes(dump_data[pos+4:pos+8], 'little')
                            logging.info(f"Found {chunk} chunk in memory at offset {pos}, size: {size}")
                            
                            # Extract and log chunk data
                            chunk_data = dump_data[pos+8:pos+8+size]
                            logging.info(f"Chunk data (hex): {chunk_data.hex()[:100]}...")
                
                # Remove the dump file to prepare for next dump
                os.remove(dump_file)
            time.sleep(1)
        
        logging.info("Memory analysis complete")
        
        # Cleanup
        if wow_process.poll() is None:
            wow_process.terminate()
        if x64dbg_process.poll() is None:
            x64dbg_process.terminate()
            
    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        raise

def main():
    if len(sys.argv) != 2:
        print("Usage: python wdt_memory_analysis.py <path_to_wdt_file>")
        return
    
    wdt_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(wdt_path):
        print(f"Error: WDT file not found: {wdt_path}")
        return
    
    log_file = setup_logging()
    print(f"Analysis started. Check {log_file} for details.")
    
    try:
        analyze_wdt_in_memory(wdt_path)
    except Exception as e:
        print(f"Analysis failed: {e}")
        logging.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
engines/orchestrator.py
Orchestrates the AI dialogue pipeline by running script generation and rendering
in the same process to maintain pipeline timing consistency.

Workflow:
1. Run ai_engine.py to generate JSON scripts in output/scripts/
2. Run dialogue_generator.py to convert JSON scripts to WebP images in output/dialogues/
3. Both processes share the same PIPELINE_RUN_TS environment variable
   to ensure script-image pairing works correctly
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

def run_ai_engine() -> bool:
    """Run the AI script generation engine.
    
    Returns:
        True if successful, False otherwise.
    """
    print("[*] Starting AI script generation (ai_engine.py)...")
    
    # Set up environment for ai_engine.py
    env = os.environ.copy()
    
    # Ensure we have a pipeline timestamp for this run
    if "PIPELINE_RUN_TS" not in env or not env["PIPELINE_RUN_TS"].strip():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        env["PIPELINE_RUN_TS"] = ts
        print(f"[*] Generated PIPELINE_RUN_TS: {ts}")
    
    # Run ai_engine.py
    try:
        result = subprocess.run(
            [sys.executable, "ai_engine.py"],
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        # Print output for debugging
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"[!] ai_engine.py stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"[!] ai_engine.py failed with return code {result.returncode}")
            return False
            
        print("[+] AI script generation completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print("[!] ai_engine.py timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"[!] Error running ai_engine.py: {e}")
        return False

def run_dialogue_generator() -> bool:
    """Run the dialogue rendering engine.
    
    Returns:
        True if successful, False otherwise.
    """
    print("[*] Starting dialogue rendering (dialogue_generator.py)...")
    
    # Use the same environment (including PIPELINE_RUN_TS) from ai_engine.py
    env = os.environ.copy()
    
    # Run dialogue_generator.py
    try:
        result = subprocess.run(
            [sys.executable, "dialogue_generator.py"],
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        # Print output for debugging
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"[!] dialogue_generator.py stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"[!] dialogue_generator.py failed with return code {result.returncode}")
            return False
            
        print("[+] Dialogue rendering completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print("[!] dialogue_generator.py timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"[!] Error running dialogue_generator.py: {e}")
        return False

def main() -> None:
    """Main orchestrator function."""
    print("[*] Starting AI Dialogue Pipeline Orchestrator...")
    
    # Step 1: Generate AI scripts
    if not run_ai_engine():
        print("[!] Pipeline aborted due to ai_engine.py failure")
        sys.exit(1)
    
    # Step 2: Render dialogue images
    if not run_dialogue_generator():
        print("[!] Pipeline aborted due to dialogue_generator.py failure")
        sys.exit(1)
    
    print("[+] AI Dialogue Pipeline completed successfully!")

if __name__ == "__main__":
    main()

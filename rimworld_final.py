#!/usr/bin/env python3
"""
RimWorld Trait Auto-Roller - FINAL VERSION
- F7: Set Random button position
- F9: Toggle start/stop
- Looks for ONE trait from List A AND ONE trait from List B
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyautogui
import pytesseract
from PIL import Image, ImageGrab
import numpy as np
import cv2
import threading
import time
import keyboard
import json
import os
import subprocess
import queue

class RimWorldAutoRoller:
    def __init__(self):
        # Main window - make it resizable
        self.root = tk.Tk()
        self.root.title("RimWorld Trait Roller")
        self.root.geometry("380x600")
        self.root.minsize(350, 400)  # Minimum size
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        
        # State
        self.is_rolling = False
        self.random_btn_pos = None
        
        # Async logging queue
        self.log_queue = queue.Queue()
        self.start_log_worker()
        
        # Setup Tesseract
        try:
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        except:
            pass
        
        # Disable pyautogui safety features for speed
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False
        
        self.create_ui()
        self.register_hotkeys()
    
    def create_ui(self):
        # Main container with grid for resizing
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill="both", expand=True)
        main.grid_rowconfigure(2, weight=1)  # List A row
        main.grid_rowconfigure(4, weight=2)  # List B row
        main.grid_rowconfigure(7, weight=1)  # Log row
        main.grid_columnconfigure(0, weight=1)
        
        # Title
        ttk.Label(main, text="RimWorld Trait Finder", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        # Status
        self.status = ttk.Label(main, text="Press F7 on Randomize button", foreground="red")
        self.status.grid(row=1, column=0, pady=10, sticky="w")
        
        # List A - Required traits (normalized: no hyphens, all lowercase)
        list_a_frame = ttk.Frame(main)
        list_a_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        list_a_frame.grid_rowconfigure(1, weight=1)
        list_a_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(list_a_frame, text="MUST HAVE one of:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.list_a = tk.Text(list_a_frame, height=3, width=45)
        self.list_a.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbar for List A
        list_a_scroll = ttk.Scrollbar(list_a_frame, orient="vertical", command=self.list_a.yview)
        list_a_scroll.grid(row=1, column=1, sticky="ns")
        self.list_a.config(yscrollcommand=list_a_scroll.set)
        
        default_required = ["tough", "iron willed", "industrious"]
        self.list_a.insert("1.0", "\n".join(default_required))
        
        # List B - Good traits (normalized: no hyphens, all lowercase)
        list_b_frame = ttk.Frame(main)
        list_b_frame.grid(row=4, column=0, sticky="nsew", pady=5)
        list_b_frame.grid_rowconfigure(1, weight=1)
        list_b_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(list_b_frame, text="AND one of these:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.list_b = tk.Text(list_b_frame, height=6, width=45)
        self.list_b.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbar for List B
        list_b_scroll = ttk.Scrollbar(list_b_frame, orient="vertical", command=self.list_b.yview)
        list_b_scroll.grid(row=1, column=1, sticky="ns")
        self.list_b.config(yscrollcommand=list_b_scroll.set)
        
        good_traits = ["jogger", "nimble", "quick sleeper", "sanguine", "kind", 
                      "brawler", "great memory", "masochist", "super immune",
                      "hard worker", "fast learner", "bloodlust", "undergrounder", 
                      "fast walker", "optimist", "steadfast",
                      "psychically hypersensitive", "psychically sensitive"]
        self.list_b.insert("1.0", "\n".join(good_traits))
        
        # Speed control
        speed_frame = ttk.Frame(main)
        speed_frame.grid(row=5, column=0, pady=5, sticky="w")
        ttk.Label(speed_frame, text="Delay (ms):").pack(side="left")
        self.delay = tk.StringVar(value="25")  # 25ms = 40 clicks/sec
        ttk.Entry(speed_frame, textvariable=self.delay, width=8).pack(side="left", padx=5)
        # OCR logging checkbox
        self.log_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(speed_frame, text="Log OCR", variable=self.log_ocr).pack(side="left", padx=10)
        
        # Log
        log_frame = ttk.Frame(main)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=5)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(log_frame, text="Log:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.log = scrolledtext.ScrolledText(log_frame, height=8, width=45, state='disabled')
        self.log.grid(row=1, column=0, sticky="nsew")
        
        # Save/Load/Log buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=8, column=0, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Save Config", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Load Config", command=self.load_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Open Log", command=self.open_log).pack(side="left", padx=5)
        
        # Instructions
        ttk.Label(main, text="F7: Set button | F9: Start/Stop", foreground="blue", font=("Arial", 10, "bold")).grid(row=9, column=0, pady=10, sticky="w")
        
        # Load config on startup
        self.load_config()
    
    def register_hotkeys(self):
        keyboard.add_hotkey('f7', self.set_button)
        keyboard.add_hotkey('f9', self.toggle)
    
    def start_log_worker(self):
        """Start async log worker thread"""
        self.last_log_msg = ""  # Track last message to avoid duplicates
        def worker():
            while True:
                try:
                    msg = self.log_queue.get(timeout=0.1)
                    if msg is None:
                        break
                    
                    # Skip duplicate messages
                    if msg == self.last_log_msg:
                        continue
                    self.last_log_msg = msg
                    
                    # Write to UI
                    self.log.config(state='normal')
                    self.log.insert(tk.END, f"{time.strftime('%H:%M:%S')} {msg}\n")
                    self.log.see(tk.END)
                    self.log.config(state='disabled')
                    
                    # Write to file
                    with open("rimworld_log.txt", "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
                except:
                    pass
        
        threading.Thread(target=worker, daemon=True).start()
    
    def write_log(self, msg):
        """Queue log message for async writing"""
        self.log_queue.put(msg)
    
    def set_button(self):
        """F7 - Set Random button position"""
        self.random_btn_pos = pyautogui.position()
        self.status.config(text=f"Button at {self.random_btn_pos}", foreground="green")
        self.write_log(f"Button set: {self.random_btn_pos}")
        
        # Show capture area
        self.show_overlay()
    
    def show_overlay(self):
        """Show where traits will be captured"""
        if not self.random_btn_pos:
            return
        
        # TRAITS LOCATION: Measured from screenshots
        x = self.random_btn_pos.x - 770  # To the "Traits" text
        y = self.random_btn_pos.y + 280  # Down to trait names
        w, h = 300, 100
        
        # Create overlay
        overlay = tk.Toplevel()
        overlay.geometry(f"{w}x{h}+{x}+{y}")
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg='red')
        
        # Auto close
        overlay.after(1500, overlay.destroy)
    
    def toggle(self):
        """F9 - Start/Stop"""
        if self.is_rolling:
            self.stop()
        else:
            self.start()
    
    def start(self):
        if not self.random_btn_pos:
            self.write_log("Set button first (F7)")
            return
        
        self.is_rolling = True
        self.status.config(text="ROLLING... F9 to stop", foreground="orange")
        self.write_log("Started")
        
        # Start thread
        threading.Thread(target=self.rolling_loop, daemon=True).start()
    
    def stop(self):
        self.is_rolling = False
        self.status.config(text="Stopped", foreground="blue")
        self.write_log("Stopped")
    
    def rolling_loop(self):
        """Main loop - FIXED: wait on the SAME pawn"""
        delay = float(self.delay.get()) / 1000
        
        # Pre-compile lists for speed
        list_a = [t.strip().lower().replace('-', ' ') for t in self.list_a.get("1.0", tk.END).strip().split('\n') if t.strip()]
        list_b = [t.strip().lower().replace('-', ' ') for t in self.list_b.get("1.0", tk.END).strip().split('\n') if t.strip()]
        
        # Pre-calculate capture region
        x = self.random_btn_pos.x - 770
        y = self.random_btn_pos.y + 280
        bbox = (x, y, x + 300, y + 100)
        
        while self.is_rolling:
            try:
                start = time.perf_counter()
                
                # Wait a bit for the game to update after click
                time.sleep(0.1)
                
                # Check current pawn's traits
                result = self.check_traits_optimized(bbox, list_a, list_b)
                
                if result == "combo":
                    self.write_log("★★★ FOUND COMBO ★★★")
                    pyautogui.alert("Found trait combo!", "SUCCESS")
                    self.stop()
                    break
                elif result == "partial":
                    # Found MUST HAVE trait - STOP HERE and wait
                    self.write_log("Found MUST HAVE trait but no second trait - pausing 5s")
                    self.write_log("Waiting for user to decide...")
                    # Wait 5 seconds ON THIS PAWN
                    time.sleep(5)
                    # After waiting, continue to click to next pawn
                
                # Click to next pawn
                pyautogui.click(self.random_btn_pos)
                
                # Wait remaining time
                elapsed = time.perf_counter() - start
                if elapsed < delay:
                    time.sleep(max(0, delay - elapsed))
                    
            except Exception as e:
                self.write_log(f"Error: {e}")
                time.sleep(0.1)
    
    def check_traits_optimized(self, bbox, list_a, list_b):
        """Optimized OCR with working configuration"""
        try:
            # Direct screenshot with pre-calculated bbox
            img = ImageGrab.grab(bbox=bbox)
            
            # Convert to grayscale for OCR
            img_np = np.array(img)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            
            # Simple threshold for better OCR
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            
            # Working OCR config - PSM 6 for uniform text, default OEM
            text = pytesseract.image_to_string(thresh, config='--psm 6')
            
            # Fast normalization
            text_lower = text.lower().replace('-', ' ').replace('_', ' ')
            
            # Ultra-fast trait checking with early exit
            found_a = None
            found_b = None
            
            # Quick scan for MUST HAVE traits
            for trait in list_a:
                if trait in text_lower:
                    found_a = trait
                    break
            
            # If no primary trait and OCR logging enabled, log for debugging
            if not found_a and self.log_ocr.get() and text.strip():
                self.write_log(f"OCR: {' '.join(text.split())[:40]}")
            
            # Only check secondary if we found primary
            if found_a:
                for trait in list_b:
                    if trait in text_lower:
                        found_b = trait
                        break
                
                # Log only when we find something
                if found_b:
                    if self.log_ocr.get():
                        self.write_log(f"OCR: {' '.join(text.split())[:40]}")
                    self.write_log(f"COMBO: {found_a} + {found_b}")
                    return "combo"
                else:
                    if self.log_ocr.get():
                        self.write_log(f"OCR: {' '.join(text.split())[:40]}")
                    self.write_log(f"Found MUST HAVE: {found_a} (no second trait)")
                    return "partial"
            
            return None
            
        except:
            return None
    
    def save_config(self):
        """Save current configuration"""
        config = {
            "list_a": self.list_a.get("1.0", tk.END).strip(),
            "list_b": self.list_b.get("1.0", tk.END).strip(),
            "delay": self.delay.get()
        }
        try:
            with open("rimworld_config.json", "w") as f:
                json.dump(config, f, indent=2)
            self.write_log("Config saved")
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            self.write_log(f"Save failed: {e}")
    
    def open_log(self):
        """Open log file in Notepad++"""
        try:
            # Try Notepad++ first
            subprocess.Popen(["notepad++", "rimworld_log.txt"], shell=True)
        except:
            try:
                # Fallback to notepad
                subprocess.Popen(["notepad", "rimworld_log.txt"], shell=True)
            except Exception as e:
                self.write_log(f"Could not open log: {e}")
    
    def load_config(self):
        """Load configuration if exists"""
        if os.path.exists("rimworld_config.json"):
            try:
                with open("rimworld_config.json", "r") as f:
                    config = json.load(f)
                
                # Clear and set list A
                self.list_a.delete("1.0", tk.END)
                self.list_a.insert("1.0", config.get("list_a", "tough\niron willed\nindustrious"))
                
                # Clear and set list B
                self.list_b.delete("1.0", tk.END)
                self.list_b.insert("1.0", config.get("list_b", ""))
                
                # Set delay
                self.delay.set(config.get("delay", "25"))
                
                self.write_log("Config loaded")
            except Exception as e:
                self.write_log(f"Load failed: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RimWorldAutoRoller()
    app.run()
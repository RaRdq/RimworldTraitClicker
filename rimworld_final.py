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
        main.grid_rowconfigure(1, weight=1)  # Notebook row
        main.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=5)
        
        # Tab 1: Trait Roller
        self.trait_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.trait_tab, text="Trait Roller")
        
        # Tab 2: Autoclicker
        self.autoclicker_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.autoclicker_tab, text="Autoclicker")
        
        self.create_trait_tab()
        self.create_autoclicker_tab()
    
    def create_trait_tab(self):
        # Configure grid for trait tab
        self.trait_tab.grid_rowconfigure(2, weight=1)  # List A row
        self.trait_tab.grid_rowconfigure(4, weight=2)  # List B row
        self.trait_tab.grid_rowconfigure(7, weight=1)  # Log row
        self.trait_tab.grid_columnconfigure(0, weight=1)
        
        # Title
        ttk.Label(self.trait_tab, text="RimWorld Trait Finder", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        # Status
        self.status = ttk.Label(self.trait_tab, text="Press F7 on Randomize button", foreground="red")
        self.status.grid(row=1, column=0, pady=10, sticky="w")
        
        # List A - Required traits (normalized: no hyphens, all lowercase)
        list_a_frame = ttk.Frame(self.trait_tab)
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
        list_b_frame = ttk.Frame(self.trait_tab)
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
        speed_frame = ttk.Frame(self.trait_tab)
        speed_frame.grid(row=5, column=0, pady=5, sticky="w")
        ttk.Label(speed_frame, text="Delay (ms):").pack(side="left")
        self.delay = tk.StringVar(value="25")  # 25ms = 40 clicks/sec
        ttk.Entry(speed_frame, textvariable=self.delay, width=8).pack(side="left", padx=5)
        # OCR logging checkbox
        self.log_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(speed_frame, text="Log OCR", variable=self.log_ocr).pack(side="left", padx=10)
        
        # Log
        log_frame = ttk.Frame(self.trait_tab)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=5)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(log_frame, text="Log:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.log = scrolledtext.ScrolledText(log_frame, height=8, width=45, state='disabled')
        self.log.grid(row=1, column=0, sticky="nsew")
        
        # Save/Load/Log buttons
        btn_frame = ttk.Frame(self.trait_tab)
        btn_frame.grid(row=8, column=0, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Save Config", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Load Config", command=self.load_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Open Log", command=self.open_log).pack(side="left", padx=5)
        
        # Instructions
        ttk.Label(self.trait_tab, text="F7: Set button | F9: Start/Stop", foreground="blue", font=("Arial", 10, "bold")).grid(row=9, column=0, pady=10, sticky="w")
        
        # Load config on startup
        self.load_config()
    
    def create_autoclicker_tab(self):
        """Create the autoclicker tab UI"""
        # State for autoclicker
        self.click_sequence = []
        self.is_recording = False
        self.is_playing = False
        
        # Configure grid for autoclicker tab
        self.autoclicker_tab.grid_rowconfigure(3, weight=1)  # Sequence list row
        self.autoclicker_tab.grid_columnconfigure(0, weight=1)
        
        # Title
        ttk.Label(self.autoclicker_tab, text="Autoclicker Macro", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        
        # Status
        self.autoclicker_status = ttk.Label(self.autoclicker_tab, text="Ready - Press F7 to start recording", foreground="blue")
        self.autoclicker_status.grid(row=1, column=0, pady=5, sticky="w")
        
        # Control buttons frame
        control_frame = ttk.Frame(self.autoclicker_tab)
        control_frame.grid(row=2, column=0, pady=10, sticky="w")
        
        ttk.Button(control_frame, text="Insert Delay", command=self.insert_delay).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Clear", command=self.clear_sequence).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Save", command=self.save_sequence).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Load", command=self.load_sequence).pack(side="left", padx=2)
        
        # Sequence list
        sequence_frame = ttk.Frame(self.autoclicker_tab)
        sequence_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        sequence_frame.grid_rowconfigure(1, weight=1)
        sequence_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(sequence_frame, text="Click Sequence:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(sequence_frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        self.sequence_listbox = tk.Listbox(list_frame, font=("Consolas", 9))
        self.sequence_listbox.grid(row=0, column=0, sticky="nsew")
        self.sequence_listbox.bind("<Double-Button-1>", self.edit_click_delay)
        
        sequence_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.sequence_listbox.yview)
        sequence_scroll.grid(row=0, column=1, sticky="ns")
        self.sequence_listbox.config(yscrollcommand=sequence_scroll.set)
        
        # Play options frame
        play_frame = ttk.Frame(self.autoclicker_tab)
        play_frame.grid(row=4, column=0, pady=10, sticky="w")
        
        ttk.Label(play_frame, text="Play Options:").pack(side="left")
        ttk.Label(play_frame, text="Delay (ms):").pack(side="left", padx=(20, 5))
        self.play_delay = tk.StringVar(value="100")
        ttk.Entry(play_frame, textvariable=self.play_delay, width=8).pack(side="left", padx=5)
        
        ttk.Label(play_frame, text="Repeat:").pack(side="left", padx=(20, 5))
        self.repeat_count = tk.StringVar(value="1")
        ttk.Entry(play_frame, textvariable=self.repeat_count, width=8).pack(side="left", padx=5)
        
        
        # Instructions
        ttk.Label(self.autoclicker_tab, text="F10: Start/Stop recording | F12: Play | ESC: Emergency stop", 
                 foreground="blue", font=("Arial", 10, "bold")).grid(row=5, column=0, pady=10, sticky="w")
    
    def register_hotkeys(self):
        keyboard.add_hotkey('f7', self.handle_f7)
        keyboard.add_hotkey('f9', self.handle_f9)
        keyboard.add_hotkey('f10', self.handle_f10)
        keyboard.add_hotkey('f12', self.handle_f12)
        keyboard.add_hotkey('esc', self.emergency_stop)
    
    def emergency_stop(self):
        """Emergency stop for recording/playback"""
        if self.is_recording:
            self.is_recording = False
            self.autoclicker_status.config(text="Recording stopped (ESC)", foreground="red")
        if self.is_playing:
            self.is_playing = False
            self.autoclicker_status.config(text="Playback stopped (ESC)", foreground="red")
    
    def handle_f7(self):
        """F7 handler - trait tab only"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Trait tab
            self.set_button()
    
    def handle_f9(self):
        """F9 handler - trait tab only"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Trait tab
            self.toggle()
    
    def handle_f10(self):
        """F10 handler - autoclicker record/stop"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Autoclicker tab
            self.toggle_recording()
    
    def handle_f12(self):
        """F12 handler - autoclicker play"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Autoclicker tab
            self.play_sequence()
    
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
    
    def toggle_recording(self):
        """Toggle click recording on/off"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start/continue recording clicks"""
        if self.is_playing:
            return
        
        self.is_recording = True
        # Don't clear existing sequence - continue adding to it
        self.update_sequence_display()
        
        if len(self.click_sequence) > 0:
            self.autoclicker_status.config(text=f"Continuing recording... {len(self.click_sequence)} clicks so far", foreground="red")
        else:
            self.autoclicker_status.config(text="Recording... Click anywhere, press F10 to stop", foreground="red")
        
        # Start click listener thread
        self.recording_thread = threading.Thread(target=self.click_listener, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        """Stop recording clicks"""
        self.is_recording = False
        self.autoclicker_status.config(text=f"Recording stopped - {len(self.click_sequence)} clicks saved", foreground="blue")
        self.update_sequence_display()
    
    def click_listener(self):
        """Listen for clicks while recording"""
        import mouse
        
        def on_click(event):
            if self.is_recording and hasattr(event, 'event_type') and event.event_type == mouse.DOWN:
                pos = pyautogui.position()
                button = 'left' if event.button == mouse.LEFT else 'right'
                
                self.click_sequence.append({
                    'x': pos.x,
                    'y': pos.y,
                    'button': button,
                    'type': 'click',
                    'random_offset': 0  # Default no offset
                })
                self.root.after_idle(self.update_sequence_display)
        
        mouse.hook(on_click)
        
        # Keep thread alive while recording
        while self.is_recording:
            time.sleep(0.1)
        
        mouse.unhook_all()
    
    def play_sequence(self):
        """Play back the recorded click sequence"""
        if not self.click_sequence or self.is_recording or self.is_playing:
            return
        
        try:
            delay = max(0.05, float(self.play_delay.get()) / 1000)  # Min 50ms
            repeats = int(self.repeat_count.get())
        except ValueError:
            delay = 0.1
            repeats = 1
        
        self.is_playing = True
        self.autoclicker_status.config(text=f"Playing sequence... Press ESC to stop", foreground="orange")
        
        # Start playback thread
        threading.Thread(target=self.playback_worker, args=(delay, repeats), daemon=True).start()
    
    def playback_worker(self, global_delay, repeats):
        """Worker thread for sequence playback"""
        import random
        try:
            # Initial delay before starting
            time.sleep(0.5)
            
            for repeat in range(repeats):
                if not self.is_playing:
                    break
                
                # Delay before each repeat (except first)
                if repeat > 0:
                    time.sleep(1.0)  # 1 second between repeats
                
                for i, item in enumerate(self.click_sequence):
                    if not self.is_playing:
                        break
                    
                    # Update status
                    self.root.after_idle(lambda r=repeat+1, i=i+1: 
                        self.autoclicker_status.config(text=f"Playing {r}/{repeats} - Item {i}/{len(self.click_sequence)}", foreground="orange"))
                    
                    if item['type'] == 'click':
                        # Apply per-click random offset if specified
                        x = item['x']
                        y = item['y']
                        click_offset = item.get('random_offset', 0)
                        if click_offset > 0:
                            x += random.randint(-click_offset, click_offset)
                            y += random.randint(-click_offset, click_offset)
                        
                        # Move to position first, then click
                        pyautogui.moveTo(x, y)
                        time.sleep(0.02)  # Small pause after move
                        
                        if item['button'] == 'right':
                            pyautogui.mouseDown(x, y, button='right')
                            time.sleep(0.05)  # 50ms click duration
                            pyautogui.mouseUp(x, y, button='right')
                        else:
                            pyautogui.mouseDown(x, y, button='left')
                            time.sleep(0.05)  # 50ms click duration
                            pyautogui.mouseUp(x, y, button='left')
                    elif item['type'] == 'delay':
                        # Custom delay
                        time.sleep(item['delay_ms'] / 1000.0)
                    
                    # Always add delay between clicks (except after custom delays)
                    if i < len(self.click_sequence) - 1:
                        # Don't add delay if next item is a delay
                        next_item = self.click_sequence[i + 1] if i + 1 < len(self.click_sequence) else None
                        if not next_item or next_item['type'] != 'delay':
                            time.sleep(global_delay)
                
        
        finally:
            self.is_playing = False
            self.root.after_idle(lambda: self.autoclicker_status.config(text="Playback completed", foreground="green"))
    
    def update_sequence_display(self):
        """Update the sequence listbox"""
        self.sequence_listbox.delete(0, tk.END)
        
        for i, item in enumerate(self.click_sequence):
            if item['type'] == 'click':
                button_name = "Left" if item['button'] == 'left' else "Right"
                offset = item.get('random_offset', 0)
                if offset > 0:
                    self.sequence_listbox.insert(tk.END, f"{i+1:3d}. {button_name} click at ({item['x']}, {item['y']}) [±{offset}px]")
                else:
                    self.sequence_listbox.insert(tk.END, f"{i+1:3d}. {button_name} click at ({item['x']}, {item['y']})")
            elif item['type'] == 'delay':
                self.sequence_listbox.insert(tk.END, f"{i+1:3d}. DELAY {item['delay_ms']}ms")
    
    def clear_sequence(self):
        """Clear the recorded sequence"""
        if self.is_recording or self.is_playing:
            return
        
        self.click_sequence = []
        self.update_sequence_display()
        self.autoclicker_status.config(text="Sequence cleared", foreground="blue")
    
    def save_sequence(self):
        """Save click sequence to file"""
        if not self.click_sequence:
            messagebox.showwarning("Warning", "No sequence to save")
            return
        
        try:
            with open("click_sequence.json", "w") as f:
                json.dump(self.click_sequence, f, indent=2)
            messagebox.showinfo("Success", "Sequence saved!")
            self.autoclicker_status.config(text="Sequence saved", foreground="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def load_sequence(self):
        """Load click sequence from file"""
        if self.is_recording or self.is_playing:
            return
        
        try:
            if os.path.exists("click_sequence.json"):
                with open("click_sequence.json", "r") as f:
                    loaded_sequence = json.load(f)
                
                # Ensure backwards compatibility - convert old format to new
                for i, item in enumerate(loaded_sequence):
                    if 'type' not in item:
                        # Old format - convert to click item
                        item['type'] = 'click'
                        # Remove any old delay_ms fields as we now use separate delay items
                        if 'delay_ms' in item:
                            del item['delay_ms']
                
                self.click_sequence = loaded_sequence
                self.update_sequence_display()
                self.autoclicker_status.config(text=f"Sequence loaded - {len(self.click_sequence)} items", foreground="green")
            else:
                messagebox.showwarning("Warning", "No saved sequence found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
    
    def insert_delay(self):
        """Insert a delay at selected position"""
        if self.is_recording or self.is_playing:
            return
        
        # Get insertion position
        selection = self.sequence_listbox.curselection()
        if selection:
            insert_pos = selection[0] + 1  # Insert after selected item
        else:
            insert_pos = len(self.click_sequence)  # Insert at end
        
        # Create dialog to set delay
        dialog = tk.Toplevel(self.root)
        dialog.title("Insert Delay")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter delay in milliseconds:").pack(pady=10)
        
        delay_var = tk.StringVar(value="1000")
        entry = ttk.Entry(dialog, textvariable=delay_var, width=10, font=("Arial", 12))
        entry.pack(pady=5)
        entry.select_range(0, tk.END)
        entry.focus()
        
        def insert():
            try:
                delay_ms = int(delay_var.get())
                if delay_ms < 50:
                    messagebox.showwarning("Warning", "Minimum delay is 50ms")
                    return
                if delay_ms > 30000:
                    messagebox.showwarning("Warning", "Maximum delay is 30000ms (30 seconds)")
                    return
                
                delay_item = {
                    'type': 'delay',
                    'delay_ms': delay_ms
                }
                
                self.click_sequence.insert(insert_pos, delay_item)
                self.update_sequence_display()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        def cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Insert", command=insert).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)
        
        entry.bind("<Return>", lambda e: insert())
    
    def edit_click_delay(self, event):
        """Edit delay or click item"""
        if self.is_recording or self.is_playing:
            return
        
        selection = self.sequence_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index >= len(self.click_sequence):
            return
        
        item = self.click_sequence[index]
        
        if item['type'] == 'delay':
            # Edit existing delay
            current_delay = item['delay_ms']
            
            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Delay")
            dialog.geometry("300x150")
            dialog.transient(self.root)
            dialog.grab_set()
            
            ttk.Label(dialog, text=f"Edit delay #{index + 1}:").pack(pady=10)
            
            delay_var = tk.StringVar(value=str(current_delay))
            entry = ttk.Entry(dialog, textvariable=delay_var, width=10, font=("Arial", 12))
            entry.pack(pady=5)
            entry.select_range(0, tk.END)
            entry.focus()
            
            def save_delay():
                try:
                    new_delay = int(delay_var.get())
                    if new_delay < 50:
                        messagebox.showwarning("Warning", "Minimum delay is 50ms")
                        return
                    if new_delay > 30000:
                        messagebox.showwarning("Warning", "Maximum delay is 30000ms")
                        return
                    
                    self.click_sequence[index]['delay_ms'] = new_delay
                    self.update_sequence_display()
                    dialog.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid number")
            
            def delete_delay():
                self.click_sequence.pop(index)
                self.update_sequence_display()
                dialog.destroy()
            
            def cancel():
                dialog.destroy()
            
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="Save", command=save_delay).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Delete", command=delete_delay).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)
            
            entry.bind("<Return>", lambda e: save_delay())
        
        else:
            # Click item - show options to edit random offset, delete, or insert delay
            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Click")
            dialog.geometry("350x180")
            dialog.transient(self.root)
            dialog.grab_set()
            
            ttk.Label(dialog, text=f"Click #{index + 1} at ({item['x']}, {item['y']})").pack(pady=10)
            
            # Random offset setting
            offset_frame = ttk.Frame(dialog)
            offset_frame.pack(pady=10)
            ttk.Label(offset_frame, text="Random offset:").pack(side="left")
            current_offset = item.get('random_offset', 0)
            offset_var = tk.StringVar(value=str(current_offset))
            offset_entry = ttk.Entry(offset_frame, textvariable=offset_var, width=6)
            offset_entry.pack(side="left", padx=5)
            ttk.Label(offset_frame, text="px").pack(side="left")
            
            def save_offset():
                try:
                    new_offset = int(offset_var.get())
                    if new_offset < 0:
                        messagebox.showwarning("Warning", "Offset must be 0 or positive")
                        return
                    if new_offset > 50:
                        messagebox.showwarning("Warning", "Maximum offset is 50px")
                        return
                    
                    self.click_sequence[index]['random_offset'] = new_offset
                    self.update_sequence_display()
                    dialog.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid number")
            
            def delete_click():
                self.click_sequence.pop(index)
                self.update_sequence_display()
                dialog.destroy()
            
            def insert_delay_after():
                dialog.destroy()
                # Select this item and call insert_delay
                self.sequence_listbox.selection_set(index)
                self.insert_delay()
            
            def cancel():
                dialog.destroy()
            
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="Save Offset", command=save_offset).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Insert Delay After", command=insert_delay_after).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Delete Click", command=delete_click).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RimWorldAutoRoller()
    app.run()
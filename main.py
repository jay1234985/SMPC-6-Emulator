import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
import os
import ctypes
import json

ISA_DATA = [
    "NOP|000000|CONTROL|0|0|#FF6666|Simply skips to the next step.",
    "HLT|000001|CONTROL|0|0|#FF6666|Stops the program.",
    "JMP|000010|CONTROL|0|1|#FF6666|Jumps to a certain line in the program.",
    "JZ|000011|CONTROL|0|1|#FF6666|Jumps to a certain line in the program once zero is met in the output.",
    "INP1|000100|I/O|0|0|#4C97FF|Insert a number into operation input 1.",
    "INP2|000101|I/O|0|0|#4C97FF|Insert a number into operation input 2.",
    "OUTS|000110|I/O|0|0|#4C97FF|Outputs the most recent ALU result to the screen.",
    "OUTR|000111|I/O|1|0|#4C97FF|Outputs a certain RAM byte to the screen.",
    "ADD|001000|MATH|0|0|#59C059|Adds Operation Input 1 and 2.",
    "SUB|001001|MATH|0|0|#59C059|Subtracts Operation Input 2 from 1.",
    "MUL|001010|MATH|0|0|#59C059|Multiplies Operation Input 1 and 2.",
    "DIV|001011|MATH|0|0|#59C059|Divides Operation Input 1 and 2.",
    "AND|010000|LOGIC|0|0|#FFAB19|Bitwise AND.",
    "OR|010001|LOGIC|0|0|#FFAB19|Bitwise OR.",
    "XOR|010010|LOGIC|0|0|#FFAB19|Bitwise XOR.",
    "NOT1|010011|LOGIC|0|0|#FFAB19|Inverts everything in Operations Input 1.",
    "NOT2|010100|LOGIC|0|0|#FFAB19|Inverts everything in Operations Input 2.",
    "LDI1|011000|MEMORY|0|1|#9966FF|Loads a constant value onto Operation Input 1.",
    "LDI2|011001|MEMORY|0|1|#9966FF|Loads a constant value onto Operation Input 2.",
    "LDRO|011010|MEMORY|1|0|#9966FF|Loads RAM into output.",
    "LDR1|011011|MEMORY|1|0|#9966FF|Loads RAM into Operation Input 1.",
    "LDR2|011100|MEMORY|1|0|#9966FF|Loads RAM into Operation Input 2.",
    "STRO|011101|MEMORY|1|0|#9966FF|Stores most recent output into RAM.",
    "STR1|011110|MEMORY|1|0|#9966FF|Stores Operation Input 1 into RAM.",
    "STR2|011111|MEMORY|1|0|#9966FF|Stores Operation Input 2 into RAM.",
    "CLR|100000|MEMORY|1|0|#9966FF|Clears the RAM byte selected.",
    "OPI1|100001|MEMORY|0|0|#9966FF|Puts the most recent ALU output onto Operation Input 1.",
    "OPI2|100010|MEMORY|0|0|#9966FF|Puts the most recent ALU output onto Operation Input 2."
]


def load_custom_font():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.getcwd()
    p = os.path.join(base_path, "font.ttf")
    if os.path.exists(p):
        try:
            ctypes.windll.gdi32.AddFontResourceExW(p, 0x10, 0)
            return "pixel"
        except:
            pass
    return "Consolas"


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        label = tk.Label(tw, text=self.text, justify="left", background="#ffffe0", relief="solid", borderwidth=1,
                         font=("Arial", 9, "normal"))
        label.pack(ipadx=1)
        tw.update_idletasks()
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        s_h = self.widget.winfo_screenheight()
        if y + tw.winfo_height() > s_h - 50:
            y = self.widget.winfo_rooty() - tw.winfo_height() - 5
        tw.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()


class SMPCBlock:
    def __init__(self, raw):
        d = raw.split("|")
        self.name, self.opcode, self.cat = d[0], d[1], d[2]
        self.use_r, self.use_c, self.color = d[3] == "1", d[4] == "1", d[5]
        self.desc = d[6] if len(d) > 6 else ""
        self.r_val, self.c_val = 0, 0
        self.frame = None


class SMPCStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("SMPC MK6 Studio")
        self.root.geometry("1500x920")
        self.root.configure(bg="#050505")
        self.font_name = load_custom_font()
        self.isa = [SMPCBlock(s) for s in ISA_DATA]
        self.program, self.ram = [], [0] * 32
        self.pc, self.op1, self.op2, self.alu = 0, 0, 0, 0
        self.is_running, self.drag_idx = False, None
        self.view_mode = tk.StringVar(value="GUIDE")
        self.setup_gui()

    def setup_gui(self):
        hbar = tk.Frame(self.root, bg="#111", height=50)
        hbar.pack(side="top", fill="x")
        self.auto_btn = tk.Button(hbar, text="▶ AUTO RUN", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"),
                                  width=12, command=self.sim_auto)
        self.auto_btn.pack(side="left", padx=(20, 5), pady=10)
        self.step_btn = tk.Button(hbar, text="↷ STEP ONE", bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                                  width=12, command=self.sim_step)
        self.step_btn.pack(side="left", padx=5)
        tk.Button(hbar, text="⏹ RESET", bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), width=10,
                  command=self.sim_reset).pack(side="left", padx=5)
        tk.Button(hbar, text="💾 SAVE CODE", bg="#9b59b6", fg="white", font=("Arial", 10, "bold"), width=12,
                  command=self.file_save).pack(side="left", padx=(40, 5))
        tk.Button(hbar, text="📁 LOAD CODE", bg="#f39c12", fg="white", font=("Arial", 10, "bold"), width=12,
                  command=self.file_load).pack(side="left", padx=5)
        main = tk.Frame(self.root, bg="#050505")
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(1, weight=1);
        main.grid_columnconfigure(2, minsize=520);
        main.grid_rowconfigure(0, weight=1)
        pal_f = tk.Frame(main, bg="#121212", width=180)
        pal_f.grid(row=0, column=0, sticky="nsw")
        pal_c = tk.Canvas(pal_f, bg="#121212", width=160, highlightthickness=0)
        pal_sb = ttk.Scrollbar(pal_f, orient="vertical", command=pal_c.yview)
        self.pal_box = tk.Frame(pal_c, bg="#121212")
        pal_c.create_window((0, 0), window=self.pal_box, anchor="nw", width=160)
        pal_c.configure(yscrollcommand=pal_sb.set);
        pal_c.pack(side="left", fill="both", expand=True);
        pal_sb.pack(side="right", fill="y")
        self.pal_box.bind("<Configure>", lambda e: pal_c.configure(scrollregion=pal_c.bbox("all")))
        for c in ["CONTROL", "I/O", "MATH", "LOGIC", "MEMORY"]:
            tk.Label(self.pal_box, text=c, bg="#121212", fg="#555", font=("Arial", 8, "bold")).pack(pady=(12, 2))
            for i in self.isa:
                if i.cat == c:
                    btn = tk.Button(self.pal_box, text=i.name, bg=i.color, fg="white", font=("Arial", 8, "bold"),
                                    command=lambda x=i: self.add_step(x))
                    btn.pack(fill="x", padx=15, pady=1);
                    ToolTip(btn, i.desc)
        work_f = tk.Frame(main, bg="#000")
        work_f.grid(row=0, column=1, sticky="nsew")
        self.work_c = tk.Canvas(work_f, bg="#000", highlightthickness=0)
        work_sb = ttk.Scrollbar(work_f, orient="vertical", command=self.work_c.yview)
        self.work_box = tk.Frame(self.work_c, bg="#000")
        self.work_c.create_window((0, 0), window=self.work_box, anchor="nw", width=500)
        self.work_c.configure(yscrollcommand=work_sb.set);
        self.work_c.pack(side="left", fill="both", expand=True);
        work_sb.pack(side="right", fill="y")
        self.work_box.bind("<Configure>", lambda e: self.work_c.configure(scrollregion=self.work_c.bbox("all")))
        right = tk.Frame(main, bg="#050505", width=520)
        right.grid(row=0, column=2, sticky="nsew", padx=15)
        lcd_f = tk.Frame(right, bg="#000", bd=2, relief="sunken")
        lcd_f.pack(fill="x", pady=20)
        self.lcd = tk.Label(lcd_f, text="00000", bg="#000", fg="#0f0", font=(self.font_name, 64))
        self.lcd.pack(pady=10)
        self.reg_lbl = tk.Label(right, text="OP1: 0 | OP2: 0 | ALU: 0", bg="#050505", fg="#666",
                                font=("Consolas", 14, "bold"))
        self.reg_lbl.pack()
        tk.Label(right, text="SELECT SECONDARY VIEW", bg="#050505", fg="#444", font=("Arial", 7, "bold")).pack(
            pady=(20, 5))
        t_bar = tk.Frame(right, bg="#111", padx=2, pady=2)
        t_bar.pack(fill="x")
        tk.Radiobutton(t_bar, text="PAINT GUIDE", variable=self.view_mode, value="GUIDE", indicatoron=0, bg="#222",
                       fg="white", selectcolor="#9966FF", font=("Arial", 9, "bold"), command=self.switch_view).pack(
            side="left", expand=True, fill="x")
        tk.Radiobutton(t_bar, text="RAM MONITOR", variable=self.view_mode, value="RAM", indicatoron=0, bg="#222",
                       fg="white", selectcolor="#4C97FF", font=("Arial", 9, "bold"), command=self.switch_view).pack(
            side="left", expand=True, fill="x")
        self.view_container = tk.Frame(right, bg="#050505")
        self.view_container.pack(fill="both", expand=True, pady=10)
        self.ram_view = tk.Frame(self.view_container, bg="#000")
        self.ram_labels = []
        for i in range(32):
            r, c = divmod(i, 4);
            l = tk.Label(self.ram_view, text=f"R{i:02}: 0", bg="#000", fg="#2a2a2a", font=("Consolas", 10), width=12,
                         anchor="w")
            l.grid(row=r, column=c, padx=1, pady=1);
            self.ram_labels.append(l)
        self.guide_view = tk.Frame(self.view_container, bg="#000")
        self.guide_canv = tk.Canvas(self.guide_view, bg="#000", highlightthickness=0)
        self.g_vsb = ttk.Scrollbar(self.guide_view, orient="vertical", command=self.guide_canv.yview);
        self.g_hsb = ttk.Scrollbar(self.guide_view, orient="horizontal", command=self.guide_canv.xview)
        self.guide_canv.configure(yscrollcommand=self.g_vsb.set, xscrollcommand=self.g_hsb.set);
        self.g_vsb.pack(side="right", fill="y");
        self.g_hsb.pack(side="bottom", fill="x");
        self.guide_canv.pack(side="left", fill="both", expand=True)
        self.switch_view()

    def switch_view(self):
        self.ram_view.pack_forget();
        self.guide_view.pack_forget()
        if self.view_mode.get() == "GUIDE":
            self.guide_view.pack(fill="both", expand=True); self.draw_guide()
        else:
            self.ram_view.pack(fill="x", pady=10); self.refresh_stats()

    def add_step(self, t):
        obj = SMPCBlock(
            f"{t.name}|{t.opcode}|{t.cat}|{'1' if t.use_r else '0'}|{'1' if t.use_c else '0'}|{t.color}|{t.desc}")
        self.program.append(obj);
        self.refresh_work()

    def refresh_work(self):
        for child in self.work_box.winfo_children(): child.destroy()
        for idx, i in enumerate(self.program):
            f = tk.Frame(self.work_box, bg=i.color, padx=10, pady=6);
            f.pack(fill="x", padx=15, pady=3);
            i.frame = f
            dl = tk.Label(f, text=f"{idx:02} {i.name}", bg=i.color, fg="white", font=("Arial", 11, "bold"), width=9,
                          cursor="fleur")
            dl.pack(side="left");
            dl.bind("<Button-1>", lambda e, x=idx: self.drag_set(x));
            dl.bind("<B1-Motion>", self.drag_do);
            dl.bind("<ButtonRelease-1>", self.drag_end);
            ToolTip(dl, i.desc)
            if i.use_r:
                tk.Label(f, text="RAM:", bg=i.color, fg="white", font=("Arial", 8)).pack(side="left", padx=(10, 0))
                rv = tk.Entry(f, width=3, bg="#111", fg="white", bd=0);
                rv.insert(0, str(i.r_val));
                rv.pack(side="left", padx=3)
                rv.bind("<KeyRelease>", lambda e, s=i, w=rv: self.up_val(s, 'r', w.get()))
            if i.use_c:
                tk.Label(f, text="VAL:", bg=i.color, fg="white", font=("Arial", 8)).pack(side="left", padx=(10, 0))
                cv = tk.Entry(f, width=7, bg="#111", fg="white", bd=0);
                cv.insert(0, str(i.c_val));
                cv.pack(side="left", padx=3)
                cv.bind("<KeyRelease>", lambda e, s=i, w=cv: self.up_val(s, 'c', w.get()))
            tk.Button(f, text="✕", bg="#000", fg="#444", bd=0, command=lambda x=i: self.del_step(x)).pack(side="right")
        self.draw_guide()

    def drag_set(self, i):
        self.drag_idx = i

    def drag_do(self, e):
        if self.drag_idx is None: return
        y = e.y_root - self.work_box.winfo_rooty();
        tgt = max(0, min(len(self.program) - 1, y // 44))
        if tgt != self.drag_idx: self.program.insert(tgt, self.program.pop(
            self.drag_idx)); self.drag_idx = tgt; self.refresh_work()

    def drag_end(self, e):
        self.drag_idx = None; self.refresh_work()

    def up_val(self, i, m, v):
        try:
            n = int(v)
            if m == 'r':
                i.r_val = n % 32
            else:
                i.c_val = n % 256
            self.draw_guide()
        except:
            pass

    def del_step(self, i):
        self.program.remove(i); self.refresh_work()

    def file_save(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if f:
            data = [{"name": i.name, "r": i.r_val, "c": i.c_val} for i in self.program]
            with open(f, 'w') as j: json.dump(data, j)

    def file_load(self):
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if f:
            with open(f, 'r') as j:
                data = json.load(j);
                self.program = []
                for d in data:
                    t = next(i for i in self.isa if i.name == d["name"])
                    obj = SMPCBlock(
                        f"{t.name}|{t.opcode}|{t.cat}|{'1' if t.use_r else '0'}|{'1' if t.use_c else '0'}|{t.color}|{t.desc}")
                    obj.r_val, obj.c_val = d["r"], d["c"];
                    self.program.append(obj)
            self.refresh_work()

    def sim_reset(self):
        self.is_running, self.pc = False, 0
        self.op1, self.op2, self.alu = 0, 0, 0
        self.ram = [0] * 32;
        self.lcd.config(text="00000", fg="#0f0")
        self.auto_btn.config(state="normal");
        self.step_btn.config(state="normal")
        self.refresh_stats();
        self.draw_guide()
        for i in self.program:
            if i.frame: i.frame.config(highlightthickness=0)

    def sim_auto(self):
        if not self.program: return
        self.is_running = True;
        self.auto_btn.config(state="disabled");
        self.step_btn.config(state="disabled");
        self.sim_tick(auto=True)

    def sim_step(self):
        if not self.program: return
        self.sim_tick(auto=False)

    def refresh_stats(self):
        self.reg_lbl.config(text=f"OP1: {self.op1} | OP2: {self.op2} | ALU: {self.alu}")
        for idx, lbl in enumerate(self.ram_labels):
            v = self.ram[idx];
            lbl.config(text=f"R{idx:02}: {v}", fg="#0f0" if v > 0 else "#2a2a2a")

    def err_halt(self):
        self.is_running = False;
        self.lcd.config(text="ERR", fg="red")
        self.auto_btn.config(state="normal");
        self.step_btn.config(state="normal")
        messagebox.showerror("OVERFLOW", "Integer Limit Exceeded! (0-65535)")

    def sim_tick(self, auto=False):
        if self.pc >= len(self.program):
            self.is_running = False;
            self.auto_btn.config(state="normal");
            self.step_btn.config(state="normal");
            return
        for instr in self.program: instr.frame.config(highlightthickness=0)
        curr = self.program[self.pc];
        curr.frame.config(highlightbackground="white", highlightthickness=3);
        self.draw_guide(h_idx=self.pc)
        n, nxt = curr.name, self.pc + 1
        if n == "HLT":
            self.is_running = False;
            self.auto_btn.config(state="normal");
            self.step_btn.config(state="normal");
            return
        elif n == "JMP":
            nxt = curr.c_val
        elif n == "JZ":
            nxt = curr.c_val if self.alu == 0 else nxt
        elif n == "INP1":
            v = simpledialog.askinteger("IN", "Input OP1:");
            self.op1 = (v or 0)
            if self.op1 > 65535 or self.op1 < 0: return self.err_halt()
        elif n == "INP2":
            v = simpledialog.askinteger("IN", "Input OP2:");
            self.op2 = (v or 0)
            if self.op2 > 65535 or self.op2 < 0: return self.err_halt()
        elif n == "OUTS":
            self.lcd.config(text=str(self.alu).zfill(5))
        elif n == "OUTR":
            self.lcd.config(text=str(self.ram[curr.r_val]).zfill(5))
        elif n == "ADD":
            self.alu = self.op1 + self.op2
        elif n == "SUB":
            self.alu = self.op1 - self.op2
        elif n == "MUL":
            self.alu = self.op1 * self.op2
        elif n == "DIV":
            self.alu = (self.op1 // self.op2) if self.op2 != 0 else 0
        elif n == "AND":
            self.alu = self.op1 & self.op2
        elif n == "OR":
            self.alu = self.op1 | self.op2
        elif n == "XOR":
            self.alu = self.op1 ^ self.op2
        elif n == "NOT1":
            self.alu = ~self.op1
        elif n == "NOT2":
            self.alu = ~self.op2
        elif n == "LDI1":
            self.op1 = curr.c_val
        elif n == "LDI2":
            self.op2 = curr.c_val
        elif n == "LDRO":
            self.alu = self.ram[curr.r_val]
        elif n == "LDR1":
            self.op1 = self.ram[curr.r_val]
        elif n == "LDR2":
            self.op2 = self.ram[curr.r_val]
        elif n == "STRO":
            self.ram[curr.r_val] = self.alu
        elif n == "STR1":
            self.ram[curr.r_val] = self.op1
        elif n == "STR2":
            self.ram[curr.r_val] = self.op2
        elif n == "CLR":
            self.ram[curr.r_val] = 0
        elif n == "OPI1":
            self.op1 = self.alu
        elif n == "OPI2":
            self.op2 = self.alu

        if self.alu > 65535 or self.alu < -32768: return self.err_halt()
        if n.startswith("NOT"): self.alu &= 0xFFFF
        if self.alu < 0: self.alu = 0

        self.pc = nxt;
        self.refresh_stats()
        if auto and self.is_running: self.root.after(420, lambda: self.sim_tick(auto=True))

    def draw_guide(self, h_idx=None):
        if self.view_mode.get() != "GUIDE": return
        self.guide_canv.delete("all")
        if not self.program: return
        bh, bw, gap = 12, 18, 25
        card_h = (8 + 5 + 6) * bh + (gap * 3) + 100
        card_w = len(self.program) * (bw + 8) + 100
        self.guide_canv.configure(scrollregion=(0, 0, card_w, card_h))
        for i, instr in enumerate(self.program):
            x = 40 + i * (bw + 8)
            if h_idx == i: self.guide_canv.create_rectangle(x - 4, 10, x + bw + 4, card_h - 10, outline="#0f0", width=2)
            self.bits(x, 40, bin(instr.c_val)[2:].zfill(8), 8, bw, bh, "#1a1a1a")
            self.bits(x, 40 + (8 * bh) + gap, bin(instr.r_val)[2:].zfill(5), 5, bw, bh, "#111")
            self.bits(x, 40 + (13 * bh) + (gap * 2), instr.opcode, 6, bw, bh, "#080808")

    def bits(self, x, y_start, bs, cnt, w, h, bg):
        rev = bs[::-1]
        for i in range(cnt):
            clr = "white" if (i < len(rev) and rev[i] == '1') else bg
            y = y_start + ((cnt - 1 - i) * h)
            self.guide_canv.create_rectangle(x, y, x + w, y + h - 1, fill=clr, outline="#000")


if __name__ == "__main__":
    app_root = tk.Tk();
    SMPCStudio(app_root);
    app_root.mainloop()

import tkinter as tk


def show_guide(parent):
    guide_win = tk.Toplevel(parent)
    guide_win.title("Guide")
    guide_win.geometry("700x600")
    guide_win.configure(bg="#1a1a1a")

    help_text = """
MACRO COMMAND LIST
---------------------------------

loop [n]            : Repeat script n times (-1 = infinite)
stop                : stop the program
jump [n]            : jump lines (-n go back , n skip)
hotkey [sequence]   : [ctrl c, ctrl v , win r , alt shift tab] etc
text [message]      : any line want to type. 
                    : exmple : text hellow WORLD
print [message]     : print message in log

------- wait/delay/condition/action ------

wait [time] : Wait time supports: ms , s, m
            : example : wait 1000  or wait 1000ms
                      : wait 1s
                      : wait 1m30s

wait random [a] [b] : Random delay between a and b

wait [color condition] [area] [tolerance] [threshold] [jump] [timeout]
example : wait color 500 500 #ffffff
        : wait color 500 500 #ffffff 5s
        : wait color center #ffffff tolerance 10
        : wait color center #ffffff tolerance 10 time 10s
        : wait color center #ffffff tolerance 10 jump 2 10s
        : wait color center #272727,#ee0000,#dd1111 area 5 tolerance 10 10s
        : wait color 500 300 #ff0000,#ee0000 area 5 tolerance 15 threshold 10 5m

---------------- Keyboard ----------------

tap [key]   : Press and release key

press [key] : Hold key
end [key]   : Release key

---------------- Mouse ----------------

press mouse [left/right/middle] : Hold mouse button
end mouse [left/right/middle]   : Release mouse button

click [left/right/middle]       : Mouse Single click
dclick [left/right/middle]      : Double click

move [x] [y]                    : Move mouse to position
scroll [value]                  : Scroll mouse wheel (e.g. 500 or -500)

"""

    text_widget = tk.Text(
        guide_win,
        bg="#1a1a1a",
        fg="white",
        font=("Consolas", 10),
        wrap="word",
        relief="flat",
        padx=15,
        pady=15
    )

    text_widget.insert("1.0", help_text)
    text_widget.config(state="disabled")
    text_widget.pack(fill="both", expand=True)
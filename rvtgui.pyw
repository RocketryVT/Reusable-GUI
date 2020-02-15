from tkinter import *
from tkinter.ttk import *
from tkinter.font import Font
from tkinter.scrolledtext import ScrolledText
import time
from datetime import datetime
import numpy
import os
import socket
import re
import copy

CONSOLE_FONT = ("Consolas", 14)

set_of_nodes = set()

button_commands = [
    "system fortune | cowsay",
    "system figlet RVT",
    "system df -h",
    "system free -th",
    "read data",
    "print whitelist",
    "set readiness 0",
    "set readiness 10",
    "close solenoid",
    "open solenoid",
    "close ignition valve",
    "open ignition valve",
    "retract linear actuator",
    "extend linear actuator",
    "close vent valve",
    "open vent valve",
    "crack vent valve",
    "fire ematch",
    "abort"
]

def make_command_button(master, window, command, row):
    command = copy.copy(command)
    row = copy.copy(row)
    Button(window,
        text=command,
        command=lambda: master.send_command(command),
        width=25
    ).pack(side=TOP, padx=5, pady=2)

def dict2str(dict, debug, info, warn, error, fatal,
    show_level=False, show_time=False, show_node=False):

    level = dict["level"]
    if level == "DEBUG" and not debug:
        return ""
    if level == "INFO" and not info:
        return ""
    if level == "WARN" and not warn:
        return ""
    if level == "ERROR" and not error:
        return ""
    if level == "FATAL" and not fatal:
        return ""

    ret = dict['content'] + "\n"
    if show_level or show_time or show_node:
        ret = ": " + ret
    header = []
    if show_level:
        header.append(("[" + level + "]").ljust(7))
    if show_time:
        header.append("[" + dict['stamp'] + "]")
    if show_node:
        header.append("[" + dict['node'] + "]")

    return ' '.join(header) + ret


def make_focus(window):
    window.attributes('-topmost', 1)
    window.attributes('-topmost', 0)
    window.focus()

def parse_message(string):

    pattern = re.compile(
        "\[\w+\]\s+\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\] \[.+\]\:[\S\s]+?(?=(?:\[\w+\]|$))")
    text = re.compile("\]:(\s|$)([\S\s]+)")
    meta = re.compile("\[(.*?)\]")

    messages = pattern.findall(string);

    msgdicts = []
    for msg in messages:
        content = text.findall(msg)[0][1]
        if content.count('\n') is 1:
            content = content.rstrip() # to combat spurious \n

        metadata = meta.findall(msg)
        (level, datestr, node) = metadata[0:3]
        dict = {}
        dict["content"] = content
        dict["level"] = level
        dict["stamp"] = datestr
        dict["node"] = node
        if node not in set_of_nodes:
            set_of_nodes.add(node)
            print("New node: " + str(set_of_nodes))

        msgdicts.append(dict)

    return msgdicts

class MainWindow(Tk):

    def __init__(self):

        self.delay = 50
        self.buffer = list([])
        self.socket = None

        if not os.path.exists("logs"):
            os.mkdir("logs")

        filename = "logs/LOG-" + str(datetime.utcnow()
            ).replace(" ", "-").replace(":", "-") + ".txt"
        self.logfile = open(filename, 'wb')

        Tk.__init__(self)
        self.style = Style()
        self.style.theme_use("xpnative")
        self.style.configure("console", foreground="black", background="white")
        self.title("Rocketry@VT Ground Control v2020-02-15a")
        self.wm_iconbitmap("logo_nowords_cZC_icon.ico")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        make_focus(self)
        self.update_idletasks()
        width = 1400
        height = 800
        self.geometry('{}x{}'.format(width, height))
        self.state('zoomed')

        bottom_frame = Frame(self)
        sidebar = Frame(self)
        top_frame = Frame(self)
        self.status_text = Label(self)
        self.set_status("Disconnected.")

        for i in range(0, len(button_commands)):
            make_command_button(self, sidebar, button_commands[i], i)
        sidebar.pack(side=LEFT, fill=BOTH)
        self.status_text.pack(side=TOP, fill='x', padx=3, pady=6)

        Label(top_frame, text="IP Address: ").pack(side = LEFT, padx=3, pady=3)
        self.addrInputBox = Entry(top_frame)
        self.addrInputBox.insert(0, "gandalf.local")
        self.addrInputBox.pack(side = LEFT, padx=3, pady=3)
        Label(top_frame, text="Port: ").pack(side = LEFT, padx=3, pady=3)
        self.portInputBox = Entry(top_frame)
        self.portInputBox.insert(0, "8001")
        self.portInputBox.pack(side = LEFT, padx=3, pady=3)
        self.connectButton = Button(top_frame, text='Connect',
            command=lambda: self.tcp_connect(self.addrInputBox.get(), self.portInputBox.get()))
        self.connectButton.pack(side = LEFT, padx=3, pady=3)
        clearButton = Button(top_frame, text='Clear',
            command=lambda: self.clear_console())
        clearButton.pack(side = LEFT, padx=3, pady=3)

        self.snap_to_bottom = BooleanVar()
        self.snap_to_bottom.set(True)
        self.show_debug = BooleanVar()
        self.show_debug.set(False)
        self.show_debug.trace('w', self.redraw_console)
        self.show_info = BooleanVar()
        self.show_info.set(True)
        self.show_info.trace('w', self.redraw_console)
        self.show_warn = BooleanVar()
        self.show_warn.set(True)
        self.show_warn.trace('w', self.redraw_console)
        self.show_error = BooleanVar()
        self.show_error.set(True)
        self.show_error.trace('w', self.redraw_console)
        self.show_fatal = BooleanVar()
        self.show_fatal.set(True)
        self.show_fatal.trace('w', self.redraw_console)
        self.show_level = BooleanVar()
        self.show_level.set(True)
        self.show_level.trace('w', self.redraw_console)
        self.show_time = BooleanVar()
        self.show_time.set(True)
        self.show_time.trace('w', self.redraw_console)
        self.show_node = BooleanVar()
        self.show_node.set(True)
        self.show_node.trace('w', self.redraw_console)

        Checkbutton(top_frame, text="Snap to Bottom", var=self.snap_to_bottom,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Debug", var=self.show_debug,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Info", var=self.show_info,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Warn", var=self.show_warn,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Error", var=self.show_error,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Fatal", var=self.show_fatal,
            ).pack(side = LEFT, padx=3, pady=3)
        Checkbutton(top_frame, text="Levels", var=self.show_level,
            ).pack(side = RIGHT, padx=3, pady=3)
        Checkbutton(top_frame, text="Timestamp", var=self.show_time,
            ).pack(side = RIGHT, padx=3, pady=3)
        Checkbutton(top_frame, text="Nodes", var=self.show_node,
            ).pack(side = RIGHT, padx=3, pady=3)
        top_frame.pack(side=TOP, fill='x')

        self.textOutput = ScrolledText(self, wrap=WORD,
            width = 28*3, bg='#1A3747', fg='white',
            relief='flat', borderwidth=6, font=CONSOLE_FONT)
        self.textOutput.pack(fill=BOTH, expand=YES)
        self.textOutput.config(state=DISABLED)

        self.textOutput.tag_configure("DEBUG", foreground="#5D737E")
        self.textOutput.tag_configure("INFO", foreground="white")
        self.textOutput.tag_configure("WARN", foreground="#fffe00")
        self.textOutput.tag_configure("ERROR", foreground="#f08e00")
        self.textOutput.tag_configure("FATAL", foreground="#bb0000")

        self.textInputBox = Entry(bottom_frame, width=70)
        self.textInputBox.pack(padx=5, pady=5, fill=BOTH)
        bottom_frame.pack(side=BOTTOM, fill=BOTH)

        self.bind("<Return>", self.pressed_enter)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.begin_loop()

    def set_status(self, message):
        self.status_text['text'] = message

    def begin_loop(self):

        self.update()
        self.after(self.delay, self.begin_loop)

    def update(self):

        message = None

        if self.socket is not None:
            try:
                message = self.socket.recv(1024)
                message = message.decode()
            except:
                pass

        if message is not None:

            self.logfile.write(message.encode())
            self.logfile.flush()
            parsed = parse_message(message)
            for p in parsed:
                self.buffer.append(p)
                st = dict2str(p,
                    self.show_debug.get(),
                    self.show_info.get(),
                    self.show_warn.get(),
                    self.show_error.get(),
                    self.show_fatal.get(),
                    self.show_level.get(),
                    self.show_time.get(),
                    self.show_node.get())

                if st:
                    begin = "end-10c linestart"
                    end = "end-10c lineend"
                    self.textOutput.configure(state='normal')
                    self.textOutput.insert(END, st)
                    self.textOutput.configure(state='disabled')
                    if p['level'] == "DEBUG":
                        self.textOutput.tag_add("DEBUG", begin, end)
                    if p['level'] == "INFO":
                        self.textOutput.tag_add("INFO", begin, end)
                    if p['level'] == "WARN":
                        self.textOutput.tag_add("WARN", begin, end)
                    if p['level'] == "ERROR":
                        self.textOutput.tag_add("ERROR", begin, end)
                    if p['level'] == "FATAL":
                        self.textOutput.tag_add("FATAL", begin, end)

                    if self.snap_to_bottom.get():
                        self.textOutput.see(END)


    def tcp_connect(self, addr, port):

        self.set_status("Connecting...")
        self.socket = socket.socket()
        if self.connectButton["text"] == "Disconnect":
            self.connectButton.config(text="Connect")
            self.set_status("Disconnected.")
            return
        try:
            self.socket.connect((addr, int(port)))
        except Exception as e:
            self.set_status(str(e))
            return
        self.socket.setblocking(0)
        self.connectButton.config(text="Disconnect")
        self.set_status("Connected at {}:{}.".format(addr, port))

    def send_command(self, text):
        try:
            self.socket.sendall(text.encode())
        except:
            pass

    def pressed_enter(self, event):
        if self.focus_get() is self.textInputBox:
            self.send_command(self.textInputBox.get())
            self.textInputBox.delete(0, 'end')

    def clear_buffers(self):
        self.buffer.clear()

    def clear_console(self):
        self.textOutput.configure(state='normal')
        self.textOutput.delete('1.0', 'end')
        self.textOutput.configure(state='disabled')
        self.buffer = []

    def redraw_console(self, event=None, another=None, more=None):
        self.textOutput.configure(state='normal')
        self.textOutput.delete('1.0', 'end')
        self.textOutput.configure(state='disabled')
        for p in self.buffer:
            st = dict2str(p,
                self.show_debug.get(),
                self.show_info.get(),
                self.show_warn.get(),
                self.show_error.get(),
                self.show_fatal.get(),
                self.show_level.get(),
                self.show_time.get(),
                self.show_node.get())
            if st:
                begin = "end-10c linestart"
                end = "end-10c lineend"
                self.textOutput.configure(state='normal')
                self.textOutput.insert(END, st)
                self.textOutput.configure(state='disabled')
                if p['level'] == "DEBUG":
                    self.textOutput.tag_add("DEBUG", begin, end)
                if p['level'] == "INFO":
                    self.textOutput.tag_add("INFO", begin, end)
                if p['level'] == "WARN":
                    self.textOutput.tag_add("WARN", begin, end)
                if p['level'] == "ERROR":
                    self.textOutput.tag_add("ERROR", begin, end)
                if p['level'] == "FATAL":
                    self.textOutput.tag_add("FATAL", begin, end)

                if self.snap_to_bottom.get():
                    self.textOutput.see(END)


print("Starting R@VT control.")

MainWindow().mainloop()

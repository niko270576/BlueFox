#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Fox OS 2.0 - a complete desktop operating system that runs in a window.
Written in Python with Tkinter. Run it with:   python bluefox.py

No packages need to be installed. Everything Blue Fox does stays inside
Blue Fox: its files live in one data file (~/.bluefox_data.json) and
nothing on the host computer is changed unless YOU export a file to it.
"""

import base64
import calendar
import contextlib
import copy
import datetime
import io
import json
import math
import os
import platform
import queue
import random
import re
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
import webbrowser
from html.parser import HTMLParser
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

APP_NAME = "Blue Fox"
VERSION = "2.0"
DATA_FILE = os.path.join(os.path.expanduser("~"), ".bluefox_data.json")
HOME = "/home/user"
# When Blue Fox runs as the whole operating system (from the Blue Fox ISO / USB)
SESSION = os.environ.get("BLUEFOX_SESSION") == "1"
IS_LINUX = platform.system() == "Linux"
REAL_HOME = os.path.expanduser("~")


def have(cmd):
    return shutil.which(cmd) is not None


def sh(args, timeout=60, input_text=None):
    """Run a real program and return (exit code, output)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input_text)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)

# ════════════════════════════════════════════════════════════════════
#  Language (English by default, Greek available in Settings)
# ════════════════════════════════════════════════════════════════════
LANG = {"code": "en"}
LANGUAGES = {"en": "English", "el": "Ελληνικά"}


def _(text, **kw):
    """Translate a UI string. The Greek table EL is defined near the end of the file."""
    if LANG["code"] == "el":
        text = EL.get(text, text)
    return text.format(**kw) if kw else text


# Colour emoji can crash Tk on some systems, so use plain symbols there.
USE_EMOJI = platform.system() in ("Windows", "Darwin")

ICONS = {
    "prompt": ("🖥️", "C>"), "bash": ("💻", "$_"), "foxcode": ("🦊", "F>"),
    "files": ("📁", "▤"), "notepad": ("📝", "✎"), "calc": ("🧮", "±"),
    "paint": ("🎨", "▨"), "snake": ("🐍", "§"), "settings": ("⚙️", "☼"),
    "taskmgr": ("📊", "▥"), "calendar": ("📅", "▦"), "about": ("ℹ️", "i"),
    "web": ("🌐", "◎"), "store": ("🛍️", "⌂"), "firefox": ("🌍", "◉"), "brave": ("🦁", "◈"),
    "mines": ("💣", "✱"), "2048": ("🔢", "#"), "ttt": ("⭕", "✕"), "pong": ("🏓", "◐"),
    "python": ("🐍", "Py"), "turtle": ("🐢", "◭"), "image": ("🖼️", "▧"), "programs": ("🧰", "▦"),
    "folder": ("📁", "▣"), "file": ("📄", "▢"), "start": ("◆", "◆"),
    "power": ("⏻", "⏻"), "lock": ("🔒", "◉"), "restart": ("🔄", "↻"),
}


def icon(name):
    e, s = ICONS.get(name, ("•", "•"))
    return e if USE_EMOJI else s


UI_FONT = ("Segoe UI", 10)
UI_BOLD = ("Segoe UI", 10, "bold")
MONO = ("Consolas", 11) if platform.system() == "Windows" else ("DejaVu Sans Mono", 10)

THEMES = {
    "dark": dict(bg="#1e1e2e", fg="#cdd6f4", panel="#181825", title="#11111b", accent="#5ea8ff",
                 hover="#313244", entry="#313244", muted="#7f849c", taskbar="#11111b"),
    "light": dict(bg="#f5f5f5", fg="#1f1f1f", panel="#e8e8e8", title="#dadada", accent="#0b6ce0",
                  hover="#cfcfcf", entry="#ffffff", muted="#666666", taskbar="#e0e0e0"),
    "ocean": dict(bg="#0d1b2a", fg="#e0f0ff", panel="#0a1622", title="#06101a", accent="#3fa9f5",
                  hover="#1b3550", entry="#152a40", muted="#7f9bb5", taskbar="#06101a"),
}
THEME_NAMES = {"dark": "Dark", "light": "Light", "ocean": "Ocean blue"}

WALLPAPERS = {
    "Blue Fox": ("#04122e", "#1f6fd1"), "Ocean": ("#0f2027", "#2c5364"),
    "Sunset": ("#ff7e5f", "#2b1055"), "Aurora": ("#0b3d3d", "#3ad1a0"),
    "Forest": ("#0b3d0b", "#56ab2f"), "Night": ("#000000", "#434343"),
}

DEFAULT_SETTINGS = {
    "setup_done": False, "lang": "en", "theme": "dark",
    "wall1": "#04122e", "wall2": "#1f6fd1", "wall_image": "",
    "username": "user", "hostname": "bluefox", "password": "",
    "terminals": ["bash"], "browser": "firefox", "internet": True,
    "installed": [], "home_page": "https://duckduckgo.com/html/",
    "icons": {}, "icon_default": {}, "icon_pos": {}, "pinned": None, "desk_apps": None, "icon_style": "colorful",
}


# ════════════════════════════════════════════════════════════════════
#  Virtual file system (everything lives inside Blue Fox only)
# ════════════════════════════════════════════════════════════════════
def _dir(children=None):
    return {"type": "dir", "children": children or {}}


def _file(content=""):
    return {"type": "file", "content": content}


class VFS:
    def __init__(self, root=None):
        self.root = root if root else self.default()

    @staticmethod
    def default():
        return _dir({
            "home": _dir({"user": _dir({
                "Desktop": _dir({"Welcome.txt": _file(
                    "Welcome to Blue Fox!\n\n"
                    "* Double-click icons to open apps.\n"
                    "* Click the ◆ button (bottom left) for the Start menu.\n"
                    "* Get more games and apps from the Fox Store.\n"
                    "* Open a terminal and type 'help'.\n"
                    "* Settings lets you change language, password, wallpaper and more.\n")}),
                "Documents": _dir({"notes.txt": _file("My notes...\n")}),
                "Pictures": _dir(), "Music": _dir(), "Downloads": _dir(),
                "Code": _dir({"hello.py": _file(
                    'name = "Blue Fox"\nprint("Hello from", name)\n'
                    'for i in range(1, 6):\n    print(i, "x", i, "=", i * i)\n')}),
            })}),
            "apps": _dir(), "tmp": _dir(),
            "etc": _dir({"hostname": _file("bluefox\n"), "os-release": _file(
                'NAME="Blue Fox"\nVERSION="%s"\nID=bluefox\n' % VERSION)}),
        })

    @staticmethod
    def norm(path, cwd="/"):
        path = path.replace("\\", "/")
        if re.match(r"^[a-zA-Z]:", path):          # C:\something  ->  /something
            path = path[2:] or "/"
            if not path.startswith("/"):
                path = "/" + path
        if path.startswith("~"):
            path = HOME + path[1:]
        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path
        parts = []
        for p in path.split("/"):
            if p in ("", "."):
                continue
            if p == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(p)
        return "/" + "/".join(parts)

    @staticmethod
    def split(path):
        head, _sep, name = path.rstrip("/").rpartition("/")
        return (head or "/"), name

    def get(self, path):
        node = self.root
        for p in [x for x in path.split("/") if x]:
            if node["type"] != "dir" or p not in node["children"]:
                return None
            node = node["children"][p]
        return node

    def is_dir(self, path):
        n = self.get(path)
        return bool(n) and n["type"] == "dir"

    def is_file(self, path):
        n = self.get(path)
        return bool(n) and n["type"] == "file"

    def listdir(self, path):
        n = self.get(path)
        if not n or n["type"] != "dir":
            raise NotADirectoryError(path)
        ch = n["children"]
        return sorted(ch.keys(), key=lambda k: (ch[k]["type"] != "dir", k.lower()))

    def _parent(self, path):
        parent, name = self.split(path)
        pn = self.get(parent)
        if not pn or pn["type"] != "dir":
            raise FileNotFoundError(parent)
        if not name:
            raise PermissionError("/")
        return pn, name

    def mkdir(self, path, parents=False):
        if parents:
            cur = "/"
            for p in [x for x in path.split("/") if x]:
                cur = self.norm(p, cur)
                if not self.get(cur):
                    self.mkdir(cur)
            return
        pn, name = self._parent(path)
        if name in pn["children"]:
            raise FileExistsError(path)
        pn["children"][name] = _dir()

    def write(self, path, content, append=False):
        pn, name = self._parent(path)
        node = pn["children"].get(name)
        if node and node["type"] == "dir":
            raise IsADirectoryError(path)
        if node and append:
            if self.is_binary(node):
                raise ValueError(_("cannot append text to a binary file"))
            node["content"] += content
        else:
            pn["children"][name] = _file(content)

    def touch(self, path):
        if not self.get(path):
            self.write(path, "")

    def read(self, path):
        n = self.get(path)
        if not n:
            raise FileNotFoundError(path)
        if n["type"] == "dir":
            raise IsADirectoryError(path)
        if self.is_binary(n):
            raise ValueError(_("this is a binary file (e.g. a picture) and cannot be shown as text"))
        return n["content"]

    @staticmethod
    def is_binary(node):
        return node.get("b64") is not None

    @staticmethod
    def size(node):
        if node["type"] == "dir":
            return 0
        if node.get("b64") is not None:
            return len(base64.b64decode(node["b64"]))
        return len(node["content"].encode("utf-8"))

    def write_bytes(self, path, data):
        try:
            self.write(path, data.decode("utf-8"))
            return
        except UnicodeDecodeError:
            pass
        pn, name = self._parent(path)
        old = pn["children"].get(name)
        if old and old["type"] == "dir":
            raise IsADirectoryError(path)
        pn["children"][name] = {"type": "file", "content": "", "b64": base64.b64encode(data).decode("ascii")}

    def get_bytes(self, path):
        n = self.get(path)
        if not n:
            raise FileNotFoundError(path)
        if n["type"] == "dir":
            raise IsADirectoryError(path)
        if self.is_binary(n):
            return base64.b64decode(n["b64"])
        return n["content"].encode("utf-8")

    def remove(self, path, recursive=False):
        pn, name = self._parent(path)
        node = pn["children"].get(name)
        if not node:
            raise FileNotFoundError(path)
        if node["type"] == "dir" and node["children"] and not recursive:
            raise OSError(_("folder is not empty"))
        del pn["children"][name]

    def move(self, src, dst, keep=False):
        node = self.get(src)
        if not node:
            raise FileNotFoundError(src)
        if self.is_dir(dst):
            dst = self.norm(self.split(src)[1], dst)
        if dst == src or dst.startswith(src.rstrip("/") + "/"):
            raise OSError(_("invalid destination"))
        pn, name = self._parent(dst)
        pn["children"][name] = copy.deepcopy(node)
        if not keep:
            self.remove(src, recursive=True)

    def walk_find(self, start, pattern):
        res = []

        def rec(path, node):
            for k, v in node.get("children", {}).items():
                p = self.norm(k, path)
                if pattern.lower() in k.lower():
                    res.append(p)
                if v["type"] == "dir":
                    rec(p, v)
        n = self.get(start)
        if n and n["type"] == "dir":
            rec(start, n)
        return res

    def free_name(self, dest, name):
        target = self.norm(name, dest)
        base, ext = os.path.splitext(name)
        i = 2
        while self.get(target):
            target = self.norm(f"{base} ({i}){ext}", dest)
            i += 1
        return target


def human_size(n):
    for unit in ("bytes", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


def err_text(e):
    names = {FileNotFoundError: _("no such file or folder"), FileExistsError: _("already exists"),
             IsADirectoryError: _("is a folder"), NotADirectoryError: _("not a folder"),
             PermissionError: _("not allowed")}
    for k, v in names.items():
        if isinstance(e, k):
            return f"{e}: {v}" if str(e) else v
    return str(e)


# ════════════════════════════════════════════════════════════════════
#  Internet helpers
# ════════════════════════════════════════════════════════════════════
UA = "Mozilla/5.0 (X11; BlueFox 2.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def http_get(url, limit=4_000_000, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,el;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        data = r.read(limit)
        return data, r.headers.get("Content-Type", ""), r.geturl()


def decode_html(data, ctype):
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I) or \
        re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', data[:3000], re.I)
    enc = m.group(1) if m else "utf-8"
    if isinstance(enc, bytes):
        enc = enc.decode("ascii", "ignore")
    try:
        return data.decode(enc, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def fix_url(text):
    text = text.strip()
    if not text:
        return ""
    if re.match(r"^[a-z]+://", text, re.I):
        return text
    if " " in text or "." not in text:
        return "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(text)
    return "https://" + text


def online_check(timeout=3):
    for host in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            socket.create_connection(host, timeout=timeout).close()
            return True
        except OSError:
            continue
    return False


class PageParser(HTMLParser):
    """Turns HTML into text segments: (text, kind, href)."""
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "header",
             "footer", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote", "form", "nav", "hr"}
    SKIP = {"script", "style", "head", "noscript", "svg", "template", "iframe"}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.out = []
        self.title = ""
        self._skip = 0
        self._in_title = False
        self._href = None
        self._heading = False
        self._pre = False

    def nl(self, n=1):
        txt = "".join(t for t, _k, _h in self.out[-3:])
        if not txt.endswith("\n" * n):
            self.out.append(("\n", None, None))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP:
            self._skip += 1
            return
        if tag in self.BLOCK:
            self.nl()
        if tag in ("h1", "h2", "h3"):
            self._heading = True
        if tag == "li":
            self.out.append(("  • ", None, None))
        if tag == "pre":
            self._pre = True
        if tag == "a" and a.get("href"):
            href = a["href"]
            if "duckduckgo.com/l/?" in href or href.startswith("/l/?"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                href = q.get("uddg", [href])[0]
            self._href = urllib.parse.urljoin(self.base, href)
        if tag == "img" and a.get("alt"):
            self.out.append((f"[{a['alt']}]", "muted", None))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if tag in ("h1", "h2", "h3"):
            self._heading = False
            self.nl(2)
        if tag == "a":
            self._href = None
        if tag == "pre":
            self._pre = False
        if tag in self.BLOCK:
            self.nl()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip:
            return
        if not self._pre:
            data = re.sub(r"\s+", " ", data)
        if not data.strip() and data != " ":
            return
        kind = "link" if self._href else ("h" if self._heading else None)
        self.out.append((data, kind, self._href))


def find_host_browser(name):
    """Look for the real Firefox / Brave installed on this computer."""
    system = platform.system()
    env = os.environ.get
    cands = []
    if name == "firefox":
        if system == "Windows":
            cands = [os.path.join(env(v, ""), "Mozilla Firefox", "firefox.exe")
                     for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        elif system == "Darwin":
            cands = ["/Applications/Firefox.app/Contents/MacOS/firefox"]
        cands += [shutil.which("firefox"), shutil.which("firefox-esr")]
    elif name == "brave":
        if system == "Windows":
            cands = [os.path.join(env(v, ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
                     for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        elif system == "Darwin":
            cands = ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
        cands += [shutil.which("brave-browser"), shutil.which("brave")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


HOST_BROWSERS = {
    "firefox": ("Firefox", "https://www.mozilla.org/firefox/new/"),
    "brave": ("Brave", "https://brave.com/download/"),
}


# ════════════════════════════════════════════════════════════════════
#  Python runner (used by the Python app and the "python" command)
# ════════════════════════════════════════════════════════════════════
class _Writer(io.TextIOBase):
    def __init__(self, fn):
        self.fn = fn

    def write(self, s):
        self.fn(s)
        return len(s)


def run_python(code, write, ask, filename="<blue fox>"):
    """Run Python code; print() goes to write(), input() asks with a dialog."""
    def _input(prompt=""):
        write(str(prompt))
        ans = ask(str(prompt))
        if ans is None:
            raise KeyboardInterrupt(_("input cancelled"))
        write(ans + "\n")
        return ans
    g = {"__name__": "__main__", "input": _input}
    w = _Writer(write)
    try:
        with contextlib.redirect_stdout(w), contextlib.redirect_stderr(w):
            exec(compile(code, filename, "exec"), g)  # noqa: S102  (the user's own code)
        return True
    except SystemExit:
        return True
    except BaseException:  # noqa
        tb = traceback.format_exc().splitlines()
        tb = [tb[0]] + [ln for ln in tb[1:] if "bluefox" not in ln.lower() or filename in ln]
        write("\n".join(tb[-6:]) + "\n", "err") if _accepts_tag(write) else write("\n".join(tb[-6:]) + "\n")
        return False


def _accepts_tag(fn):
    try:
        return fn.__code__.co_argcount >= 2
    except AttributeError:
        return True


def safe_calc(expr):
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", ".")
    allowed = {k: getattr(math, k) for k in ("sqrt", "sin", "cos", "tan", "log", "log10", "pi", "e",
                                             "floor", "ceil", "factorial", "radians")}
    allowed.update(abs=abs, round=round)
    if any(c in expr for c in "_[]{};:'\"\\") or "lambda" in expr:
        raise ValueError(_("invalid expression"))
    res = eval(compile(expr, "<calc>", "eval"), {"__builtins__": {}}, allowed)  # noqa: S307
    if isinstance(res, float) and res.is_integer() and abs(res) < 1e15:
        return int(res)
    return round(res, 10) if isinstance(res, float) else res


# ════════════════════════════════════════════════════════════════════
#  Shell: one engine, three command languages ("dialects")
#     prompt  - classic prompt style   (dir, cls, type, del ...)
#     bash    - bash style              (ls, clear, cat, rm ...)
#     foxcode - Blue Fox Code: same power, our own words (look, wipe, show, trash ...)
# ════════════════════════════════════════════════════════════════════
#  (names, method, usage, description)
BASH_CMDS = [
    ("help", "help", "", "show this help"),
    ("ls", "ls", "[-a] [-l] [folder]", "list files"),
    ("cd", "cd", "<folder>", "change folder (.. = up, ~ = home)"),
    ("pwd", "pwd", "", "show the current folder"),
    ("mkdir", "mkdir", "[-p] <name>", "make a folder"),
    ("touch", "touch", "<file>", "make an empty file"),
    ("cat", "cat", "<file>", "show a file"),
    ("echo", "echo", "<text> [> file]", "print text (> or >> writes to a file)"),
    ("rm", "rm", "[-r] <name>", "delete"),
    ("rmdir", "rmdir", "<folder>", "delete an empty folder"),
    ("mv", "mv", "<from> <to>", "move or rename"),
    ("cp", "cp", "<from> <to>", "copy"),
    ("tree", "tree", "[folder]", "show the folder tree"),
    ("find", "find", "<word>", "search file names"),
    ("grep", "grep", "<word> <file>", "search inside a file"),
    ("head", "head", "[-n] <file>", "first lines of a file"),
    ("tail", "tail", "[-n] <file>", "last lines of a file"),
    ("wc", "wc", "<file>", "count lines, words and characters"),
    ("nano", "edit", "<file>", "edit a file in Notepad"),
    ("open / xdg-open", "open", "<app or file>", "open an app or a file"),
    ("apps", "apps", "", "list the apps"),
    ("install", "install", "<app>", "install an app from the Fox Store"),
    ("uninstall", "uninstall", "<app>", "remove an app"),
    ("ps", "ps", "", "running apps"),
    ("kill", "kill", "<PID>", "close an app"),
    ("python / python3", "python", "<file.py> | -c <code>", "run Python code"),
    ("run", "run", "<program>", "run a real program of the computer (e.g. run node -v)"),
    ("calc / bc", "calc", "<expression>", "calculator, e.g. 2*(3+4)"),
    ("curl", "curl", "<url>", "show a web page as text"),
    ("wget", "wget", "<url>", "download a file into Downloads"),
    ("ping", "ping", "<host>", "test the internet connection"),
    ("ip", "ipconfig", "", "network information"),
    ("import", "import", "", "bring files in from this computer"),
    ("export", "export", "<file>", "save a file out to this computer"),
    ("neofetch", "info", "", "system information"),
    ("uname", "uname", "[-a]", "system name"),
    ("whoami", "whoami", "", "your user name"),
    ("hostname", "hostname", "", "computer name"),
    ("date", "date", "", "date and time"),
    ("cal", "cal", "", "calendar"),
    ("history", "history", "", "command history"),
    ("theme", "theme", "dark | light | ocean", "change the theme"),
    ("lang", "lang", "en | el", "change the language"),
    ("fortune", "fortune", "", "a random saying"),
    ("sudo", "sudo", "<command>", "run as administrator"),
    ("clear", "clear", "", "clear the screen"),
    ("exit", "exit", "", "close the terminal"),
    ("lock", "lock", "", "lock the screen"),
    ("reboot", "reboot", "", "restart Blue Fox"),
    ("shutdown / poweroff", "shutdown", "", "shut down Blue Fox"),
]

PROMPT_CMDS = [
    ("help", "help", "", "show this help"),
    ("dir", "dir", "[folder]", "list files"),
    ("cd / chdir", "cd_cmd", "[folder]", "show or change the folder"),
    ("md / mkdir", "mkdir", "<name>", "make a folder"),
    ("type", "cat", "<file>", "show a file  (type nul > file  makes an empty file)"),
    ("more", "cat", "<file>", "show a file"),
    ("echo", "echo", "<text> [> file]", "print text (> or >> writes to a file)"),
    ("del / erase", "del", "[/s] <name>", "delete files"),
    ("rd / rmdir", "rd", "[/s] <folder>", "delete a folder"),
    ("move", "mv", "<from> <to>", "move"),
    ("ren / rename", "mv", "<old> <new>", "rename"),
    ("copy / xcopy", "cp", "<from> <to>", "copy"),
    ("tree", "tree", "[folder]", "show the folder tree"),
    ("where", "find", "<word>", "search file names"),
    ("findstr / find", "grep", "<word> <file>", "search inside a file"),
    ("notepad / edit", "edit", "<file>", "edit a file in Notepad"),
    ("start", "open", "<app or file>", "open an app or a file"),
    ("apps", "apps", "", "list the apps"),
    ("install", "install", "<app>", "install an app from the Fox Store"),
    ("uninstall", "uninstall", "<app>", "remove an app"),
    ("tasklist", "ps", "", "running apps"),
    ("taskkill", "kill", "/PID <n>", "close an app"),
    ("python / py", "python", "<file.py> | -c <code>", "run Python code"),
    ("run", "run", "<program>", "run a real program of the computer (e.g. run node -v)"),
    ("calc", "calc", "<expression>", "calculator, e.g. 2*(3+4)"),
    ("curl", "curl", "<url>", "show a web page as text"),
    ("download", "wget", "<url>", "download a file into Downloads"),
    ("ping", "ping", "<host>", "test the internet connection"),
    ("ipconfig", "ipconfig", "", "network information"),
    ("import", "import", "", "bring files in from this computer"),
    ("export", "export", "<file>", "save a file out to this computer"),
    ("systeminfo", "info", "", "system information"),
    ("ver", "ver", "", "Blue Fox version"),
    ("whoami", "whoami", "", "your user name"),
    ("hostname", "hostname", "", "computer name"),
    ("date", "date", "", "date"),
    ("time", "time", "", "time"),
    ("doskey", "history", "/history", "command history"),
    ("theme", "theme", "dark | light | ocean", "change the theme"),
    ("lang", "lang", "en | el", "change the language"),
    ("cls", "clear", "", "clear the screen"),
    ("exit", "exit", "", "close the terminal"),
    ("lock", "lock", "", "lock the screen"),
    ("shutdown", "shutdown", "[/r]", "shut down (/r = restart)"),
]

FOX_CMDS = [
    ("help / howto", "help", "", "show this help"),
    ("look", "ls", "[folder]", "list files"),
    ("go", "cd", "<folder>", "change folder (.. = up, ~ = home)"),
    ("here", "pwd", "", "show the current folder"),
    ("nest", "mkdir", "<name>", "make a folder"),
    ("new", "touch", "<file>", "make an empty file"),
    ("show", "cat", "<file>", "show a file"),
    ("say", "echo", "<text> [> file]", "print text (> or >> writes to a file)"),
    ("trash", "rm", "<name>", "delete (folders too)"),
    ("move", "mv", "<from> <to>", "move or rename"),
    ("twin", "cp", "<from> <to>", "copy"),
    ("roots", "tree", "[folder]", "show the folder tree"),
    ("sniff", "find", "<word>", "search file names"),
    ("hunt", "grep", "<word> <file>", "search inside a file"),
    ("top", "head", "<file>", "first lines of a file"),
    ("bottom", "tail", "<file>", "last lines of a file"),
    ("count", "wc", "<file>", "count lines, words and characters"),
    ("write", "edit", "<file>", "edit a file in Notepad"),
    ("launch", "open", "<app or file>", "open an app or a file"),
    ("tricks", "apps", "", "list the apps"),
    ("adopt", "install", "<app>", "install an app from the Fox Store"),
    ("release", "uninstall", "<app>", "remove an app"),
    ("pack", "ps", "", "running apps"),
    ("bite", "kill", "<PID>", "close an app"),
    ("py", "python", "<file.py> | -c <code>", "run Python code"),
    ("unleash", "run", "<program>", "run a real program of the computer (e.g. unleash node -v)"),
    ("math", "calc", "<expression>", "calculator, e.g. 2*(3+4)"),
    ("fetch", "curl", "<url>", "show a web page as text"),
    ("grab", "wget", "<url>", "download a file into Downloads"),
    ("sonar", "ping", "<host>", "test the internet connection"),
    ("net", "ipconfig", "", "network information"),
    ("bring", "import", "", "bring files in from this computer"),
    ("send", "export", "<file>", "save a file out to this computer"),
    ("fox", "info", "", "system information"),
    ("me", "whoami", "", "your user name"),
    ("den", "hostname", "", "computer name"),
    ("when", "date", "", "date and time"),
    ("moon", "cal", "", "calendar"),
    ("memory", "history", "", "command history"),
    ("fur", "theme", "dark | light | ocean", "change the theme"),
    ("speak", "lang", "en | el", "change the language"),
    ("wisdom", "fortune", "", "a random saying"),
    ("howl", "foxsay", "<text>", "the fox says something"),
    ("alpha", "sudo", "<command>", "run as administrator"),
    ("wipe", "clear", "", "clear the screen"),
    ("bye", "exit", "", "close the terminal"),
    ("nap", "lock", "", "lock the screen"),
    ("reborn", "reboot", "", "restart Blue Fox"),
    ("sleep", "shutdown", "", "shut down Blue Fox"),
]

DIALECTS = {"prompt": PROMPT_CMDS, "bash": BASH_CMDS, "foxcode": FOX_CMDS}
TERMINAL_NAMES = {"prompt": "Prompt", "bash": "Bash", "foxcode": "Blue Fox Code"}


class Shell:
    def __init__(self, osys, out, dialect="bash"):
        self.os = osys
        self.vfs = osys.vfs
        self.out = out
        self.dialect = dialect
        self.cwd = HOME
        self.history = []
        self.pending = False
        self.on_done = None
        self.table = {}
        for names, method, usage, desc in DIALECTS[dialect]:
            for n in names.split(" / "):
                self.table[n.strip().lower()] = method

    # ---------- helpers ----------
    def p(self, path):
        return self.vfs.norm(path, self.cwd)

    @staticmethod
    def dos(path):
        return "C:" + (path.replace("/", "\\") if path != "/" else "\\")

    def prompt_parts(self):
        """Returns list of (text, tag) for the prompt."""
        s = self.os.settings
        if self.dialect == "prompt":
            return [(self.dos(self.cwd) + ">", None)]
        short = "~" + self.cwd[len(HOME):] if self.cwd.startswith(HOME) else self.cwd
        if self.dialect == "foxcode":
            return [("fox", "user"), (" ▸ ", "muted"), (short, "path"), (" » ", "accent")]
        return [(f"{s['username']}@{s['hostname']}", "user"), (":", None), (short, "path"), ("$ ", None)]

    def resolve(self, word):
        return self.table.get(word.lower())

    def need_net(self):
        if not self.os.settings.get("internet", True):
            raise ValueError(_("the internet is turned off in Settings"))

    def async_job(self, fn, done):
        self.pending = True

        def finish(ok, res):
            try:
                done(ok, res)
            except Exception as e:  # noqa
                self.out(f"{err_text(e)}\n", "err")
            self.pending = False
            if self.on_done:
                self.on_done()
        self.os.run_async(fn, finish)

    # ---------- running a line ----------
    def run(self, line):
        line = line.strip()
        if not line:
            return
        self.history.append(line)
        for part in line.split("&&"):
            if not self.run_one(part.strip()) or self.pending:
                break
        self.os.save()
        self.os.fs_changed()

    def run_one(self, line):
        try:
            tokens = shlex.split(line, posix=True) if self.dialect != "prompt" else \
                shlex.split(line.replace("\\", "/"), posix=True)
        except ValueError as e:
            self.out(_("syntax error: {e}", e=e) + "\n", "err")
            return False
        if not tokens:
            return True
        redirect, append = None, False
        for op in (">>", ">"):
            if op in tokens:
                i = tokens.index(op)
                if i + 1 >= len(tokens):
                    self.out(_("error: missing file name after >") + "\n", "err")
                    return False
                redirect, append = tokens[i + 1], op == ">>"
                tokens = tokens[:i]
                break
        word, args = tokens[0], tokens[1:]
        method = self.resolve(word)
        if not method:
            self.out(_("{cmd}: command not found. Type 'help'.", cmd=word) + "\n", "err")
            return False
        if method in ("clear", "exit"):
            return True    # handled by the terminal window
        fn = getattr(self, "c_" + method)
        buf = []
        real_out = self.out
        if redirect:
            self.out = lambda s, tag=None: buf.append(s) if tag != "err" else real_out(s, tag)
        ok = True
        try:
            fn(args)
        except Exception as e:  # noqa
            real_out(f"{word}: {err_text(e)}\n", "err")
            ok = False
        finally:
            self.out = real_out
        if redirect and ok and not self.pending:
            try:
                self.vfs.write(self.p(redirect), "".join(buf), append=append)
            except Exception as e:  # noqa
                self.out(f"{word}: {err_text(e)}\n", "err")
                ok = False
        return ok

    # ---------- commands ----------
    def c_help(self, a):
        self.out(_("{name} - commands", name=TERMINAL_NAMES[self.dialect]) + "\n", "head")
        for names, method, usage, desc in DIALECTS[self.dialect]:
            left = f"  {names} {usage}".rstrip()
            self.out(f"{left:<44}", "cmd")
            self.out(" " + _(desc) + "\n")
        self.out(_("Tips: Up/Down = history, Tab = complete, cmd1 && cmd2 runs both") + "\n", "muted")

    def c_ls(self, a):
        show_all = any(x in ("-a", "-la", "-al") for x in a)
        long = any(x in ("-l", "-la", "-al") for x in a)
        targets = [x for x in a if not x.startswith("-")] or ["."]
        path = self.p(targets[0])
        if self.vfs.is_file(path):
            self.out(targets[0] + "\n")
            return
        names = self.vfs.listdir(path)
        node = self.vfs.get(path)
        if show_all:
            names = [".", ".."] + names
        for n in names:
            child = node["children"].get(n)
            is_d = n in (".", "..") or child["type"] == "dir"
            if long:
                size = 0 if is_d else VFS.size(child)
                self.out(f"{'drwxr-xr-x' if is_d else '-rw-r--r--'} user user {size:>8} ")
            self.out(n + ("/" if is_d and n not in (".", "..") else ""), "dir" if is_d else None)
            self.out("\n" if long else "  ")
        if names and not long:
            self.out("\n")

    def c_dir(self, a):
        targets = [x for x in a if not x.startswith("/")] or ["."]
        path = self.p(targets[0])
        if not self.vfs.is_dir(path):
            raise FileNotFoundError(targets[0])
        node = self.vfs.get(path)
        self.out(" " + _("Directory of {p}", p=self.dos(path)) + "\n\n")
        stamp = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M")
        files = dirs = total = 0
        for n in self.vfs.listdir(path):
            ch = node["children"][n]
            if ch["type"] == "dir":
                dirs += 1
                self.out(f"{stamp}    <DIR>          ")
                self.out(n + "\n", "dir")
            else:
                files += 1
                sz = VFS.size(ch)
                total += sz
                self.out(f"{stamp}    {sz:>14,} {n}\n")
        self.out(f"{files:>16} " + _("File(s)") + f" {total:>14,} bytes\n")
        self.out(f"{dirs:>16} " + _("Dir(s)") + "\n")

    def c_cd(self, a):
        path = self.p(a[0]) if a else HOME
        if not self.vfs.get(path):
            raise FileNotFoundError(a[0])
        if not self.vfs.is_dir(path):
            raise NotADirectoryError(a[0])
        self.cwd = path

    def c_cd_cmd(self, a):
        a = [x for x in a if x.lower() != "/d"]
        if not a:
            self.out(self.dos(self.cwd) + "\n")
            return
        self.c_cd([" ".join(a)])

    def c_pwd(self, a):
        self.out(self.cwd + "\n")

    def c_mkdir(self, a):
        parents = "-p" in a or self.dialect != "bash"
        names = [x for x in a if x != "-p"]
        if not names:
            raise ValueError(_("usage: {u}", u="mkdir <name>"))
        for n in names:
            self.vfs.mkdir(self.p(n), parents=parents)

    def c_touch(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="touch <file>"))
        for n in a:
            self.vfs.touch(self.p(n))

    def c_cat(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="cat <file>"))
        for n in a:
            if n.lower() == "nul":
                continue
            txt = self.vfs.read(self.p(n))
            self.out(txt if txt.endswith("\n") or not txt else txt + "\n")

    def c_echo(self, a):
        if not a and self.dialect == "prompt":
            self.out("ECHO is on.\n")
            return
        self.out(" ".join(a) + "\n")

    def c_rm(self, a):
        rec = any(x in ("-r", "-rf", "-fr") for x in a) or self.dialect == "foxcode"
        names = [x for x in a if not x.startswith("-")]
        if not names:
            raise ValueError(_("usage: {u}", u="rm [-r] <name>"))
        for n in names:
            path = self.p(n)
            if path in ("/", HOME):
                raise PermissionError(_("you cannot delete that"))
            if self.vfs.is_dir(path) and not rec:
                raise IsADirectoryError(n + " (rm -r)")
            self.vfs.remove(path, recursive=True)

    def c_del(self, a):
        rec = any(x.lower() == "/s" for x in a)
        names = [x for x in a if not x.startswith("/") or self.vfs.get(self.p(x))]
        names = [x for x in names if x.lower() not in ("/s", "/q", "/f")]
        if not names:
            raise ValueError(_("usage: {u}", u="del [/s] <name>"))
        for n in names:
            path = self.p(n)
            if self.vfs.is_dir(path):
                if not rec:
                    raise IsADirectoryError(n + " (del /s, rd /s)")
                if path in ("/", HOME):
                    raise PermissionError(_("you cannot delete that"))
            self.vfs.remove(path, recursive=True)

    def c_rd(self, a):
        rec = any(x.lower() == "/s" for x in a)
        for n in [x for x in a if x.lower() not in ("/s", "/q")]:
            path = self.p(n)
            if not self.vfs.is_dir(path):
                raise NotADirectoryError(n)
            if path in ("/", HOME):
                raise PermissionError(_("you cannot delete that"))
            self.vfs.remove(path, recursive=rec)

    def c_rmdir(self, a):
        for n in a:
            if not self.vfs.is_dir(self.p(n)):
                raise NotADirectoryError(n)
            self.vfs.remove(self.p(n))

    def c_mv(self, a):
        a = [x for x in a if x.lower() != "/y"]
        if len(a) != 2:
            raise ValueError(_("usage: {u}", u="move <from> <to>"))
        self.vfs.move(self.p(a[0]), self.p(a[1]))

    def c_cp(self, a):
        a = [x for x in a if x not in ("-r", "/s", "/e", "/y")]
        if len(a) != 2:
            raise ValueError(_("usage: {u}", u="copy <from> <to>"))
        self.vfs.move(self.p(a[0]), self.p(a[1]), keep=True)

    def c_tree(self, a):
        start = self.p(a[0]) if a else self.cwd
        node = self.vfs.get(start)
        if not node or node["type"] != "dir":
            raise NotADirectoryError(start)
        self.out((self.dos(start) if self.dialect == "prompt" else start) + "\n", "dir")
        counts = [0, 0]

        def rec(n, prefix):
            items = sorted(n["children"].items(), key=lambda kv: (kv[1]["type"] != "dir", kv[0].lower()))
            for i, (k, v) in enumerate(items):
                last = i == len(items) - 1
                self.out(prefix + ("└── " if last else "├── "))
                if v["type"] == "dir":
                    counts[0] += 1
                    self.out(k + "\n", "dir")
                    rec(v, prefix + ("    " if last else "│   "))
                else:
                    counts[1] += 1
                    self.out(k + "\n")
        rec(node, "")
        self.out("\n" + _("{d} folders, {f} files", d=counts[0], f=counts[1]) + "\n", "muted")

    def c_find(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="find <word>"))
        res = self.vfs.walk_find(self.cwd, a[-1])
        for r in res:
            self.out((self.dos(r) if self.dialect == "prompt" else r) + "\n")
        if not res:
            self.out(_("Nothing found.") + "\n", "muted")

    def c_grep(self, a):
        a = [x for x in a if not (x.startswith("/") and len(x) == 2)]
        if len(a) < 2:
            raise ValueError(_("usage: {u}", u="grep <word> <file>"))
        for f in a[1:]:
            for i, line in enumerate(self.vfs.read(self.p(f)).splitlines(), 1):
                if a[0].lower() in line.lower():
                    self.out(f"{f}:{i}: ", "muted")
                    self.out(line + "\n")

    def _lines(self, a):
        n = 10
        files = [x for x in a if not x.startswith("-")]
        for x in a:
            if x.startswith("-") and x[1:].isdigit():
                n = int(x[1:])
        return n, files

    def c_head(self, a):
        n, files = self._lines(a)
        for f in files:
            self.out("\n".join(self.vfs.read(self.p(f)).splitlines()[:n]) + "\n")

    def c_tail(self, a):
        n, files = self._lines(a)
        for f in files:
            self.out("\n".join(self.vfs.read(self.p(f)).splitlines()[-n:]) + "\n")

    def c_wc(self, a):
        for f in a:
            t = self.vfs.read(self.p(f))
            self.out(f"{len(t.splitlines()):>5} {len(t.split()):>6} {len(t):>7} {f}\n")

    def c_edit(self, a):
        path = self.p(a[0]) if a else None
        if path and not self.vfs.get(path):
            self.vfs.touch(path)
        self.os.launch("notepad", path=path)

    def c_open(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="open <app | file>"))
        key = self.os.find_app(" ".join(a))
        if key:
            if not self.os.app_available(key):
                raise ValueError(_("'{a}' is not installed. Try: install {a}", a=key))
            self.os.launch(key)
            self.out(_("Opened: {a}", a=self.os.app_name(key)) + "\n", "muted")
            return
        path = self.p(a[0])
        if not self.vfs.get(path):
            raise FileNotFoundError(a[0])
        self.os.open_path(path)

    def c_apps(self, a):
        self.out(_("Installed apps:") + "\n", "head")
        for key in self.os.available_apps():
            self.out(f"  {key:<12}", "cmd")
            self.out(self.os.app_name(key) + "\n")
        self.out(_("More in the Fox Store:") + " " + ", ".join(self.os.store_missing()) + "\n", "muted")

    def c_install(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="install <app>"))
        key = self.os.find_app(" ".join(a))
        if not key or key not in STORE_KEYS:
            raise ValueError(_("no app called '{a}' in the Fox Store", a=" ".join(a)))
        self.os.store_install(key)
        self.out(_("Installed: {a}", a=self.os.app_name(key)) + "\n", "ok")

    def c_uninstall(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="uninstall <app>"))
        key = self.os.find_app(" ".join(a))
        if not key or key not in self.os.settings["installed"]:
            raise ValueError(_("'{a}' is not installed", a=" ".join(a)))
        self.os.store_uninstall(key)
        self.out(_("Removed: {a}", a=self.os.app_name(key)) + "\n", "ok")

    def c_ps(self, a):
        self.out(_("  PID  APP") + "\n", "head")
        self.out("    1  bluefox-core\n    2  desktop\n    3  taskbar\n")
        for w in self.os.windows:
            self.out(f"{w.pid:>5}  {w.title}\n")

    def c_kill(self, a):
        nums = [x for x in a if x.isdigit()]
        if not nums:
            raise ValueError(_("usage: {u}", u="kill <PID>"))
        for n in map(int, nums):
            if n <= 3:
                raise PermissionError(_("that is a system process"))
            w = next((w for w in self.os.windows if w.pid == n), None)
            if not w:
                raise ValueError(_("no process {n}", n=n))
            self.os.root.after(10, w.close)
            self.out(_("Closed process {n} ({t})", n=n, t=w.title) + "\n", "muted")

    def c_python(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="python <file.py>  |  python -c \"print(1+1)\""))
        if a[0] == "-c":
            code, name = " ".join(a[1:]), "<command>"
        else:
            code, name = self.vfs.read(self.p(a[0])), a[0]
        run_python(code, self.out, self.os.ask_text, name)

    def c_run(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="run <program> [arguments]"))
        if not have(a[0]):
            raise ValueError(_("'{p}' is not installed on this computer. Get it from the Fox Store (Computer apps).",
                               p=a[0]))
        self.out(_("Running {p} in your real home folder ({h}) ...", p=" ".join(a), h=REAL_HOME) + "\n", "muted")

        def job():
            return subprocess.run(a, capture_output=True, text=True, timeout=300, cwd=REAL_HOME, stdin=subprocess.DEVNULL)

        def done(ok, res):
            if not ok:
                self.out(_("error: {e}", e=res) + "\n", "err")
                return
            if res.stdout:
                self.out(res.stdout if res.stdout.endswith("\n") else res.stdout + "\n")
            if res.stderr:
                self.out(res.stderr if res.stderr.endswith("\n") else res.stderr + "\n", "err")
            self.out(_("(finished with code {c})", c=res.returncode) + "\n", "muted")
        self.async_job(job, done)

    def c_calc(self, a):
        self.out(f"{safe_calc(' '.join(a))}\n")

    def c_curl(self, a):
        urls = [x for x in a if not x.startswith("-")]
        if not urls:
            raise ValueError(_("usage: {u}", u="curl <url>"))
        self.need_net()
        url = fix_url(urls[0])
        self.out(_("Connecting to {u} ...", u=url) + "\n", "muted")

        def done(ok, res):
            if not ok:
                self.out(_("error: {e}", e=res) + "\n", "err")
                return
            data, ctype, final = res
            if "html" in ctype:
                pp = PageParser(final)
                pp.feed(decode_html(data, ctype))
                text = re.sub(r"\n{3,}", "\n\n", "".join(t for t, _k, _h in pp.out)).strip()
                if pp.title:
                    self.out(pp.title.strip() + "\n\n", "head")
            else:
                text = decode_html(data, ctype)
            self.out(text[:6000] + ("\n...\n" if len(text) > 6000 else "\n"))
        self.async_job(lambda: http_get(url), done)

    def c_wget(self, a):
        urls = [x for x in a if not x.startswith("-")]
        if not urls:
            raise ValueError(_("usage: {u}", u="wget <url>"))
        self.need_net()
        url = fix_url(urls[0])
        name = os.path.basename(urllib.parse.urlparse(url).path) or "index.html"
        self.out(_("Downloading {u} ...", u=url) + "\n", "muted")

        def done(ok, res):
            if not ok:
                self.out(_("error: {e}", e=res) + "\n", "err")
                return
            data = res[0]
            target = self.vfs.free_name(HOME + "/Downloads", urllib.parse.unquote(name))
            self.vfs.write_bytes(target, data)
            self.os.save()
            self.os.fs_changed()
            self.out(_("Saved {n} ({s}) to {p}", n=VFS.split(target)[1], s=human_size(len(data)),
                       p=target) + "\n", "ok")
        self.async_job(lambda: http_get(url, limit=25_000_000, timeout=60), done)

    def c_ping(self, a):
        self.need_net()
        host = (a[-1] if a else "duckduckgo.com").replace("https://", "").replace("http://", "").split("/")[0]
        self.out(_("Pinging {h} ...", h=host) + "\n", "muted")

        def job():
            res = []
            for _i in range(4):
                t0 = time.time()
                try:
                    socket.create_connection((host, 443), timeout=4).close()
                    res.append(int((time.time() - t0) * 1000))
                except OSError:
                    res.append(None)
            return res

        def done(ok, res):
            if not ok:
                self.out(_("error: {e}", e=res) + "\n", "err")
                return
            for ms in res:
                if ms is None:
                    self.out(_("Request timed out.") + "\n", "err")
                else:
                    self.out(_("Reply from {h}: time={ms}ms", h=host, ms=ms) + "\n")
            good = [m for m in res if m is not None]
            self.out(_("{g}/4 replies", g=len(good)) + "\n", "ok" if good else "err")
        self.async_job(job, done)

    def c_ipconfig(self, a):
        s = self.os.settings
        self.out(_("Blue Fox network") + "\n", "head")
        self.out(f"   {_('Computer name')} . . . : {s['hostname']}\n")
        self.out(f"   {_('Adapter')} . . . . . . . : Blue Fox Virtual Network\n")
        self.out(f"   IPv4 . . . . . . . . . : 10.0.0.{(sum(map(ord, s['hostname'])) % 200) + 20}\n")
        st = _("on") if s.get("internet", True) else _("off")
        self.out(f"   {_('Internet')} . . . . . . . : {st}\n")

    def c_import(self, a):
        n = self.os.import_files(self.cwd)
        self.out(_("Imported {n} files into {p}", n=n, p=self.cwd) + "\n", "muted")

    def c_export(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="export <file | folder>"))
        path = self.p(a[0])
        if not self.vfs.get(path):
            raise FileNotFoundError(a[0])
        self.os.export_path(path)

    def c_info(self, a):
        s = self.os.settings
        up = int(time.time() - self.os.boot_time)
        logo = ["    /\\       /\\   ", "   /  \\_____/  \\  ", "  (   ◆     ◆   ) ", "   \\     ▾     /  ",
                "    \\___/ \\___/   ", "      BLUE FOX     ", "                   ", "                   "]
        info = [(f"{s['username']}@{s['hostname']}", ""), ("-" * 20, ""),
                ("OS: ", f"Blue Fox {VERSION}"), ("Shell: ", TERMINAL_NAMES[self.dialect]),
                ("Engine: ", f"Python {platform.python_version()}"),
                ("Uptime: ", f"{up // 3600}h {up % 3600 // 60}m {up % 60}s"),
                ("Theme: ", _(THEME_NAMES.get(s["theme"], s["theme"]))),
                ("Language: ", LANGUAGES[s["lang"]]), ("Apps open: ", str(len(self.os.windows)))]
        for i in range(max(len(logo), len(info))):
            self.out(logo[i] if i < len(logo) else " " * 19, "logo")
            if i < len(info):
                self.out("  " + info[i][0], "head")
                self.out(info[i][1])
            self.out("\n")

    def c_uname(self, a):
        self.out(f"BlueFox {self.os.settings['hostname']} {VERSION} Python/{platform.python_version()} "
                 f"{platform.machine()}\n" if "-a" in a else "BlueFox\n")

    def c_ver(self, a):
        self.out(f"\nBlue Fox [{_('Version')} {VERSION}]\n\n")

    def c_whoami(self, a):
        self.out(self.os.settings["username"] + "\n")

    def c_hostname(self, a):
        self.out(self.os.settings["hostname"] + "\n")

    def c_date(self, a):
        fmt = "%d/%m/%Y" if self.dialect == "prompt" else "%A %d %B %Y, %H:%M:%S"
        self.out(datetime.datetime.now().strftime(fmt) + "\n")

    def c_time(self, a):
        self.out(datetime.datetime.now().strftime("%H:%M:%S") + "\n")

    def c_cal(self, a):
        now = datetime.date.today()
        self.out(calendar.month(now.year, now.month))

    def c_history(self, a):
        for i, h in enumerate(self.history, 1):
            self.out(f"{i:>4}  {h}\n")

    def c_theme(self, a):
        if not a or a[0] not in THEMES:
            raise ValueError(_("usage: {u}", u="theme dark | light | ocean"))
        self.os.root.after(10, lambda: self.os.set_theme(a[0]))

    def c_lang(self, a):
        if not a or a[0] not in LANGUAGES:
            raise ValueError(_("usage: {u}", u="lang en | el"))
        self.os.root.after(10, lambda: self.os.set_language(a[0]))

    FORTUNES = ["The code you write today is someone's legacy tomorrow.",
                "If it doesn't work, try turning it off and on again.",
                "There's no place like 127.0.0.1",
                "A fox is quick because it never stops learning.",
                "There are 10 types of people: those who know binary and those who don't.",
                "The best operating system is the one you built yourself."]

    def c_fortune(self, a):
        self.out(_(random.choice(self.FORTUNES)) + "\n")

    def _bubble(self, msg):
        self.out(" " + "_" * (len(msg) + 2) + "\n< " + msg + " >\n " + "-" * (len(msg) + 2) + "\n")

    def c_foxsay(self, a):
        self._bubble(" ".join(a) or "Awooo!")
        self.out("      \\    /\\     /\\\n       \\  /  \\___/  \\\n         (   o   o   )\n"
                 "          \\    v    /\n           \\__/ \\__/\n", "logo")

    def c_sudo(self, a):
        if not a:
            raise ValueError(_("usage: {u}", u="sudo <command>"))
        self.out(_("[admin] Nice try! You are already the boss here.") + "\n", "muted")
        self.run_one(" ".join(shlex.quote(x) for x in a))

    def c_lock(self, a):
        self.os.root.after(100, self.os.lock_screen)

    def c_reboot(self, a):
        self.os.root.after(200, self.os.restart)

    def c_shutdown(self, a):
        if any(x.lower() == "/r" for x in a):
            self.os.root.after(200, self.os.restart)
        else:
            self.os.root.after(200, self.os.shutdown)


# ════════════════════════════════════════════════════════════════════
#  Window (an app window inside the Blue Fox desktop)
# ════════════════════════════════════════════════════════════════════
class Window(tk.Frame):
    _pid = 100
    _cascade = 0

    def __init__(self, osys, title, icon_name="file", w=640, h=420, resizable=True):
        t = osys.theme
        super().__init__(osys.desktop, bg=t["title"], highlightthickness=1,
                         highlightbackground=t["accent"], highlightcolor=t["accent"])
        Window._pid += 1
        self.pid = Window._pid
        self.os = osys
        self.title = title
        self.icon = icon(icon_name)
        self.app_key = osys.launching
        self.maximized = False
        self.minimized = False
        self.on_close = None

        dw = max(osys.desktop.winfo_width(), 800)
        dh = max(osys.desktop.winfo_height(), 500)
        w, h = min(w, dw - 40), min(h, dh - 30)
        off = (Window._cascade % 8) * 28
        Window._cascade += 1
        self.geom = dict(x=max(10, (dw - w) // 2 - 100 + off), y=max(6, (dh - h) // 2 - 80 + off),
                         width=w, height=h)

        self.titlebar = tk.Frame(self, bg=t["title"], height=32)
        self.titlebar.pack(fill="x")
        self.titlebar.pack_propagate(False)
        self.tlabel = tk.Label(self.titlebar, text=f"  {self.icon}  {title}", bg=t["title"], fg=t["fg"],
                               font=UI_FONT, anchor="w")
        self.tlabel.pack(side="left", fill="both", expand=True)
        buttons = [("✕", self.close, "#e81123")]
        if resizable:
            buttons.append(("☐", self.toggle_max, t["hover"]))
        buttons.append(("—", self.minimize, t["hover"]))
        for txt, cmd, hov in buttons:
            b = tk.Label(self.titlebar, text=txt, width=5, bg=t["title"], fg=t["fg"], font=UI_FONT)
            b.pack(side="right", fill="y")
            b.bind("<ButtonRelease-1>", lambda e, c=cmd: c())
            b.bind("<Enter>", lambda e, b=b, h=hov: b.config(bg=h, fg="white" if h == "#e81123" else t["fg"]))
            b.bind("<Leave>", lambda e, b=b: b.config(bg=t["title"], fg=t["fg"]))
        for wdg in (self.titlebar, self.tlabel):
            wdg.bind("<ButtonPress-1>", self._drag_start)
            wdg.bind("<B1-Motion>", self._drag_move)
            if resizable:
                wdg.bind("<Double-Button-1>", lambda e: self.toggle_max())

        self.body = tk.Frame(self, bg=t["bg"])
        self.body.pack(fill="both", expand=True)
        self.grip = None
        if resizable:
            self.grip = tk.Label(self, text="◢", bg=t["bg"], fg=t["muted"], cursor="bottom_right_corner",
                                 font=("Arial", 8))
            self.grip.place(relx=1.0, rely=1.0, anchor="se")
            self.grip.bind("<ButtonPress-1>", self._resize_start)
            self.grip.bind("<B1-Motion>", self._resize_move)
        self.place(**self.geom)
        osys.register(self)

    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        if self.maximized:
            self.toggle_max()
            self._dx, self._dy = self.geom["width"] // 2, 15
        x = e.x_root - self._dx
        y = min(max(0, e.y_root - self._dy), self.os.desktop.winfo_height() - 32)
        self.geom.update(x=x, y=y)
        self.place(x=x, y=y)

    def _resize_start(self, e):
        self._rx, self._ry = e.x_root, e.y_root
        self._rw, self._rh = self.winfo_width(), self.winfo_height()

    def _resize_move(self, e):
        if self.maximized:
            return
        w = max(260, self._rw + e.x_root - self._rx)
        h = max(160, self._rh + e.y_root - self._ry)
        self.geom.update(width=w, height=h)
        self.place(width=w, height=h)

    def toggle_max(self):
        self.place_forget()
        if self.maximized:
            self.place(**self.geom)
        else:
            self.place(x=0, y=0, relwidth=1, relheight=1)
        self.maximized = not self.maximized
        if self.grip:
            self.grip.lift()

    def minimize(self):
        self.minimized = True
        self.place_forget()
        if self.os.active is self:
            self.os.active = None
        self.os.refresh_taskbar()

    def restore(self):
        self.minimized = False
        if self.maximized:
            self.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.place(**self.geom)
        self.os.focus_window(self)

    def close(self):
        if self.on_close and self.on_close() is False:
            return
        self.os.unregister(self)
        self.destroy()

    def set_title(self, title):
        if title == self.title:
            return
        self.title = title
        self.tlabel.config(text=f"  {self.icon}  {title}")
        self.os.refresh_taskbar()


def flat_button(parent, text, cmd, t, bg=None, fg=None, font=UI_FONT, **kw):
    bg = bg or t["panel"]
    fg = fg or t["fg"]
    b = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, cursor="hand2", **kw)
    b.bind("<ButtonRelease-1>", lambda e: cmd())
    b.bind("<Enter>", lambda e: b.config(bg=t["hover"] if bg != t["accent"] else "#3d8be8"))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def toolbar(win, t):
    bar = tk.Frame(win.body, bg=t["panel"])
    bar.pack(fill="x")
    return bar


def entry(parent, t, var=None, **kw):
    return tk.Entry(parent, textvariable=var, bg=t["entry"], fg=t["fg"], insertbackground=t["fg"],
                    relief="flat", font=kw.pop("font", UI_FONT), **kw)


# ════════════════════════════════════════════════════════════════════
#  Terminal window (the same window works for all three terminals)
# ════════════════════════════════════════════════════════════════════
TERM_STYLES = {
    "prompt": dict(bg="#0c0c0c", fg="#cccccc", cursor="#cccccc", user="#cccccc", path="#cccccc",
                   accent="#cccccc", logo="#5ea8ff"),
    "bash": dict(bg="#1a1b26", fg="#c0caf5", cursor="#9ece6a", user="#9ece6a", path="#7aa2f7",
                 accent="#bb9af7", logo="#7aa2f7"),
    "foxcode": dict(bg="#06142e", fg="#d6ecff", cursor="#ff9e3d", user="#ff9e3d", path="#4fc3ff",
                    accent="#ff9e3d", logo="#4fc3ff"),
}


class Terminal:
    def __init__(self, osys, dialect="bash", cwd=None, **kw):
        self.os = osys
        st = TERM_STYLES[dialect]
        self.win = Window(osys, TERMINAL_NAMES[dialect], dialect, 780, 470)
        self.text = tk.Text(self.win.body, bg=st["bg"], fg=st["fg"], insertbackground=st["cursor"], font=MONO,
                            bd=0, padx=10, pady=8, wrap="char", selectbackground="#3a3a5a")
        sb = tk.Scrollbar(self.win.body, command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        bold = MONO + ("bold",)
        for tag, kwargs in {"user": dict(foreground=st["user"], font=bold), "path": dict(foreground=st["path"], font=bold),
                            "accent": dict(foreground=st["accent"], font=bold), "err": dict(foreground="#ff6b6b"),
                            "dir": dict(foreground=st["path"], font=bold), "head": dict(foreground="#f9e2af", font=bold),
                            "cmd": dict(foreground="#a6e3a1"), "muted": dict(foreground="#7f849c"),
                            "logo": dict(foreground=st["logo"], font=bold), "ok": dict(foreground="#9ece6a")}.items():
            self.text.tag_config(tag, **kwargs)
        self.shell = Shell(osys, self.write, dialect)
        self.shell.on_done = self.prompt
        if cwd:
            self.shell.cwd = cwd
        self.hidx = 0
        if dialect == "prompt":
            self.write(f"Blue Fox Prompt [{_('Version')} {VERSION}]\n", None)
            self.write(_("Type 'help' for the list of commands.") + "\n\n", "muted")
        elif dialect == "foxcode":
            self.write("  /\\_/\\   Blue Fox Code " + VERSION + "\n", "logo")
            self.write(" ( ◆.◆ )  " + _("Our own command language. Type 'help' to learn the words.") + "\n", "logo")
            self.write("  > ^ <\n\n", "logo")
        else:
            self.write(f"Blue Fox Bash {VERSION}\n", "head")
            self.write(_("Type 'help' for the list of commands.") + "\n\n", "muted")
        self.prompt()
        t = self.text
        t.bind("<Return>", self.on_enter)
        t.bind("<KP_Enter>", self.on_enter)
        t.bind("<BackSpace>", self.on_back)
        t.bind("<Delete>", self.on_del)
        t.bind("<Up>", lambda e: self.hist(-1))
        t.bind("<Down>", lambda e: self.hist(1))
        t.bind("<Tab>", self.on_tab)
        t.bind("<Home>", lambda e: (t.mark_set("insert", "inp"), "break")[1])
        t.bind("<Control-l>", lambda e: (self.clear(), "break")[1])
        t.bind("<Control-c>", self.on_ctrl_c)
        t.bind("<Key>", self.on_key)
        t.bind("<<Paste>>", self.on_paste)
        self.win.body.after(50, t.focus_set)

    def alive(self):
        try:
            return bool(self.text.winfo_exists())
        except tk.TclError:
            return False

    def write(self, s, tag=None):
        if not self.alive():
            return
        self.text.insert("end", s, tag)
        self.text.see("end")

    def prompt(self):
        if not self.alive():
            return
        for txt, tag in self.shell.prompt_parts():
            self.write(txt, tag)
        self.text.mark_set("inp", "end-1c")
        self.text.mark_gravity("inp", "left")
        self.text.mark_set("insert", "end")
        self.text.see("end")

    def current(self):
        return self.text.get("inp", "end-1c")

    def set_current(self, s):
        self.text.delete("inp", "end")
        self.text.insert("end", s)
        self.text.mark_set("insert", "end")

    def clear(self):
        self.text.delete("1.0", "end")
        self.prompt()

    def on_key(self, e):
        if self.shell.pending:
            return "break"
        if e.keysym in ("Left", "Right", "End", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return None
        if e.state & 0x4 and e.keysym.lower() in ("c", "a", "v"):
            return None
        if self.text.compare("insert", "<", "inp"):
            self.text.mark_set("insert", "end")
        try:
            if self.text.compare("sel.first", "<", "inp"):
                self.text.tag_remove("sel", "1.0", "end")
        except tk.TclError:
            pass
        return None

    def on_paste(self, e):
        if self.text.compare("insert", "<", "inp"):
            self.text.mark_set("insert", "end")

    def on_back(self, e):
        try:
            return None if self.text.compare("sel.first", ">=", "inp") else "break"
        except tk.TclError:
            pass
        return "break" if self.text.compare("insert", "<=", "inp") else None

    def on_del(self, e):
        return "break" if self.text.compare("insert", "<", "inp") else None

    def on_ctrl_c(self, e):
        try:
            self.text.index("sel.first")
            return None
        except tk.TclError:
            self.write("^C\n")
            if not self.shell.pending:
                self.prompt()
            return "break"

    def hist(self, d):
        h = self.shell.history
        if h and not self.shell.pending:
            self.hidx = max(0, min(len(h), self.hidx + d))
            self.set_current(h[self.hidx] if self.hidx < len(h) else "")
        return "break"

    def on_tab(self, e):
        if self.shell.pending:
            return "break"
        line = self.current()
        parts = line.split(" ")
        word = parts[-1]
        vfs = self.os.vfs
        if len(parts) == 1:
            opts = sorted(c for c in self.shell.table if c.startswith(word.lower()))
        else:
            w2 = word.replace("\\", "/")
            base, sep, frag = w2.rpartition("/")
            if sep:
                d, prefix = (self.shell.p(base) if base else "/"), base + "/"
            else:
                d, prefix = self.shell.cwd, ""
            try:
                names = vfs.listdir(d)
            except Exception:  # noqa
                names = []
            opts = [prefix + n + ("/" if vfs.is_dir(vfs.norm(n, d)) else "")
                    for n in names if n.lower().startswith(frag.lower())]
            if self.shell.dialect == "prompt":
                opts = [o.replace("/", "\\") for o in opts]
            opts = [f'"{o}"' if " " in o else o for o in opts]
        if len(opts) == 1:
            parts[-1] = opts[0]
            self.set_current(" ".join(parts))
        elif len(opts) > 1:
            self.write("\n" + "  ".join(opts) + "\n", "muted")
            self.prompt()
            self.set_current(line)
        return "break"

    def on_enter(self, e):
        if self.shell.pending:
            return "break"
        line = self.current()
        self.write("\n")
        first = line.strip().split(" ")[0] if line.strip() else ""
        method = self.shell.resolve(first) if first else None
        if method == "clear":
            self.shell.history.append(line.strip())
            self.hidx = len(self.shell.history)
            self.clear()
            return "break"
        if method == "exit":
            self.win.close()
            return "break"
        self.shell.run(line)
        self.hidx = len(self.shell.history)
        if self.alive() and not self.shell.pending:
            self.prompt()
        return "break"


# ════════════════════════════════════════════════════════════════════
#  Files
# ════════════════════════════════════════════════════════════════════
class FileExplorer:
    def __init__(self, osys, path=HOME, **kw):
        self.os = osys
        t = osys.theme
        self.cwd = path if osys.vfs.is_dir(path) else HOME
        self.back_stack = []
        self.names = []
        self.win = Window(osys, _("Files"), "files", 960, 520)
        self.win.on_close = lambda: osys.fs_listeners.discard(self.refresh) or True

        bar = toolbar(self.win, t)
        for txt, cmd in [("←", self.back), ("↑", self.up), ("⟳", self.refresh)]:
            flat_button(bar, txt, cmd, t, width=3, font=("Segoe UI", 12)).pack(side="left", padx=1, pady=3)
        self.path_var = tk.StringVar()
        ent = entry(bar, t, self.path_var)
        ent.pack(side="left", fill="x", expand=True, padx=6, pady=5, ipady=3)
        ent.bind("<Return>", lambda e: self.go(osys.vfs.norm(self.path_var.get(), self.cwd)))

        bar2 = toolbar(self.win, t)
        for txt, cmd in [(_("+ Folder"), self.new_folder), (_("+ File"), self.new_file), (_("Rename"), self.rename),
                         (_("Delete"), self.delete), (_("Terminal here"), self.open_term)]:
            flat_button(bar2, txt, cmd, t, padx=8, pady=3).pack(side="left", padx=1, pady=2)
        for txt, cmd in [(_("⇧ Save to computer"), self.export),
                         (_("⇩ Folder from computer"), lambda: osys.import_folder(self.cwd)),
                         (_("⇩ Files from computer"), lambda: osys.import_files(self.cwd))]:
            flat_button(bar2, txt, cmd, t, bg=t["accent"], fg="white", padx=8, pady=3).pack(side="right", padx=1, pady=2)

        main = tk.Frame(self.win.body, bg=t["bg"])
        main.pack(fill="both", expand=True)
        side = tk.Frame(main, bg=t["panel"], width=160)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text=_("Quick access"), bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(
            anchor="w", padx=10, pady=(8, 4))
        for name, p in [(_("Home"), HOME), (_("Desktop"), HOME + "/Desktop"), (_("Documents"), HOME + "/Documents"),
                        (_("Pictures"), HOME + "/Pictures"), (_("Music"), HOME + "/Music"),
                        (_("Downloads"), HOME + "/Downloads"), (_("Code"), HOME + "/Code"), (_("Root /"), "/")]:
            flat_button(side, f"  {icon('folder')}  {name}", lambda p=p: self.go(p), t, anchor="w", pady=4).pack(fill="x")

        self.lb = tk.Listbox(main, bg=t["bg"], fg=t["fg"], selectbackground=t["accent"], selectforeground="white",
                             font=("Segoe UI", 11), bd=0, highlightthickness=0, activestyle="none")
        sb = tk.Scrollbar(main, command=self.lb.yview)
        self.lb.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True, padx=4, pady=4)
        self.lb.bind("<Double-Button-1>", self.open_selected)
        self.lb.bind("<Return>", self.open_selected)
        self.lb.bind("<Delete>", lambda e: self.delete())
        self.lb.bind("<BackSpace>", lambda e: self.up())
        self.status = tk.Label(self.win.body, bg=t["panel"], fg=t["muted"], anchor="w", font=("Segoe UI", 9))
        self.status.pack(fill="x")
        osys.fs_listeners.add(self.refresh)
        self.refresh()

    def go(self, path, remember=True):
        if not self.os.vfs.is_dir(path):
            messagebox.showerror(_("Files"), _("Folder not found:") + f"\n{path}", parent=self.os.root)
            return
        if remember and path != self.cwd:
            self.back_stack.append(self.cwd)
        self.cwd = path
        self.refresh()

    def back(self):
        if self.back_stack:
            self.go(self.back_stack.pop(), remember=False)

    def up(self):
        self.go(VFS.split(self.cwd)[0] if self.cwd != "/" else "/")

    def refresh(self):
        if not self.win.winfo_exists():
            return
        if not self.os.vfs.is_dir(self.cwd):
            self.cwd = HOME
        self.path_var.set(self.cwd)
        self.win.set_title(f"{_('Files')} — {VFS.split(self.cwd)[1] or '/'}")
        self.lb.delete(0, "end")
        self.names = self.os.vfs.listdir(self.cwd)
        node = self.os.vfs.get(self.cwd)
        for n in self.names:
            ch = node["children"][n]
            if ch["type"] == "dir":
                self.lb.insert("end", f"  {icon('folder')}   {n}")
            else:
                ic = "image" if n.lower().endswith((".png", ".gif", ".jpg", ".jpeg")) else "file"
                self.lb.insert("end", f"  {icon(ic)}   {n}    ({human_size(VFS.size(ch))})")
        self.status.config(text="  " + _("{n} items", n=len(self.names)))

    def selected(self):
        s = self.lb.curselection()
        return self.os.vfs.norm(self.names[s[0]], self.cwd) if s else None

    def open_selected(self, e=None):
        p = self.selected()
        if p:
            self.go(p) if self.os.vfs.is_dir(p) else self.os.open_path(p)

    def _do(self, fn):
        try:
            fn()
        except Exception as ex:  # noqa
            messagebox.showerror(_("Error"), err_text(ex), parent=self.os.root)
        self.os.save()
        self.os.fs_changed()

    def new_folder(self):
        n = self.os.ask_text(_("Folder name:"), _("New folder"))
        if n:
            self._do(lambda: self.os.vfs.mkdir(self.os.vfs.norm(n, self.cwd)))

    def new_file(self):
        n = self.os.ask_text(_("File name:"), "new.txt")
        if n:
            self._do(lambda: self.os.vfs.write(self.os.vfs.norm(n, self.cwd), ""))

    def rename(self):
        p = self.selected()
        if p:
            n = self.os.ask_text(_("New name:"), VFS.split(p)[1])
            if n:
                self._do(lambda: self.os.vfs.move(p, self.os.vfs.norm(n, self.cwd)))

    def delete(self):
        p = self.selected()
        if p and messagebox.askyesno(_("Delete"), _("Delete {p}?", p=p), parent=self.os.root):
            self._do(lambda: self.os.vfs.remove(p, recursive=True))

    def export(self):
        p = self.selected()
        if not p:
            messagebox.showinfo(_("Save to computer"), _("First select a file or folder in the list."),
                                parent=self.os.root)
            return
        self.os.export_path(p)

    def open_term(self):
        key = self.os.default_terminal()
        if not key:
            messagebox.showinfo(_("Terminal"), _("No terminal is installed. Get one from the Fox Store."),
                                parent=self.os.root)
            return
        self.os.launch(key, cwd=self.cwd)


# ════════════════════════════════════════════════════════════════════
#  Notepad
# ════════════════════════════════════════════════════════════════════
class Notepad:
    def __init__(self, osys, path=None, **kw):
        self.os = osys
        t = osys.theme
        self.path = None
        self.win = Window(osys, _("Notepad"), "notepad", 680, 470)
        self.win.on_close = self.confirm_close
        bar = toolbar(self.win, t)
        for txt, cmd in [(_("New"), self.new), (_("Open"), self.open), (_("Save"), self.save),
                         (_("Save as"), self.save_as)]:
            flat_button(bar, txt, cmd, t, padx=10, pady=4).pack(side="left", padx=1, pady=2)
        self.wrap = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text=_("Word wrap"), variable=self.wrap, command=self.toggle_wrap, bg=t["panel"],
                       fg=t["fg"], selectcolor=t["entry"], activebackground=t["panel"], activeforeground=t["fg"],
                       font=UI_FONT).pack(side="right", padx=6)
        self.text = tk.Text(self.win.body, bg=t["entry"], fg=t["fg"], insertbackground=t["fg"], font=MONO, bd=0,
                            padx=10, pady=8, undo=True, wrap="word")
        sb = tk.Scrollbar(self.win.body, command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        self.status = tk.Label(self.win.body, bg=t["panel"], fg=t["muted"], anchor="w", font=("Segoe UI", 9))
        self.status.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        self.text.bind("<Control-s>", lambda e: (self.save(), "break")[1])
        self.text.bind("<KeyRelease>", lambda e: self.update_status())
        if path:
            self.load(path)
        self.update_status()
        self.win.body.after(50, self.text.focus_set)

    def update_status(self):
        line, col = self.text.index("insert").split(".")
        mod = " •" if self.text.edit_modified() else ""
        name = VFS.split(self.path)[1] if self.path else _("Untitled")
        self.status.config(text=f"  {self.path or _('Untitled')}{mod}    " +
                           _("Line {l}, Column {c}", l=line, c=int(col) + 1))
        self.win.set_title(f"{name}{mod} — {_('Notepad')}")

    def toggle_wrap(self):
        self.text.config(wrap="word" if self.wrap.get() else "none")

    def load(self, path):
        try:
            content = self.os.vfs.read(path)
        except Exception as ex:  # noqa
            messagebox.showerror(_("Notepad"), err_text(ex), parent=self.os.root)
            return
        self.path = path
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content.replace("\r\n", "\n"))
        self.text.edit_modified(False)
        self.text.edit_reset()
        self.update_status()

    def new(self):
        if self.confirm_close() is False:
            return
        self.path = None
        self.text.delete("1.0", "end")
        self.text.edit_modified(False)
        self.update_status()

    def open(self):
        p = self.os.ask_text(_("File path:"), self.path or HOME + "/Documents/")
        if p:
            self.load(self.os.vfs.norm(p))

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            self.os.vfs.write(self.path, self.text.get("1.0", "end-1c"))
        except Exception as ex:  # noqa
            messagebox.showerror(_("Notepad"), err_text(ex), parent=self.os.root)
            return False
        self.text.edit_modified(False)
        self.os.save()
        self.os.fs_changed()
        self.update_status()
        return True

    def save_as(self):
        p = self.os.ask_text(_("Save as (file path):"), self.path or HOME + "/Documents/new.txt")
        if not p:
            return False
        self.path = self.os.vfs.norm(p)
        return self.save()

    def confirm_close(self):
        if self.text.edit_modified():
            r = messagebox.askyesnocancel(_("Notepad"), _("Save your changes?"), parent=self.os.root)
            if r is None:
                return False
            if r:
                return self.save() is not False
        return True


# ════════════════════════════════════════════════════════════════════
#  Calculator, Paint, Picture viewer, Calendar, Task manager, About
# ════════════════════════════════════════════════════════════════════
class Calculator:
    def __init__(self, osys, **kw):
        t = osys.theme
        self.win = Window(osys, _("Calculator"), "calc", 320, 460, resizable=False)
        self.var = tk.StringVar(value="0")
        self.hist = tk.StringVar(value="")
        tk.Label(self.win.body, textvariable=self.hist, bg=t["bg"], fg=t["muted"], anchor="e",
                 font=("Segoe UI", 11)).pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(self.win.body, textvariable=self.var, bg=t["bg"], fg=t["fg"], anchor="e",
                 font=("Segoe UI", 28, "bold")).pack(fill="x", padx=12, pady=(0, 8))
        grid = tk.Frame(self.win.body, bg=t["bg"])
        grid.pack(fill="both", expand=True, padx=6, pady=6)
        keys = [["C", "⌫", "%", "÷"], ["7", "8", "9", "×"], ["4", "5", "6", "-"], ["1", "2", "3", "+"], ["√", "0", ".", "="]]
        for r, row in enumerate(keys):
            grid.rowconfigure(r, weight=1)
            for c, k in enumerate(row):
                grid.columnconfigure(c, weight=1)
                bg = t["accent"] if k == "=" else (t["panel"] if k in "÷×-+%C⌫√" else t["hover"])
                flat_button(grid, k, lambda k=k: self.press(k), t, bg=bg, fg="white" if k == "=" else t["fg"],
                            font=("Segoe UI", 15)).grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        self.fresh = True

    def press(self, k):
        cur = self.var.get()
        if k == "C":
            self.var.set("0")
            self.hist.set("")
        elif k == "⌫":
            self.var.set(cur[:-1] or "0")
        elif k == "=":
            try:
                res = safe_calc(cur.replace("%", "/100"))
                self.hist.set(cur + " =")
                self.var.set(str(res))
            except Exception:  # noqa
                self.var.set(_("Error"))
            self.fresh = True
            return
        elif k == "√":
            try:
                self.var.set(str(safe_calc(f"sqrt({cur})")))
            except Exception:  # noqa
                self.var.set(_("Error"))
        else:
            if (cur in ("0", _("Error")) or (self.fresh and k.isdigit())) and k not in "÷×-+%":
                cur = ""
            self.var.set(cur + k)
        self.fresh = False


class Paint:
    COLORS = ["#000000", "#ffffff", "#e81123", "#ff8c00", "#fff100", "#16c60c", "#0078d7", "#886ce4",
              "#e3008c", "#8b4513", "#808080"]

    def __init__(self, osys, **kw):
        t = osys.theme
        self.os = osys
        self.win = Window(osys, _("Paint"), "paint", 780, 530)
        self.color = "#000000"
        self.size = tk.IntVar(value=4)
        self.last = None
        bar = toolbar(self.win, t)
        self.swatch = tk.Label(bar, bg=self.color, width=3, relief="solid", bd=1)
        self.swatch.pack(side="left", padx=(8, 6), pady=4)
        for c in self.COLORS:
            lab = tk.Label(bar, bg=c, width=2, relief="ridge", bd=1, cursor="hand2")
            lab.pack(side="left", padx=1, pady=6)
            lab.bind("<Button-1>", lambda e, c=c: self.set_color(c))
        flat_button(bar, _("More…"), self.pick, t, padx=6).pack(side="left", padx=4)
        flat_button(bar, _("Eraser"), lambda: self.set_color("#ffffff"), t, padx=6).pack(side="left", padx=2)
        flat_button(bar, _("Clear"), lambda: self.cv.delete("all"), t, padx=6).pack(side="left", padx=2)
        tk.Scale(bar, from_=1, to=40, orient="horizontal", variable=self.size, bg=t["panel"], fg=t["fg"],
                 highlightthickness=0, troughcolor=t["entry"], length=110).pack(side="right", padx=6)
        tk.Label(bar, text=_("Size:"), bg=t["panel"], fg=t["fg"], font=UI_FONT).pack(side="right")
        self.cv = tk.Canvas(self.win.body, bg="white", highlightthickness=0, cursor="pencil")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<ButtonPress-1>", self.start)
        self.cv.bind("<B1-Motion>", self.draw)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "last", None))

    def set_color(self, c):
        self.color = c
        self.swatch.config(bg=c)

    def pick(self):
        c = colorchooser.askcolor(self.color, parent=self.os.root)[1]
        if c:
            self.set_color(c)

    def start(self, e):
        self.last = (e.x, e.y)
        r = self.size.get() / 2
        self.cv.create_oval(e.x - r, e.y - r, e.x + r, e.y + r, fill=self.color, outline=self.color)

    def draw(self, e):
        if self.last:
            self.cv.create_line(*self.last, e.x, e.y, fill=self.color, width=self.size.get(), capstyle="round")
        self.last = (e.x, e.y)


def load_photo(node, max_w=None, max_h=None):
    """PhotoImage from a binary VFS file (PNG / GIF), shrunk to fit if needed."""
    img = tk.PhotoImage(data=node["b64"])
    if max_w and max_h:
        f = max(1, math.ceil(max(img.width() / max_w, img.height() / max_h)))
        if f > 1:
            img = img.subsample(f)
    return img


class ImageViewer:
    def __init__(self, osys, path, **kw):
        t = osys.theme
        name = VFS.split(path)[1]
        try:
            self.img = load_photo(osys.vfs.get(path), 900, 580)
        except tk.TclError:
            if messagebox.askyesno(_("Pictures"), _("'{n}' cannot be shown inside Blue Fox (PNG and GIF work).\n\n"
                                                    "Save it to your computer instead?", n=name), parent=osys.root):
                osys.export_path(path)
            return
        w, h = self.img.width(), self.img.height()
        self.win = Window(osys, f"{name} — {_('Pictures')}", "image", max(w + 20, 340), max(h + 80, 200))
        tk.Label(self.win.body, image=self.img, bg=t["bg"]).pack(fill="both", expand=True)
        bar = tk.Frame(self.win.body, bg=t["panel"])
        bar.pack(fill="x")
        tk.Label(bar, text=f"  {w} × {h}", bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(side="left")
        flat_button(bar, _("Set as wallpaper"), lambda: osys.set_wall_image(path), t, padx=8).pack(side="right", pady=2)


class CalendarApp:
    MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
              "October", "November", "December"]
    DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, osys, **kw):
        t = self.t = osys.theme
        self.win = Window(osys, _("Calendar"), "calendar", 370, 340, resizable=False)
        today = datetime.date.today()
        self.y, self.m = today.year, today.month
        top = tk.Frame(self.win.body, bg=t["bg"])
        top.pack(fill="x", pady=6)
        flat_button(top, " ◀ ", lambda: self.shift(-1), t).pack(side="left", padx=8)
        flat_button(top, " ▶ ", lambda: self.shift(1), t).pack(side="right", padx=8)
        self.title = tk.Label(top, bg=t["bg"], fg=t["fg"], font=("Segoe UI", 13, "bold"))
        self.title.pack()
        self.grid = tk.Frame(self.win.body, bg=t["bg"])
        self.grid.pack(fill="both", expand=True, padx=10, pady=4)
        self.render()

    def shift(self, d):
        self.m += d
        if self.m == 0:
            self.m, self.y = 12, self.y - 1
        elif self.m == 13:
            self.m, self.y = 1, self.y + 1
        self.render()

    def render(self):
        t = self.t
        for w in self.grid.winfo_children():
            w.destroy()
        self.title.config(text=f"{_(self.MONTHS[self.m - 1])} {self.y}")
        for c, d in enumerate(self.DAYS):
            tk.Label(self.grid, text=_(d), bg=t["bg"], fg=t["muted"], font=UI_BOLD, width=4).grid(row=0, column=c)
        today = datetime.date.today()
        for r, week in enumerate(calendar.monthcalendar(self.y, self.m), 1):
            for c, day in enumerate(week):
                if day:
                    is_today = (self.y, self.m, day) == (today.year, today.month, today.day)
                    tk.Label(self.grid, text=str(day), width=4, pady=4, bg=t["accent"] if is_today else t["bg"],
                             fg="white" if is_today else t["fg"], font=UI_FONT).grid(row=r, column=c, pady=1)


class TaskManager:
    def __init__(self, osys, **kw):
        t = self.t = osys.theme
        self.os = osys
        self.win = Window(osys, _("Task Manager"), "taskmgr", 470, 400)
        self.info = tk.Label(self.win.body, bg=t["panel"], fg=t["fg"], anchor="w", font=UI_FONT)
        self.info.pack(fill="x", ipady=6, ipadx=8)
        self.list = tk.Frame(self.win.body, bg=t["bg"])
        self.list.pack(fill="both", expand=True, padx=8, pady=8)
        self.cpu = [random.randint(5, 20) for _i in range(40)]
        self.graph = tk.Canvas(self.win.body, height=60, bg=t["panel"], highlightthickness=0)
        self.graph.pack(fill="x", padx=8, pady=(0, 8))
        self.update()

    def update(self):
        if not self.win.winfo_exists():
            return
        t = self.t
        up = int(time.time() - self.os.boot_time)
        self.info.config(text=_("Processes: {n}     Up time: {m}m {s}s", n=len(self.os.windows) + 3,
                                m=up // 60, s=up % 60))
        for w in self.list.winfo_children():
            w.destroy()
        for w in list(self.os.windows):
            row = tk.Frame(self.list, bg=t["bg"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=str(w.pid), width=6, anchor="w", bg=t["bg"], fg=t["muted"], font=UI_FONT).pack(side="left")
            tk.Label(row, text=f"{w.icon}  {w.title}", anchor="w", bg=t["bg"], fg=t["fg"], font=UI_FONT).pack(
                side="left", fill="x", expand=True)
            if w is not self.win:
                flat_button(row, _("End task"), w.close, t, padx=8).pack(side="right")
        self.cpu = self.cpu[1:] + [max(2, min(95, self.cpu[-1] + random.randint(-8, 8)))]
        g = self.graph
        g.delete("all")
        wdt = max(g.winfo_width(), 200)
        pts = []
        for i, v in enumerate(self.cpu):
            pts += [i * wdt / (len(self.cpu) - 1), 58 - v * 0.55]
        g.create_line(*pts, fill=t["accent"], width=2, smooth=True)
        g.create_text(8, 8, text=f"CPU {self.cpu[-1]}%", anchor="nw", fill=t["fg"], font=("Segoe UI", 9))
        self.win.after(1000, self.update)


class About:
    def __init__(self, osys, **kw):
        t = osys.theme
        win = Window(osys, _("About Blue Fox"), "about", 420, 300, resizable=False)
        tk.Label(win.body, text="Blue Fox", bg=t["bg"], fg=t["accent"], font=("Segoe UI", 34, "bold")).pack(pady=(24, 0))
        tk.Label(win.body, text=f"{_('Version')} {VERSION}", bg=t["bg"], fg=t["fg"], font=UI_FONT).pack()
        tk.Label(win.body, text="\n" + _("A complete operating system that runs in a window.") + "\n" +
                 _("Made entirely in Python.") + f"\n\nPython {platform.python_version()}  •  Tk {tk.TkVersion}",
                 bg=t["bg"], fg=t["muted"], font=("Segoe UI", 9), justify="center").pack()


# ════════════════════════════════════════════════════════════════════
#  GAMES
# ════════════════════════════════════════════════════════════════════
class Snake:
    CELL, N = 20, 20

    def __init__(self, osys, **kw):
        t = osys.theme
        size = self.CELL * self.N
        self.win = Window(osys, _("Snake"), "snake", size + 4, size + 70, resizable=False)
        self.win.on_close = self.stop
        top = tk.Frame(self.win.body, bg=t["panel"])
        top.pack(fill="x")
        self.score_l = tk.Label(top, bg=t["panel"], fg=t["fg"], font=UI_BOLD)
        self.score_l.pack(side="left", padx=10, pady=4)
        flat_button(top, _("New game"), self.reset, t, padx=8).pack(side="right", padx=6, pady=3)
        self.cv = tk.Canvas(self.win.body, width=size, height=size, bg="#0b1a0b", highlightthickness=0)
        self.cv.pack()
        for k, d in (("Up", (0, -1)), ("Down", (0, 1)), ("Left", (-1, 0)), ("Right", (1, 0)),
                     ("w", (0, -1)), ("s", (0, 1)), ("a", (-1, 0)), ("d", (1, 0))):
            self.cv.bind(f"<{k}>", lambda e, d=d: self.turn(d))
        self.cv.bind("<space>", lambda e: self.reset() if self.dead else None)
        self.cv.bind("<Button-1>", lambda e: self.cv.focus_set())
        self.job = None
        self.best = 0
        self.reset()

    def reset(self):
        self.snake = [(5, 10), (4, 10), (3, 10)]
        self.dir = self.next_dir = (1, 0)
        self.dead = False
        self.score = 0
        self.place_food()
        self.cv.focus_set()
        if self.job:
            self.cv.after_cancel(self.job)
        self.tick()

    def stop(self):
        if self.job:
            try:
                self.cv.after_cancel(self.job)
            except tk.TclError:
                pass
        return True

    def place_food(self):
        self.food = random.choice([(x, y) for x in range(self.N) for y in range(self.N) if (x, y) not in self.snake])

    def turn(self, d):
        if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
            self.next_dir = d

    def tick(self):
        if not self.cv.winfo_exists():
            return
        self.dir = self.next_dir
        head = (self.snake[0][0] + self.dir[0], self.snake[0][1] + self.dir[1])
        if not (0 <= head[0] < self.N and 0 <= head[1] < self.N) or head in self.snake:
            self.dead = True
            self.best = max(self.best, self.score)
            self.render()
            return
        self.snake.insert(0, head)
        if head == self.food:
            self.score += 1
            self.place_food()
        else:
            self.snake.pop()
        self.render()
        self.job = self.cv.after(max(60, 140 - self.score * 3), self.tick)

    def render(self):
        c, cv = self.CELL, self.cv
        cv.delete("all")
        fx, fy = self.food
        cv.create_oval(fx * c + 3, fy * c + 3, fx * c + c - 3, fy * c + c - 3, fill="#ff4d4d", outline="")
        for i, (x, y) in enumerate(self.snake):
            cv.create_rectangle(x * c + 1, y * c + 1, x * c + c - 1, y * c + c - 1,
                                fill="#7CFC00" if i == 0 else "#32cd32", outline="")
        self.score_l.config(text=_("Score: {s}    Best: {b}", s=self.score, b=max(self.best, self.score)))
        if self.dead:
            mid = c * self.N / 2
            cv.create_text(mid, mid - 10, text="GAME OVER", fill="white", font=("Segoe UI", 26, "bold"))
            cv.create_text(mid, mid + 25, text=_("Press Space to play again"), fill="#cccccc", font=UI_FONT)


class Minesweeper:
    W, H, MINES = 10, 10, 14
    NUM_COLORS = {1: "#5ea8ff", 2: "#4caf50", 3: "#ff5252", 4: "#b388ff", 5: "#ff9800", 6: "#26c6da",
                  7: "#eeeeee", 8: "#9e9e9e"}

    def __init__(self, osys, **kw):
        t = self.t = osys.theme
        self.win = Window(osys, _("Minesweeper"), "mines", 380, 450, resizable=False)
        top = tk.Frame(self.win.body, bg=t["panel"])
        top.pack(fill="x")
        self.info = tk.Label(top, bg=t["panel"], fg=t["fg"], font=UI_BOLD)
        self.info.pack(side="left", padx=10, pady=4)
        flat_button(top, _("New game"), self.reset, t, padx=8).pack(side="right", padx=6, pady=3)
        tk.Label(self.win.body, text=_("Left click = open, right click = flag"), bg=t["bg"], fg=t["muted"],
                 font=("Segoe UI", 9)).pack()
        self.grid = tk.Frame(self.win.body, bg=t["bg"])
        self.grid.pack(pady=6)
        self.cells = {}
        for y in range(self.H):
            for x in range(self.W):
                lab = tk.Label(self.grid, width=3, height=1, font=("Segoe UI", 11, "bold"), relief="raised", bd=2)
                lab.grid(row=y, column=x, padx=1, pady=1)
                lab.bind("<Button-1>", lambda e, p=(x, y): self.open(p))
                lab.bind("<Button-3>", lambda e, p=(x, y): self.flag(p))
                lab.bind("<Button-2>", lambda e, p=(x, y): self.flag(p))
                self.cells[(x, y)] = lab
        self.reset()

    def reset(self):
        self.mines = set()
        self.opened, self.flags = set(), set()
        self.over = False
        self.first = True
        for lab in self.cells.values():
            lab.config(text="", bg=self.t["hover"], relief="raised", fg=self.t["fg"])
        self.update_info()

    def neighbours(self, p):
        x, y = p
        return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx or dy) and 0 <= x + dx < self.W and 0 <= y + dy < self.H]

    def update_info(self, msg=None):
        self.info.config(text=msg or _("Mines: {m}   Flags: {f}", m=self.MINES, f=len(self.flags)))

    def open(self, p):
        if self.over or p in self.flags or p in self.opened:
            return
        if self.first:
            safe = set(self.neighbours(p)) | {p}
            spots = [c for c in self.cells if c not in safe]
            self.mines = set(random.sample(spots, self.MINES))
            self.first = False
        if p in self.mines:
            self.over = True
            for m in self.mines:
                self.cells[m].config(text="✱", bg="#c62828", fg="white", relief="sunken")
            self.update_info(_("Boom! You lost."))
            return
        stack = [p]
        while stack:
            c = stack.pop()
            if c in self.opened:
                continue
            self.opened.add(c)
            self.flags.discard(c)
            n = sum(1 for q in self.neighbours(c) if q in self.mines)
            self.cells[c].config(text=str(n) if n else "", bg=self.t["panel"], relief="sunken",
                                 fg=self.NUM_COLORS.get(n, self.t["fg"]))
            if n == 0:
                stack += [q for q in self.neighbours(c) if q not in self.opened]
        if len(self.opened) == self.W * self.H - self.MINES:
            self.over = True
            self.update_info(_("You won!"))
        else:
            self.update_info()

    def flag(self, p):
        if self.over or p in self.opened:
            return
        if p in self.flags:
            self.flags.remove(p)
            self.cells[p].config(text="")
        else:
            self.flags.add(p)
            self.cells[p].config(text="⚑", fg="#ff5252")
        self.update_info()


class Game2048:
    COLORS = {0: "#2b2b3b", 2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563", 32: "#f67c5f",
              64: "#f65e3b", 128: "#edcf72", 256: "#edcc61", 512: "#edc850", 1024: "#edc53f", 2048: "#5ea8ff"}

    def __init__(self, osys, **kw):
        t = osys.theme
        self.win = Window(osys, "2048", "2048", 420, 500, resizable=False)
        top = tk.Frame(self.win.body, bg=t["panel"])
        top.pack(fill="x")
        self.info = tk.Label(top, bg=t["panel"], fg=t["fg"], font=UI_BOLD)
        self.info.pack(side="left", padx=10, pady=4)
        flat_button(top, _("New game"), self.reset, t, padx=8).pack(side="right", padx=6, pady=3)
        tk.Label(self.win.body, text=_("Use the arrow keys. Join the numbers to reach 2048!"), bg=t["bg"],
                 fg=t["muted"], font=("Segoe UI", 9)).pack(pady=2)
        self.cv = tk.Canvas(self.win.body, width=400, height=400, bg="#1a1a26", highlightthickness=0)
        self.cv.pack(pady=4)
        for k, d in (("Left", "L"), ("Right", "R"), ("Up", "U"), ("Down", "D"), ("a", "L"), ("d", "R"), ("w", "U"), ("s", "D")):
            self.cv.bind(f"<{k}>", lambda e, d=d: self.move(d))
        self.cv.bind("<Button-1>", lambda e: self.cv.focus_set())
        self.reset()

    def reset(self):
        self.b = [[0] * 4 for _i in range(4)]
        self.score = 0
        self.add()
        self.add()
        self.draw()
        self.cv.focus_set()

    def add(self):
        empty = [(r, c) for r in range(4) for c in range(4) if not self.b[r][c]]
        if empty:
            r, c = random.choice(empty)
            self.b[r][c] = 4 if random.random() < 0.1 else 2

    @staticmethod
    def slide(row):
        nums = [x for x in row if x]
        out, gained, i = [], 0, 0
        while i < len(nums):
            if i + 1 < len(nums) and nums[i] == nums[i + 1]:
                out.append(nums[i] * 2)
                gained += nums[i] * 2
                i += 2
            else:
                out.append(nums[i])
                i += 1
        return out + [0] * (4 - len(out)), gained

    def move(self, d):
        old = [r[:] for r in self.b]
        for i in range(4):
            if d in "LR":
                line = self.b[i][:] if d == "L" else self.b[i][::-1]
            else:
                col = [self.b[r][i] for r in range(4)]
                line = col if d == "U" else col[::-1]
            new, g = self.slide(line)
            self.score += g
            if d in "LR":
                self.b[i] = new if d == "L" else new[::-1]
            else:
                new = new if d == "U" else new[::-1]
                for r in range(4):
                    self.b[r][i] = new[r]
        if self.b != old:
            self.add()
        self.draw()

    def can_move(self):
        for r in range(4):
            for c in range(4):
                if not self.b[r][c] or (c < 3 and self.b[r][c] == self.b[r][c + 1]) or \
                        (r < 3 and self.b[r][c] == self.b[r + 1][c]):
                    return True
        return False

    def draw(self):
        cv = self.cv
        cv.delete("all")
        for r in range(4):
            for c in range(4):
                v = self.b[r][c]
                x, y = 10 + c * 97, 10 + r * 97
                cv.create_rectangle(x, y, x + 88, y + 88, fill=self.COLORS.get(v, "#3c3a32"), outline="")
                if v:
                    cv.create_text(x + 44, y + 44, text=str(v), fill="#776e65" if v <= 4 else "white",
                                   font=("Segoe UI", 26 if v < 1000 else 20, "bold"))
        best = max(max(r) for r in self.b)
        msg = _("Score: {s}", s=self.score)
        if best >= 2048:
            msg += "   " + _("You won!")
        elif not self.can_move():
            msg += "   " + _("Game over!")
        self.info.config(text=msg)


class TicTacToe:
    LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]

    def __init__(self, osys, **kw):
        t = self.t = osys.theme
        self.win = Window(osys, _("Tic-Tac-Toe"), "ttt", 340, 420, resizable=False)
        top = tk.Frame(self.win.body, bg=t["panel"])
        top.pack(fill="x")
        self.info = tk.Label(top, bg=t["panel"], fg=t["fg"], font=UI_BOLD)
        self.info.pack(side="left", padx=10, pady=4)
        flat_button(top, _("New game"), self.reset, t, padx=8).pack(side="right", padx=6, pady=3)
        g = tk.Frame(self.win.body, bg=t["bg"])
        g.pack(pady=14)
        self.btns = []
        for i in range(9):
            b = tk.Label(g, width=4, height=2, font=("Segoe UI", 26, "bold"), bg=t["hover"], cursor="hand2")
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            b.bind("<Button-1>", lambda e, i=i: self.play(i))
            self.btns.append(b)
        self.wins = [0, 0, 0]
        self.reset()

    def reset(self):
        self.b = [""] * 9
        self.over = False
        for b in self.btns:
            b.config(text="", bg=self.t["hover"])
        self.status(_("Your turn (X)"))

    def status(self, msg):
        self.info.config(text=f"{msg}    {_('You')} {self.wins[0]} - {self.wins[1]} {_('CPU')}")

    def winner(self, b):
        for a, c, d in self.LINES:
            if b[a] and b[a] == b[c] == b[d]:
                return b[a], (a, c, d)
        return ("draw", ()) if all(b) else (None, ())

    def finish(self, w, line):
        self.over = True
        for i in line:
            self.btns[i].config(bg="#2e7d32")
        if w == "X":
            self.wins[0] += 1
            self.status(_("You won!"))
        elif w == "O":
            self.wins[1] += 1
            self.status(_("The computer won."))
        else:
            self.status(_("Draw!"))

    def play(self, i):
        if self.over or self.b[i]:
            return
        self.b[i] = "X"
        self.btns[i].config(text="X", fg="#5ea8ff")
        w, line = self.winner(self.b)
        if w:
            return self.finish(w, line)
        j = self.cpu_move()
        self.b[j] = "O"
        self.btns[j].config(text="O", fg="#ff9e3d")
        w, line = self.winner(self.b)
        if w:
            return self.finish(w, line)
        self.status(_("Your turn (X)"))

    def cpu_move(self):
        free = [i for i in range(9) if not self.b[i]]
        for mark in ("O", "X"):          # win, otherwise block
            for i in free:
                test = self.b[:]
                test[i] = mark
                if self.winner(test)[0] == mark:
                    return i
        if 4 in free:
            return 4
        corners = [i for i in (0, 2, 6, 8) if i in free]
        return random.choice(corners or free)


class Pong:
    W, H = 560, 360

    def __init__(self, osys, **kw):
        t = osys.theme
        self.win = Window(osys, _("Pong"), "pong", self.W + 4, self.H + 70, resizable=False)
        self.win.on_close = self.stop
        top = tk.Frame(self.win.body, bg=t["panel"])
        top.pack(fill="x")
        self.info = tk.Label(top, bg=t["panel"], fg=t["fg"], font=UI_BOLD)
        self.info.pack(side="left", padx=10, pady=4)
        tk.Label(top, text=_("Up/Down or W/S"), bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(side="right", padx=10)
        self.cv = tk.Canvas(self.win.body, width=self.W, height=self.H, bg="#05101f", highlightthickness=0)
        self.cv.pack()
        self.keys = set()
        for k in ("Up", "Down", "w", "s"):
            self.cv.bind(f"<KeyPress-{k}>", lambda e, k=k: self.keys.add(k))
            self.cv.bind(f"<KeyRelease-{k}>", lambda e, k=k: self.keys.discard(k))
        self.cv.bind("<Button-1>", lambda e: self.cv.focus_set())
        self.score = [0, 0]
        self.py = self.cy = self.H / 2
        self.job = None
        self.serve()
        self.cv.focus_set()
        self.loop()

    def stop(self):
        if self.job:
            try:
                self.cv.after_cancel(self.job)
            except tk.TclError:
                pass
        return True

    def serve(self):
        self.bx, self.by = self.W / 2, self.H / 2
        ang = random.uniform(-0.6, 0.6)
        sp = 6
        self.vx = sp * math.cos(ang) * random.choice((-1, 1))
        self.vy = sp * math.sin(ang)

    def loop(self):
        if not self.cv.winfo_exists():
            return
        if self.keys & {"Up", "w"}:
            self.py -= 7
        if self.keys & {"Down", "s"}:
            self.py += 7
        self.py = min(max(40, self.py), self.H - 40)
        self.cy += max(-4.5, min(4.5, self.by - self.cy))
        self.cy = min(max(40, self.cy), self.H - 40)
        self.bx += self.vx
        self.by += self.vy
        if self.by < 8 or self.by > self.H - 8:
            self.vy *= -1
        if self.bx < 30 and abs(self.by - self.py) < 44 and self.vx < 0:
            self.vx = -self.vx * 1.05
            self.vy += (self.by - self.py) * 0.08
        if self.bx > self.W - 30 and abs(self.by - self.cy) < 44 and self.vx > 0:
            self.vx = -self.vx * 1.05
            self.vy += (self.by - self.cy) * 0.08
        if self.bx < 0:
            self.score[1] += 1
            self.serve()
        elif self.bx > self.W:
            self.score[0] += 1
            self.serve()
        cv = self.cv
        cv.delete("all")
        for y in range(0, self.H, 24):
            cv.create_line(self.W / 2, y, self.W / 2, y + 12, fill="#1d3a5f", width=3)
        cv.create_rectangle(14, self.py - 40, 24, self.py + 40, fill="#5ea8ff", outline="")
        cv.create_rectangle(self.W - 24, self.cy - 40, self.W - 14, self.cy + 40, fill="#ff9e3d", outline="")
        cv.create_oval(self.bx - 8, self.by - 8, self.bx + 8, self.by + 8, fill="white", outline="")
        self.info.config(text=f"{_('You')} {self.score[0]}  -  {self.score[1]} {_('CPU')}")
        self.job = cv.after(16, self.loop)


# ════════════════════════════════════════════════════════════════════
#  WEB BROWSER (built in) + launchers for the real Firefox / Brave
# ════════════════════════════════════════════════════════════════════
class WebBrowser:
    QUICK = [("Wikipedia", "https://en.wikipedia.org/wiki/Special:Random"),
             ("DuckDuckGo Lite", "https://lite.duckduckgo.com/lite/"),
             ("NPR News (text)", "https://text.npr.org/"),
             ("Python.org", "https://www.python.org/"),
             ("Hacker News", "https://news.ycombinator.com/")]

    def __init__(self, osys, url=None, **kw):
        self.os = osys
        t = self.t = osys.theme
        self.win = Window(osys, _("Web"), "web", 940, 620)
        self.history, self.idx = [], -1
        self.images = []
        bar = toolbar(self.win, t)
        for txt, cmd in [("←", self.back), ("→", self.forward), ("⟳", self.reload), ("⌂", self.home)]:
            flat_button(bar, txt, cmd, t, width=3, font=("Segoe UI", 12)).pack(side="left", padx=1, pady=3)
        self.addr = tk.StringVar()
        ent = entry(bar, t, self.addr, font=("Segoe UI", 11))
        ent.pack(side="left", fill="x", expand=True, padx=6, pady=5, ipady=4)
        ent.bind("<Return>", lambda e: self.navigate(fix_url(self.addr.get())))
        hb = osys.settings.get("browser")
        if hb in HOST_BROWSERS:
            flat_button(bar, _("Open in {b}", b=HOST_BROWSERS[hb][0]), self.open_external, t, bg=t["accent"],
                        fg="white", padx=8).pack(side="right", padx=4, pady=4)
        self.text = tk.Text(self.win.body, bg=t["entry"], fg=t["fg"], font=("Segoe UI", 11), bd=0, padx=24,
                            pady=14, wrap="word", cursor="arrow", spacing1=2, spacing3=2)
        sb = tk.Scrollbar(self.win.body, command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        self.status = tk.Label(self.win.body, bg=t["panel"], fg=t["muted"], anchor="w", font=("Segoe UI", 9))
        self.status.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        self.text.tag_config("h", font=("Segoe UI", 15, "bold"), foreground=t["fg"], spacing1=8)
        self.text.tag_config("title", font=("Segoe UI", 22, "bold"), foreground=t["accent"])
        self.text.tag_config("link", foreground="#5ea8ff", underline=True)
        self.text.tag_config("muted", foreground=t["muted"])
        self.text.tag_bind("link", "<Enter>", lambda e: self.text.config(cursor="hand2"))
        self.text.tag_bind("link", "<Leave>", lambda e: self.text.config(cursor="arrow"))
        self.text.bind("<Key>", lambda e: None if (e.state & 0x4) else "break")
        self.navigate(url or "about:home")

    def page_begin(self, url, title):
        self.text.delete("1.0", "end")
        self.links = 0
        self.addr.set("" if url == "about:home" else url)
        self.win.set_title(f"{title} — {_('Web')}")

    def add_link(self, text, href):
        self.links += 1
        tag = f"l{self.links}"
        self.text.insert("end", text, ("link", tag))
        self.text.tag_bind(tag, "<Button-1>", lambda e, h=href: self.navigate(h))
        self.text.tag_bind(tag, "<Enter>", lambda e, h=href: self.status.config(text="  " + h))

    def home(self):
        self.navigate("about:home")

    def show_home(self):
        self.page_begin("about:home", _("Start page"))
        self.text.insert("end", "Blue Fox Web\n", "title")
        self.text.insert("end", _("Type a web address or words to search in the bar above and press Enter.") + "\n\n", "muted")
        self.text.insert("end", _("Quick links") + "\n", "h")
        for name, url in self.QUICK:
            self.text.insert("end", "  • ")
            self.add_link(name, url)
            self.text.insert("end", "\n")
        self.text.insert("end", "\n" + _("Blue Fox Web shows the text and links of web pages. For videos and "
                                         "full websites use the Firefox or Brave app.") + "\n", "muted")
        self.status.config(text="")

    def navigate(self, url, push=True):
        if not url:
            return
        if push:
            self.history = self.history[:self.idx + 1] + [url]
            self.idx = len(self.history) - 1
        if url == "about:home":
            self.show_home()
            return
        if not self.os.settings.get("internet", True):
            self.page_begin(url, _("Offline"))
            self.text.insert("end", _("You are offline") + "\n", "title")
            self.text.insert("end", _("The internet is turned off in Settings → Internet.") + "\n", "muted")
            return
        self.status.config(text="  " + _("Loading {u} ...", u=url))
        self.os.run_async(lambda: http_get(url), lambda ok, res: self.show(ok, res, url))

    def show(self, ok, res, url):
        if not self.win.winfo_exists():
            return
        if not ok:
            self.page_begin(url, _("Error"))
            self.text.insert("end", _("This page could not be opened") + "\n", "title")
            self.text.insert("end", f"{url}\n\n{res}\n", "muted")
            self.status.config(text="")
            return
        data, ctype, final = res
        self.status.config(text="  " + final)
        if ctype.startswith("image/"):
            self.page_begin(final, VFS.split(urllib.parse.urlparse(final).path)[1] or _("Picture"))
            try:
                img = tk.PhotoImage(data=base64.b64encode(data).decode("ascii"))
                f = max(1, math.ceil(img.width() / 860))
                img = img.subsample(f) if f > 1 else img
                self.images = [img]
                self.text.image_create("end", image=img)
                self.text.insert("end", "\n\n")
            except tk.TclError:
                self.text.insert("end", _("(This picture type cannot be shown here.)") + "\n\n", "muted")
            self.offer_download(data, final)
            return
        if "html" not in ctype and "text" not in ctype and "json" not in ctype and "xml" not in ctype:
            self.page_begin(final, _("Download"))
            self.text.insert("end", _("This is a file, not a web page.") + "\n\n", "h")
            self.offer_download(data, final)
            return
        txt = decode_html(data, ctype)
        if "html" not in ctype:
            self.page_begin(final, final)
            self.text.insert("end", txt[:200000])
            return
        pp = PageParser(final)
        try:
            pp.feed(txt)
        except Exception:  # noqa
            pass
        title = re.sub(r"\s+", " ", pp.title).strip() or final
        self.page_begin(final, title[:60])
        if pp.title:
            self.text.insert("end", title + "\n", "title")
        blank = 0
        for i, (seg, kind, href) in enumerate(pp.out):
            if i > 6000:
                self.text.insert("end", "\n…", "muted")
                break
            if seg == "\n":
                blank += 1
                if blank > 2:
                    continue
            else:
                blank = 0
            if kind == "link" and href and not href.startswith(("javascript:", "mailto:")):
                self.add_link(seg, href)
            else:
                self.text.insert("end", seg, kind)
        self.text.yview_moveto(0)

    def offer_download(self, data, url):
        name = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(url).path)) or "download"

        def save():
            target = self.os.vfs.free_name(HOME + "/Downloads", name)
            self.os.vfs.write_bytes(target, data)
            self.os.save()
            self.os.fs_changed()
            self.os.toast(_("Saved to {p}", p=target))
        self.text.insert("end", f"{name}  ({human_size(len(data))})\n\n")
        b = tk.Button(self.text, text=_("Save to Downloads"), command=save, bg=self.t["accent"], fg="white",
                      relief="flat", padx=10, pady=4, cursor="hand2")
        self.text.window_create("end", window=b)

    def back(self):
        if self.idx > 0:
            self.idx -= 1
            self.navigate(self.history[self.idx], push=False)

    def forward(self):
        if self.idx < len(self.history) - 1:
            self.idx += 1
            self.navigate(self.history[self.idx], push=False)

    def reload(self):
        if self.history:
            self.navigate(self.history[self.idx], push=False)

    def open_external(self):
        url = self.history[self.idx] if self.history and self.history[self.idx] != "about:home" else "https://duckduckgo.com"
        self.os.open_host_browser(self.os.settings.get("browser"), url)


class HostBrowserApp:
    """Opens the real Firefox / Brave of this computer in its own window."""

    def __init__(self, osys, which="firefox", url=None, **kw):
        osys.open_host_browser(which, url or "https://duckduckgo.com")


# ════════════════════════════════════════════════════════════════════
#  PROGRAMMING: Python IDE + Fox Turtle (a little drawing language)
# ════════════════════════════════════════════════════════════════════
PY_KEYWORDS = r"\b(def|class|if|elif|else|for|while|in|return|import|from|as|and|or|not|True|False|None|" \
              r"try|except|finally|with|break|continue|pass|lambda|print|input|range|len|is)\b"


class PythonIDE:
    EXAMPLES = {
        "Hello": 'print("Hello, Blue Fox!")\nname = input("What is your name? ")\nprint("Nice to meet you,", name)\n',
        "Guess the number": 'import random\nsecret = random.randint(1, 20)\nfor turn in range(5):\n'
                            '    guess = int(input("Guess (1-20): "))\n    if guess == secret:\n'
                            '        print("Correct!")\n        break\n    print("Higher" if guess < secret else "Lower")\n'
                            'else:\n    print("The number was", secret)\n',
        "Times table": 'n = int(input("Which number? "))\nfor i in range(1, 11):\n    print(f"{n} x {i} = {n*i}")\n',
    }

    def __init__(self, osys, path=None, **kw):
        self.os = osys
        t = osys.theme
        self.path = None
        self.win = Window(osys, "Python", "python", 820, 560)
        bar = toolbar(self.win, t)
        flat_button(bar, "▶ " + _("Run") + " (F5)", self.run, t, bg="#2e7d32", fg="white", padx=10, pady=4).pack(
            side="left", padx=2, pady=3)
        for txt, cmd in [(_("New"), self.new), (_("Open"), self.open), (_("Save"), self.save)]:
            flat_button(bar, txt, cmd, t, padx=10, pady=4).pack(side="left", padx=1)
        ex = tk.Menubutton(bar, text=_("Examples") + " ▾", bg=t["panel"], fg=t["fg"], relief="flat", font=UI_FONT)
        m = tk.Menu(ex, tearoff=0)
        for name, code in self.EXAMPLES.items():
            m.add_command(label=_(name), command=lambda c=code: self.set_code(c))
        ex.config(menu=m)
        ex.pack(side="left", padx=4)
        pw = tk.PanedWindow(self.win.body, orient="vertical", bg=t["panel"], sashwidth=5, bd=0)
        pw.pack(fill="both", expand=True)
        self.ed = tk.Text(pw, bg="#11131c", fg="#e6e6e6", insertbackground="white", font=MONO, bd=0, padx=10,
                          pady=8, undo=True, tabs=("1c",), wrap="none")
        self.outp = tk.Text(pw, bg="#0b0c10", fg="#cfe8ff", font=MONO, bd=0, padx=10, pady=6, height=8)
        pw.add(self.ed, minsize=120)
        pw.add(self.outp, minsize=60)
        for tag, col in (("kw", "#c792ea"), ("str", "#c3e88d"), ("com", "#697098"), ("num", "#f78c6c")):
            self.ed.tag_config(tag, foreground=col)
        self.outp.tag_config("err", foreground="#ff6b6b")
        self.outp.tag_config("muted", foreground="#697098")
        self.ed.bind("<KeyRelease>", lambda e: self.highlight())
        self.ed.bind("<F5>", lambda e: (self.run(), "break")[1])
        self.ed.bind("<Tab>", lambda e: (self.ed.insert("insert", "    "), "break")[1])
        if path:
            self.load(path)
        else:
            self.set_code(self.EXAMPLES["Hello"])
        self.ed.focus_set()

    def set_code(self, code):
        self.ed.delete("1.0", "end")
        self.ed.insert("1.0", code)
        self.highlight()

    def highlight(self):
        code = self.ed.get("1.0", "end-1c")
        for tag in ("kw", "str", "com", "num"):
            self.ed.tag_remove(tag, "1.0", "end")
        for tag, pat in (("num", r"\b\d+(\.\d+)?\b"), ("kw", PY_KEYWORDS), ("str", r"(\"[^\"\n]*\"|'[^'\n]*')"),
                         ("com", r"#[^\n]*")):
            for m in re.finditer(pat, code):
                self.ed.tag_add(tag, f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    def out(self, s, tag=None):
        if self.outp.winfo_exists():
            self.outp.insert("end", s, tag)
            self.outp.see("end")
            self.outp.update_idletasks()

    def run(self):
        self.outp.delete("1.0", "end")
        self.out(_("Running…") + "\n", "muted")
        ok = run_python(self.ed.get("1.0", "end-1c"), self.out, self.os.ask_text, self.path or "<editor>")
        self.out(("\n" + _("Finished.") if ok else "") + "\n", "muted")

    def new(self):
        self.path = None
        self.set_code("")
        self.win.set_title("Python")

    def load(self, path):
        try:
            self.set_code(self.os.vfs.read(path))
            self.path = path
            self.win.set_title(f"{VFS.split(path)[1]} — Python")
        except Exception as ex:  # noqa
            messagebox.showerror("Python", err_text(ex), parent=self.os.root)

    def open(self):
        p = self.os.ask_text(_("File path:"), self.path or HOME + "/Code/hello.py")
        if p:
            self.load(self.os.vfs.norm(p))

    def save(self):
        if not self.path:
            p = self.os.ask_text(_("Save as (file path):"), HOME + "/Code/program.py")
            if not p:
                return
            self.path = self.os.vfs.norm(p)
        try:
            self.os.vfs.write(self.path, self.ed.get("1.0", "end-1c"))
            self.os.save()
            self.os.fs_changed()
            self.win.set_title(f"{VFS.split(self.path)[1]} — Python")
            self.os.toast(_("Saved"))
        except Exception as ex:  # noqa
            messagebox.showerror("Python", err_text(ex), parent=self.os.root)


class FoxTurtle:
    """Fox Turtle: a tiny drawing language. Example:  repeat 5 [ forward 150 right 144 ]"""
    EXAMPLES = {
        "Star": "color gold\nwidth 3\nrepeat 5 [ forward 200 right 144 ]",
        "Flower": "color deepskyblue\nrepeat 36 [ repeat 4 [ forward 90 right 90 ] right 10 ]",
        "Circles": "color orange\nrepeat 12 [ circle 70 right 30 ]",
        "House": "color white\nwidth 3\nrepeat 4 [ forward 120 right 90 ]\nforward 120 right 30\n"
                 "forward 120 right 120 forward 120",
    }
    HELP = ("forward n / fd n · back n / bk n · right n / rt n · left n / lt n · penup / pu · pendown / pd · "
            "color name · width n · circle r · repeat n [ … ] · home · clear")

    def __init__(self, osys, **kw):
        self.os = osys
        t = osys.theme
        self.win = Window(osys, "Fox Turtle", "turtle", 900, 560)
        self.win.on_close = self.stop
        bar = toolbar(self.win, t)
        flat_button(bar, "▶ " + _("Draw"), self.run, t, bg="#2e7d32", fg="white", padx=10, pady=4).pack(side="left", padx=2, pady=3)
        flat_button(bar, _("Clear"), self.clear, t, padx=10, pady=4).pack(side="left", padx=1)
        ex = tk.Menubutton(bar, text=_("Examples") + " ▾", bg=t["panel"], fg=t["fg"], relief="flat", font=UI_FONT)
        m = tk.Menu(ex, tearoff=0)
        for name, code in self.EXAMPLES.items():
            m.add_command(label=_(name), command=lambda c=code: self.set_code(c))
        ex.config(menu=m)
        ex.pack(side="left", padx=4)
        self.speed = tk.IntVar(value=6)
        tk.Scale(bar, from_=1, to=10, orient="horizontal", variable=self.speed, bg=t["panel"], fg=t["fg"],
                 highlightthickness=0, troughcolor=t["entry"], length=100).pack(side="right", padx=6)
        tk.Label(bar, text=_("Speed:"), bg=t["panel"], fg=t["fg"], font=UI_FONT).pack(side="right")
        tk.Label(self.win.body, text=self.HELP, bg=t["bg"], fg=t["muted"], font=("Segoe UI", 8), wraplength=860,
                 justify="left").pack(fill="x", padx=6)
        main = tk.Frame(self.win.body, bg=t["bg"])
        main.pack(fill="both", expand=True)
        self.ed = tk.Text(main, width=34, bg="#11131c", fg="#e6e6e6", insertbackground="white", font=MONO, bd=0,
                          padx=8, pady=8, undo=True)
        self.ed.pack(side="left", fill="y")
        self.cv = tk.Canvas(main, bg="#0b1530", highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        self.status = tk.Label(self.win.body, bg=t["panel"], fg=t["muted"], anchor="w", font=("Segoe UI", 9))
        self.status.pack(fill="x")
        self.job = None
        self.set_code(self.EXAMPLES["Star"])

    def stop(self):
        if self.job:
            try:
                self.cv.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        return True

    def set_code(self, code):
        self.ed.delete("1.0", "end")
        self.ed.insert("1.0", code)

    def clear(self):
        self.stop()
        self.cv.delete("all")

    def compile(self, code):
        tokens = re.findall(r"\[|\]|[^\s\[\]]+", code.lower())
        cw, ch = max(self.cv.winfo_width(), 400), max(self.cv.winfo_height(), 300)
        st = dict(x=cw / 2, y=ch / 2, a=-90.0, pen=True, color="white", width=2)
        ops = []

        def num(i):
            try:
                return float(tokens[i])
            except (IndexError, ValueError):
                raise ValueError(_("a number is needed after '{w}'", w=tokens[i - 1] if i - 1 < len(tokens) else "?"))

        def block(i):
            if i >= len(tokens) or tokens[i] != "[":
                raise ValueError(_("'[' expected after repeat"))
            depth, j = 0, i
            while j < len(tokens):
                depth += {"[": 1, "]": -1}.get(tokens[j], 0)
                if depth == 0:
                    return i + 1, j
                j += 1
            raise ValueError(_("missing ']'"))

        def move(d):
            nx = st["x"] + d * math.cos(math.radians(st["a"]))
            ny = st["y"] + d * math.sin(math.radians(st["a"]))
            if st["pen"]:
                ops.append((st["x"], st["y"], nx, ny, st["color"], st["width"]))
            st["x"], st["y"] = nx, ny

        def run(i, end):
            while i < end:
                if len(ops) > 30000:
                    raise ValueError(_("too many steps"))
                w = tokens[i]
                if w in ("forward", "fd"):
                    move(num(i + 1))
                    i += 2
                elif w in ("back", "bk"):
                    move(-num(i + 1))
                    i += 2
                elif w in ("right", "rt"):
                    st["a"] += num(i + 1)
                    i += 2
                elif w in ("left", "lt"):
                    st["a"] -= num(i + 1)
                    i += 2
                elif w in ("penup", "pu"):
                    st["pen"] = False
                    i += 1
                elif w in ("pendown", "pd"):
                    st["pen"] = True
                    i += 1
                elif w == "color":
                    st["color"] = tokens[i + 1] if i + 1 < len(tokens) else "white"
                    try:
                        self.cv.winfo_rgb(st["color"])
                    except tk.TclError:
                        raise ValueError(_("unknown color '{c}'", c=st["color"]))
                    i += 2
                elif w == "width":
                    st["width"] = max(1, num(i + 1))
                    i += 2
                elif w == "circle":
                    r = num(i + 1)
                    step = 2 * math.pi * r / 36
                    for _k in range(36):
                        move(step)
                        st["a"] += 10
                    i += 2
                elif w == "repeat":
                    n = int(num(i + 1))
                    s, e = block(i + 2)
                    for _k in range(max(0, n)):
                        run(s, e)
                    i = e + 1
                elif w == "home":
                    st.update(x=cw / 2, y=ch / 2, a=-90.0)
                    i += 1
                elif w == "clear":
                    ops.append("clear")
                    i += 1
                else:
                    raise ValueError(_("unknown word '{w}'", w=w))
        run(0, len(tokens))
        return ops, st

    def run(self):
        self.stop()
        self.cv.delete("all")
        try:
            ops, st = self.compile(self.ed.get("1.0", "end"))
        except ValueError as e:
            self.status.config(text="  ✗ " + str(e), fg="#ff6b6b")
            return
        self.status.config(text="  " + _("Drawing {n} lines…", n=len(ops)), fg=self.os.theme["muted"])
        self.ops, self.final = ops, st
        self.pos = 0
        self.step()

    def step(self):
        if not self.cv.winfo_exists():
            return
        per = int(2 ** (self.speed.get() - 1))
        for op in self.ops[self.pos:self.pos + per]:
            if op == "clear":
                self.cv.delete("all")
            else:
                x1, y1, x2, y2, c, w = op
                self.cv.create_line(x1, y1, x2, y2, fill=c, width=w, capstyle="round")
        self.pos += per
        self.cv.delete("turtle")
        if self.pos < len(self.ops):
            x1, y1, x2, y2 = self.ops[self.pos - 1][:4] if self.ops[self.pos - 1] != "clear" else (0, 0, 0, 0)
            self.draw_turtle(x2, y2, math.degrees(math.atan2(y2 - y1, x2 - x1)))
            self.job = self.cv.after(16, self.step)
        else:
            self.job = None
            self.draw_turtle(self.final["x"], self.final["y"], self.final["a"])
            self.status.config(text="  ✓ " + _("Done!"))

    def draw_turtle(self, x, y, a):
        r = math.radians(a)
        pts = [(x + 14 * math.cos(r), y + 14 * math.sin(r)),
               (x + 8 * math.cos(r + 2.5), y + 8 * math.sin(r + 2.5)),
               (x + 8 * math.cos(r - 2.5), y + 8 * math.sin(r - 2.5))]
        self.cv.create_polygon(pts, fill="#ff9e3d", outline="white", tags="turtle")


# ════════════════════════════════════════════════════════════════════
#  PROGRAMS: every real program installed on the computer (Blue Fox as OS)
# ════════════════════════════════════════════════════════════════════
def read_desktop_files():
    apps = {}
    for d in ("/usr/share/applications", "/usr/local/share/applications",
              os.path.join(REAL_HOME, ".local/share/applications")):
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for f in names:
            if not f.endswith(".desktop"):
                continue
            try:
                txt = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            sect = txt.split("[Desktop Entry]", 1)[-1].split("\n[", 1)[0]
            kv = {}
            for line in sect.splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    kv.setdefault(k.strip(), v.strip())
            if kv.get("Type") != "Application" or kv.get("NoDisplay") == "true" or kv.get("Hidden") == "true":
                continue
            if not kv.get("Exec") or kv.get("Terminal") == "true":
                continue
            name = kv.get(f"Name[{LANG['code']}]") or kv.get("Name") or f[:-8]
            exe = re.sub(r"\s%[a-zA-Z]", "", kv["Exec"]).strip()
            apps[name] = (exe, kv.get(f"Comment[{LANG['code']}]") or kv.get("Comment", ""))
    return apps


class ProgramsApp:
    def __init__(self, osys, **kw):
        self.os = osys
        t = self.t = osys.theme
        self.win = Window(osys, _("Programs"), "programs", 640, 520)
        bar = toolbar(self.win, t)
        tk.Label(bar, text="⌕", bg=t["panel"], fg=t["muted"], font=("Segoe UI", 12)).pack(side="left", padx=(10, 2))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: self.render())
        entry(bar, t, self.q).pack(side="left", fill="x", expand=True, padx=6, pady=6, ipady=3)
        flat_button(bar, _("Get more"), lambda: osys.launch("store", category="Computer apps"), t, bg=t["accent"],
                    fg="white", padx=10, pady=3).pack(side="right", padx=6)
        self.list = ScrollFrame(self.win.body, t["bg"])
        self.list.pack(fill="both", expand=True)
        self.apps = read_desktop_files()
        self.render()

    def render(self):
        t = self.t
        for w in self.list.inner.winfo_children():
            w.destroy()
        q = self.q.get().strip().lower()
        n = 0
        for name, (exe, comment) in sorted(self.apps.items(), key=lambda kv: kv[0].lower()):
            if q and q not in name.lower() and q not in comment.lower():
                continue
            n += 1
            row = tk.Frame(self.list.inner, bg=t["panel"], cursor="hand2")
            row.pack(fill="x", padx=10, pady=2)
            a = tk.Label(row, text=name, bg=t["panel"], fg=t["fg"], font=UI_BOLD, anchor="w")
            a.pack(fill="x", padx=10, pady=(5, 0))
            b = tk.Label(row, text=comment, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9), anchor="w")
            b.pack(fill="x", padx=10, pady=(0, 5))
            for w in (row, a, b):
                w.bind("<Button-1>", lambda e, x=exe: self.os.run_program(shlex.split(x)))
        if not n:
            tk.Label(self.list.inner, text=_("Nothing found."), bg=t["bg"], fg=t["muted"], font=UI_FONT).pack(pady=30)


# ════════════════════════════════════════════════════════════════════
#  FOX STORE
# ════════════════════════════════════════════════════════════════════
STORE = [  # key, category, description, size
    ("prompt", "Terminals", "Classic prompt with commands like dir, cls, type, del.", "1.2 MB"),
    ("bash", "Terminals", "Bash style terminal with commands like ls, clear, cat, rm.", "1.4 MB"),
    ("foxcode", "Terminals", "Blue Fox Code: the same power with our own easy words (look, wipe, show...).", "1.1 MB"),
    ("snake", "Games", "The classic snake game. Eat, grow, don't hit the walls!", "0.4 MB"),
    ("mines", "Games", "Find all the safe squares without hitting a mine.", "0.5 MB"),
    ("2048", "Games", "Slide the tiles and join the numbers to reach 2048.", "0.3 MB"),
    ("ttt", "Games", "Tic-Tac-Toe against the computer.", "0.2 MB"),
    ("pong", "Games", "Table tennis against the computer.", "0.3 MB"),
    ("python", "Programming", "Write and run real Python programs.", "3.0 MB"),
    ("turtle", "Programming", "Fox Turtle: learn to code by drawing pictures.", "0.8 MB"),
    ("firefox", "Browsers", "Opens the real Firefox browser of this computer.", "Link"),
    ("brave", "Browsers", "Opens the real Brave browser of this computer.", "Link"),
    ("paint", "Tools", "Draw pictures with colours and brushes.", "0.6 MB"),
]
STORE_KEYS = {k for k, *_rest in STORE}
# Real programs installed into the Blue Fox computer (free, open source). key, name, category, description,
# package, command
REAL_APPS = [
    ("supertuxkart", "SuperTuxKart", "Games", "3D kart racing game.", "supertuxkart", "supertuxkart"),
    ("supertux", "SuperTux", "Games", "Jump-and-run platform game.", "supertux", "supertux2"),
    ("etr", "Extreme Tux Racer", "Games", "Slide down snowy mountains.", "extremetuxracer", "etr"),
    ("minetest", "Minetest", "Games", "Build and explore a world made of blocks.", "minetest", "minetest"),
    ("frozenbubble", "Frozen Bubble", "Games", "Shoot and pop the coloured bubbles.", "frozen-bubble", "frozen-bubble"),
    ("pingus", "Pingus", "Games", "Guide the penguins to safety.", "pingus", "pingus"),
    ("cards", "Card games", "Games", "Solitaire and many other card games.", "aisleriot", "sol"),
    ("thonny", "Thonny", "Programming", "A friendly Python editor for beginners.", "thonny", "thonny"),
    ("geany", "Geany", "Programming", "Code editor for many languages (C, Java, JavaScript...).", "geany", "geany"),
    ("nodejs", "Node.js", "Programming", "Run JavaScript programs (use: run node file.js).", "nodejs", ""),
    ("gcc", "C / C++", "Programming", "Compile C and C++ programs (use: run gcc).", "build-essential", ""),
    ("java", "Java", "Programming", "Write and run Java programs (use: run java).", "default-jdk", ""),
    ("chromium", "Chromium", "Browsers", "Open source web browser.", "chromium", "chromium"),
    ("vlc", "VLC", "Tools", "Plays videos and music.", "vlc", "vlc"),
    ("gimp", "GIMP", "Tools", "Edit photos and pictures.", "gimp", "gimp"),
    ("writer", "Writer", "Tools", "Write documents.", "libreoffice-writer", "lowriter"),
]
REAL_STORE = SESSION and have("apt-get")
STORE_CATS = ["All", "Terminals", "Games", "Programming", "Browsers", "Tools"] + (["Computer apps"] if SESSION else [])


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0)
        sb = tk.Scrollbar(self, command=self.cv.yview)
        self.inner = tk.Frame(self.cv, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self._win = self.cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfig(self._win, width=e.width))
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        for w in (self.cv, self.inner):
            w.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", self._wheel))
            w.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        try:
            self.cv.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
        except tk.TclError:
            pass


class FoxStore:
    def __init__(self, osys, category="All", **kw):
        self.os = osys
        t = self.t = osys.theme
        self.cat = category
        self.win = Window(osys, "Fox Store", "store", 860, 560)
        self.win.on_close = lambda: osys.store_listeners.discard(self.render) or True
        head = tk.Frame(self.win.body, bg=t["panel"])
        head.pack(fill="x")
        tk.Label(head, text=f"{icon('store')}  Fox Store", bg=t["panel"], fg=t["accent"],
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=8)
        tk.Label(head, text=_("Everything is free. Install as many apps as you like."), bg=t["panel"],
                 fg=t["muted"], font=UI_FONT).pack(side="left")
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: self.render())
        entry(head, t, self.q, width=22).pack(side="right", padx=12, ipady=4)
        tk.Label(head, text="⌕", bg=t["panel"], fg=t["muted"], font=("Segoe UI", 12)).pack(side="right")
        main = tk.Frame(self.win.body, bg=t["bg"])
        main.pack(fill="both", expand=True)
        side = tk.Frame(main, bg=t["panel"], width=150)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.cat_btns = {}
        for c in STORE_CATS:
            b = flat_button(side, "   " + _(c), lambda c=c: self.set_cat(c), t, anchor="w", pady=7)
            b.pack(fill="x")
            self.cat_btns[c] = b
        self.list = ScrollFrame(main, t["bg"])
        self.list.pack(side="left", fill="both", expand=True)
        osys.store_listeners.add(self.render)
        self.render()

    def set_cat(self, c):
        self.cat = c
        self.render()

    def render(self):
        if not self.win.winfo_exists():
            return
        t = self.t
        for c, b in self.cat_btns.items():
            b.config(fg=t["accent"] if c == self.cat else t["fg"], font=UI_BOLD if c == self.cat else UI_FONT)
        for w in self.list.inner.winfo_children():
            w.destroy()
        q = self.q.get().strip().lower()
        shown = 0
        for key, cat, desc, size in STORE:
            name = self.os.app_name(key)
            if self.cat != "All" and cat != self.cat:
                continue
            if q and q not in name.lower() and q not in key:
                continue
            shown += 1
            card = tk.Frame(self.list.inner, bg=t["panel"], highlightthickness=1, highlightbackground=t["hover"])
            card.pack(fill="x", padx=12, pady=5)
            tk.Label(card, text=icon(APPS[key]["icon"]), bg=t["panel"], fg=t["accent"], width=4,
                     font=("Segoe UI", 22)).pack(side="left", padx=6, pady=8)
            info = tk.Frame(card, bg=t["panel"])
            info.pack(side="left", fill="both", expand=True, pady=6)
            tk.Label(info, text=name, bg=t["panel"], fg=t["fg"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=_(desc), bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9), anchor="w",
                     wraplength=430, justify="left").pack(fill="x")
            tk.Label(info, text=f"{_(cat)}  •  {size}  •  {_('Free')}", bg=t["panel"], fg=t["muted"],
                     font=("Segoe UI", 8), anchor="w").pack(fill="x")
            btns = tk.Frame(card, bg=t["panel"])
            btns.pack(side="right", padx=10)
            if key in self.os.settings["installed"]:
                flat_button(btns, _("Open"), lambda k=key: self.os.launch(k), t, bg=t["accent"], fg="white",
                            padx=14, pady=4).pack(side="left", padx=2)
                flat_button(btns, _("Remove"), lambda k=key: self.remove(k), t, bg=t["hover"], padx=10,
                            pady=4).pack(side="left", padx=2)
            else:
                b = flat_button(btns, _("Install"), None, t, bg="#2e7d32", fg="white", padx=14, pady=4)
                b.bind("<ButtonRelease-1>", lambda e, k=key, b=b: self.install(k, b))
                b.pack()
        if REAL_STORE and self.cat in ("All", "Computer apps", "Games", "Programming", "Browsers", "Tools"):
            first = True
            for key, name, cat, desc, pkg, cmd in REAL_APPS:
                if self.cat not in ("All", "Computer apps") and cat != self.cat:
                    continue
                if q and q not in name.lower() and q not in key:
                    continue
                if first:
                    tk.Label(self.list.inner, text=_("Computer apps (real programs, need internet to install)"),
                             bg=t["bg"], fg=t["accent"], font=UI_BOLD).pack(anchor="w", padx=14, pady=(10, 2))
                    first = False
                shown += 1
                self.real_card(key, name, cat, desc, pkg, cmd)
        if not shown:
            tk.Label(self.list.inner, text=_("Nothing found."), bg=t["bg"], fg=t["muted"], font=UI_FONT).pack(pady=30)

    def real_card(self, key, name, cat, desc, pkg, cmd):
        t, o = self.t, self.os
        card = tk.Frame(self.list.inner, bg=t["panel"], highlightthickness=1, highlightbackground=t["hover"])
        card.pack(fill="x", padx=12, pady=5)
        tk.Label(card, text="⬢", bg=t["panel"], fg=APP_COLORS.get(key, t["accent"]), width=4,
                 font=("Segoe UI", 22)).pack(side="left", padx=6, pady=8)
        info = tk.Frame(card, bg=t["panel"])
        info.pack(side="left", fill="both", expand=True, pady=6)
        tk.Label(info, text=name, bg=t["panel"], fg=t["fg"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=_(desc), bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9), anchor="w",
                 wraplength=430, justify="left").pack(fill="x")
        tk.Label(info, text=f"{_(cat)}  •  {_('Computer app')}  •  {_('Free')}", bg=t["panel"], fg=t["muted"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")
        btns = tk.Frame(card, bg=t["panel"])
        btns.pack(side="right", padx=10)
        busy = o.apt_busy.get(pkg)
        if busy:
            tk.Label(btns, text=busy, bg=t["panel"], fg=t["accent"], font=UI_BOLD).pack()
        elif o.pkg_installed(pkg):
            if cmd:
                flat_button(btns, _("Open"), lambda: o.run_program([cmd]), t, bg=t["accent"], fg="white",
                            padx=14, pady=4).pack(side="left", padx=2)
            flat_button(btns, _("Remove"), lambda: o.apt("remove", pkg, name), t, bg=t["hover"], padx=10,
                        pady=4).pack(side="left", padx=2)
        else:
            flat_button(btns, _("Install"), lambda: o.apt("install", pkg, name), t, bg="#2e7d32", fg="white",
                        padx=14, pady=4).pack()

    def install(self, key, btn):
        btn.unbind("<ButtonRelease-1>")
        steps = 12

        def tick(i=0):
            if not btn.winfo_exists():
                return
            if i <= steps:
                btn.config(text=f"{int(i * 100 / steps)}%")
                btn.after(70, tick, i + 1)
            else:
                self.os.store_install(key)
                self.os.toast(_("Installed: {a}", a=self.os.app_name(key)))
        tick()

    def remove(self, key):
        if messagebox.askyesno("Fox Store", _("Remove {a}?", a=self.os.app_name(key)), parent=self.os.root):
            self.os.store_uninstall(key)


# ════════════════════════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════════════════════════
class Settings:
    PAGES = [("personal", "Personalization"), ("account", "Account"), ("language", "Language"),
             ("terminals", "Terminals"), ("browser", "Browser"), ("internet", "Internet"), ("system", "System")]

    def __init__(self, osys, page="personal", **kw):
        self.os = osys
        t = self.t = osys.theme
        self.win = Window(osys, _("Settings"), "settings", 820, 540)
        nav = tk.Frame(self.win.body, bg=t["panel"], width=180)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        tk.Label(nav, text=_("Settings"), bg=t["panel"], fg=t["fg"], font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=14, pady=(14, 8))
        self.nav_btns = {}
        for key, label in self.PAGES:
            b = flat_button(nav, "   " + _(label), lambda k=key: self.show(k), t, anchor="w", pady=7)
            b.pack(fill="x")
            self.nav_btns[key] = b
        self.sf = ScrollFrame(self.win.body, t["bg"])
        self.sf.pack(side="left", fill="both", expand=True)
        self.show(page)

    # ---------- helpers ----------
    def show(self, page):
        self.page = page
        for k, b in self.nav_btns.items():
            b.config(fg=self.t["accent"] if k == page else self.t["fg"], font=UI_BOLD if k == page else UI_FONT)
        for w in self.sf.inner.winfo_children():
            w.destroy()
        self.body = tk.Frame(self.sf.inner, bg=self.t["bg"])
        self.body.pack(fill="both", expand=True, padx=24, pady=14)
        getattr(self, "p_" + page)()
        self.sf.cv.yview_moveto(0)

    def h(self, text):
        tk.Label(self.body, text=text, bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 13, "bold")).pack(
            anchor="w", pady=(12, 4))

    def note(self, text, color=None):
        tk.Label(self.body, text=text, bg=self.t["bg"], fg=color or self.t["muted"], font=("Segoe UI", 9),
                 wraplength=540, justify="left").pack(anchor="w", pady=2)

    def btn(self, parent, text, cmd, primary=False):
        t = self.t
        return flat_button(parent, text, cmd, t, bg=t["accent"] if primary else t["panel"],
                           fg="white" if primary else t["fg"], padx=12, pady=5)

    def form(self, rows):
        f = tk.Frame(self.body, bg=self.t["bg"])
        f.pack(anchor="w", pady=4)
        vars_ = {}
        for r, (key, label, value, secret) in enumerate(rows):
            tk.Label(f, text=label, bg=self.t["bg"], fg=self.t["fg"], font=UI_FONT).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar(value=value)
            entry(f, self.t, v, width=26, show="●" if secret else "").grid(row=r, column=1, sticky="w", padx=10, ipady=3)
            vars_[key] = v
        return vars_

    # ---------- pages ----------
    def p_personal(self):
        t, s, o = self.t, self.os.settings, self.os
        self.h(_("Theme"))
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(anchor="w")
        for key in THEMES:
            sel = s["theme"] == key
            flat_button(row, _(THEME_NAMES[key]), lambda k=key: o.set_theme(k, page="personal"), t,
                        bg=t["accent"] if sel else t["panel"], fg="white" if sel else t["fg"], padx=14,
                        pady=6).pack(side="left", padx=(0, 8))
        self.h(_("Wallpaper colours"))
        grid = tk.Frame(self.body, bg=t["bg"])
        grid.pack(anchor="w")
        for i, (name, (c1, c2)) in enumerate(WALLPAPERS.items()):
            prev = tk.Canvas(grid, width=120, height=56, highlightthickness=0, cursor="hand2")
            prev.grid(row=i // 3, column=i % 3, padx=4, pady=4)
            for k in range(28):
                prev.create_rectangle(0, k * 2, 120, k * 2 + 2, outline="", fill=mix(c1, c2, k / 27))
            prev.create_text(60, 28, text=_(name), fill="white", font=("Segoe UI", 9, "bold"))
            prev.bind("<Button-1>", lambda e, a=c1, b=c2: o.set_wallpaper(a, b))
        self.btn(self.body, _("Choose my own colours…"), self.custom_wall).pack(anchor="w", pady=4)

        self.h(_("Wallpaper picture"))
        cur = s.get("wall_image")
        self.note(_("Current picture: {p}", p=cur) if cur else _("No picture. Use a picture you downloaded or "
                                                                 "brought in from your computer (PNG or GIF)."))
        pics = [p for p in o.vfs.walk_find(HOME, ".") if p.lower().endswith((".png", ".gif"))]
        for p in pics[:30]:
            r = tk.Frame(self.body, bg=t["bg"])
            r.pack(anchor="w", fill="x")
            tk.Label(r, text=f"{icon('image')}  {p}", bg=t["bg"], fg=t["fg"], font=UI_FONT).pack(side="left")
            self.btn(r, _("Use"), lambda p=p: (o.set_wall_image(p), self.show("personal"))).pack(side="right", padx=4, pady=1)
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(anchor="w", pady=6)
        self.btn(row, _("⇩ Bring a picture from my computer…"), self.import_pic, True).pack(side="left", padx=(0, 6))
        if cur:
            self.btn(row, _("Remove picture"), lambda: (o.set_wall_image(""), self.show("personal"))).pack(side="left")

    def custom_wall(self):
        c1 = colorchooser.askcolor(self.os.settings["wall1"], title=_("Top colour"), parent=self.os.root)[1]
        if c1:
            c2 = colorchooser.askcolor(self.os.settings["wall2"], title=_("Bottom colour"), parent=self.os.root)[1]
            if c2:
                self.os.set_wallpaper(c1, c2)

    def import_pic(self):
        before = set(self.os.vfs.listdir(HOME + "/Pictures"))
        self.os.import_files(HOME + "/Pictures")
        new = [n for n in self.os.vfs.listdir(HOME + "/Pictures") if n not in before and
               n.lower().endswith((".png", ".gif"))]
        if new:
            self.os.set_wall_image(HOME + "/Pictures/" + new[0])
        self.show("personal")

    def p_account(self):
        s = self.os.settings
        self.h(_("Your account"))
        v = self.form([("username", _("User name"), s["username"], False),
                       ("hostname", _("Computer name"), s["hostname"], False)])

        def save():
            for k in ("username", "hostname"):
                val = v[k].get().strip().replace(" ", "_")
                if val:
                    s[k] = val
            self.os.save()
            self.os.toast(_("Saved"))
        self.btn(self.body, _("Save"), save, True).pack(anchor="w", pady=6)

        self.h(_("Change password"))
        self.note(_("You need this password every time Blue Fox starts."))
        pv = self.form([("old", _("Current password"), "", True), ("new", _("New password"), "", True),
                        ("again", _("New password again"), "", True)])
        msg = tk.Label(self.body, bg=self.t["bg"], font=UI_FONT)

        def change():
            if pv["old"].get() != s["password"]:
                msg.config(text=_("The current password is wrong."), fg="#ff6b6b")
            elif len(pv["new"].get()) < 4:
                msg.config(text=_("The new password needs at least 4 characters."), fg="#ff6b6b")
            elif pv["new"].get() != pv["again"].get():
                msg.config(text=_("The new passwords are not the same."), fg="#ff6b6b")
            else:
                s["password"] = pv["new"].get()
                self.os.save()
                for x in pv.values():
                    x.set("")
                msg.config(text=_("Password changed!"), fg="#4caf50")
        self.btn(self.body, _("Change password"), change, True).pack(anchor="w", pady=6)
        msg.pack(anchor="w")

    def p_language(self):
        self.h(_("Language"))
        self.note(_("Choose the language of Blue Fox."))
        for code, name in LANGUAGES.items():
            sel = self.os.settings["lang"] == code
            flat_button(self.body, ("●  " if sel else "○  ") + name, lambda c=code: self.os.set_language(c, page="language"),
                        self.t, bg=self.t["accent"] if sel else self.t["panel"], fg="white" if sel else self.t["fg"],
                        padx=16, pady=8, anchor="w", width=24).pack(anchor="w", pady=3)

    def p_terminals(self):
        s, o, t = self.os.settings, self.os, self.t
        self.h(_("Terminals"))
        self.note(_("Choose which terminals you want. You can have one, two or all three."))
        for key in ("prompt", "bash", "foxcode"):
            inst = key in s["installed"]
            r = tk.Frame(self.body, bg=t["panel"])
            r.pack(fill="x", pady=3)
            tk.Label(r, text=f" {icon(key)}  {TERMINAL_NAMES[key]}", bg=t["panel"], fg=t["fg"], font=UI_BOLD,
                     width=18, anchor="w").pack(side="left", pady=6)
            tk.Label(r, text=_(next(d for k, _c, d, _s in STORE if k == key)), bg=t["panel"], fg=t["muted"],
                     font=("Segoe UI", 9), wraplength=300, justify="left").pack(side="left")
            if inst:
                self.btn(r, _("Remove"), lambda k=key: (o.store_uninstall(k), self.show("terminals"))).pack(side="right", padx=6)
            else:
                self.btn(r, _("Install"), lambda k=key: (o.store_install(k), self.show("terminals")), True).pack(
                    side="right", padx=6)
        inst = [k for k in ("prompt", "bash", "foxcode") if k in s["installed"]]
        if inst:
            self.h(_("Default terminal"))
            self.note(_("Opens with Ctrl+Alt+T and with 'Terminal here' in Files."))
            for k in inst:
                sel = o.default_terminal() == k
                flat_button(self.body, ("●  " if sel else "○  ") + TERMINAL_NAMES[k],
                            lambda k=k: (s.update(default_terminal=k), o.save(), self.show("terminals")), t,
                            bg=t["accent"] if sel else t["panel"], fg="white" if sel else t["fg"], padx=14, pady=5,
                            anchor="w", width=24).pack(anchor="w", pady=2)

    def p_browser(self):
        s, o, t = self.os.settings, self.os, self.t
        self.h(_("Browser"))
        self.note(_("Blue Fox Web is always included. You can also choose Firefox or Brave. They open as real "
                    "browsers on this computer, so they must be installed on it."))
        for key in ("firefox", "brave", "none"):
            sel = s.get("browser") == key
            label = HOST_BROWSERS[key][0] if key in HOST_BROWSERS else _("Only Blue Fox Web")
            r = tk.Frame(self.body, bg=t["bg"])
            r.pack(fill="x", pady=3)
            flat_button(r, ("●  " if sel else "○  ") + label, lambda k=key: o.set_browser(k, page="browser"), t,
                        bg=t["accent"] if sel else t["panel"], fg="white" if sel else t["fg"], padx=14, pady=6,
                        anchor="w", width=22).pack(side="left")
            if key in HOST_BROWSERS:
                found = find_host_browser(key)
                tk.Label(r, text=_("✓ found on this computer") if found else _("not on this computer"), bg=t["bg"],
                         fg="#4caf50" if found else t["muted"], font=("Segoe UI", 9)).pack(side="left", padx=10)
                if not found:
                    self.btn(r, _("Download {b}", b=HOST_BROWSERS[key][0]),
                             lambda k=key: webbrowser.open(HOST_BROWSERS[k][1])).pack(side="left")

    def p_internet(self):
        s, o, t = self.os.settings, self.os, self.t
        self.h(_("Internet"))
        var = tk.BooleanVar(value=s.get("internet", True))

        def toggle():
            s["internet"] = var.get()
            o.save()
            o.check_online()
            self.show("internet")
        tk.Checkbutton(self.body, text=_("Allow Blue Fox to use the internet"), variable=var, command=toggle,
                       bg=t["bg"], fg=t["fg"], selectcolor=t["entry"], activebackground=t["bg"],
                       activeforeground=t["fg"], font=UI_FONT).pack(anchor="w")
        self.note(_("Used by Blue Fox Web, the Fox Store links and the curl / wget / ping commands."))
        st = tk.Label(self.body, text=_("Checking the connection…"), bg=t["bg"], fg=t["muted"], font=UI_BOLD)
        st.pack(anchor="w", pady=10)

        def done(ok, res):
            if st.winfo_exists():
                if not s.get("internet", True):
                    st.config(text="● " + _("Off"), fg=t["muted"])
                elif ok and res:
                    st.config(text="● " + _("Connected to the internet"), fg="#4caf50")
                else:
                    st.config(text="● " + _("No internet connection"), fg="#ff6b6b")
        o.run_async(online_check, done)
        self.btn(self.body, _("Open Blue Fox Web"), lambda: o.launch("web"), True).pack(anchor="w")
        if have("nmcli"):
            self.wifi_section()

    def wifi_section(self):
        t, o = self.t, self.os
        self.h("Wi-Fi")
        box = tk.Frame(self.body, bg=t["bg"])
        box.pack(fill="x")
        status = tk.Label(box, text=_("Looking for Wi-Fi networks…"), bg=t["bg"], fg=t["muted"], font=UI_FONT)
        status.pack(anchor="w")

        def scan():
            code, out = sh(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
                           timeout=30)
            nets = {}
            for line in out.splitlines() if code == 0 else []:
                parts = re.split(r"(?<!\\):", line)
                if len(parts) < 4 or not parts[1]:
                    continue
                ssid = parts[1].replace("\\:", ":")
                sig = int(parts[2]) if parts[2].isdigit() else 0
                if ssid not in nets or sig > nets[ssid][0]:
                    nets[ssid] = (sig, parts[3], parts[0] == "*")
            return sorted(nets.items(), key=lambda kv: (not kv[1][2], -kv[1][0]))

        def show(ok, nets):
            if not box.winfo_exists():
                return
            for w in box.winfo_children():
                w.destroy()
            if not ok or not nets:
                tk.Label(box, text=_("No Wi-Fi networks found."), bg=t["bg"], fg=t["muted"], font=UI_FONT).pack(anchor="w")
            for ssid, (sig, sec, used) in (nets if ok else [])[:15]:
                r = tk.Frame(box, bg=t["panel"])
                r.pack(fill="x", pady=2)
                bars = "▂▄▆█"[:max(1, min(4, sig // 25 + 1))]
                tk.Label(r, text=f"  {bars:<4}  {ssid}" + ("   🔒" if USE_EMOJI and sec else ("   ●" if sec else "")),
                         bg=t["panel"], fg=t["fg"], font=UI_BOLD if used else UI_FONT, anchor="w").pack(side="left", pady=6)
                if used:
                    tk.Label(r, text=_("Connected"), bg=t["panel"], fg="#4caf50", font=UI_FONT).pack(side="right", padx=10)
                else:
                    self.btn(r, _("Connect"), lambda s=ssid, sec=sec: connect(s, sec)).pack(side="right", padx=6, pady=3)
            self.btn(box, _("Search again"), lambda: (show(True, []), o.run_async(scan, show))).pack(anchor="w", pady=6)

        def connect(ssid, secured):
            args = ["nmcli", "dev", "wifi", "connect", ssid]
            if secured:
                pw = simpledialog.askstring("Wi-Fi", _("Password for {n}:", n=ssid), show="●", parent=o.root)
                if pw is None:
                    return
                args += ["password", pw]
            o.toast(_("Connecting to {n}…", n=ssid))

            def job():
                return sh(args, timeout=45)

            def done(ok, res):
                if ok and res[0] == 0:
                    o.toast(_("Connected to {n}!", n=ssid))
                    o.check_online()
                else:
                    messagebox.showerror("Wi-Fi", _("Could not connect. Check the password.") + "\n\n" +
                                         str(res[1] if ok else res)[-300:], parent=o.root)
                if box.winfo_exists():
                    o.run_async(scan, show)
            o.run_async(job, done)
        o.run_async(scan, show)

    def p_system(self):
        o, t = self.os, self.t
        self.h(_("System"))
        size = len(json.dumps({"s": o.settings, "f": o.vfs.root}))
        for k, v in ((_("Name"), "Blue Fox"), (_("Version"), VERSION), (_("Engine"), f"Python {platform.python_version()}"),
                     (_("Storage used"), human_size(size)), (_("Data file"), DATA_FILE)):
            r = tk.Frame(self.body, bg=t["bg"])
            r.pack(anchor="w")
            tk.Label(r, text=k + ":", width=16, anchor="w", bg=t["bg"], fg=t["muted"], font=UI_FONT).pack(side="left")
            tk.Label(r, text=v, bg=t["bg"], fg=t["fg"], font=UI_FONT).pack(side="left")
        row = tk.Frame(self.body, bg=t["bg"])
        row.pack(anchor="w", pady=10)
        self.btn(row, _("Restart"), o.restart).pack(side="left", padx=(0, 6))
        self.btn(row, _("Shut down"), o.shutdown).pack(side="left")
        if SESSION:
            self.h(_("Sound and screen"))
            for label, getter, setter in ((_("Volume"), get_volume, set_volume),
                                          (_("Brightness"), get_brightness, set_brightness)):
                val = getter()
                if val is None:
                    continue
                r = tk.Frame(self.body, bg=t["bg"])
                r.pack(anchor="w", fill="x")
                tk.Label(r, text=label, width=12, anchor="w", bg=t["bg"], fg=t["fg"], font=UI_FONT).pack(side="left")
                sc = tk.Scale(r, from_=5 if setter is set_brightness else 0, to=100, orient="horizontal", length=280,
                              bg=t["bg"], fg=t["fg"], highlightthickness=0, troughcolor=t["entry"],
                              command=lambda v, f=setter: f(int(float(v))))
                sc.set(val)
                sc.pack(side="left")
        self.h(_("Reset"))
        self.note(_("Erases all Blue Fox files and settings and starts the setup again. Your computer's own "
                    "files are not touched."))
        flat_button(self.body, _("Reset Blue Fox…"), o.factory_reset, t, bg="#c62828", fg="white", padx=12,
                    pady=5).pack(anchor="w", pady=4)


# ════════════════════════════════════════════════════════════════════
#  THE OPERATING SYSTEM
# ════════════════════════════════════════════════════════════════════
APPS = {
    "files": dict(name="Files", icon="files", cls=FileExplorer, core=True, desk=True),
    "web": dict(name="Blue Fox Web", icon="web", cls=WebBrowser, core=True, desk=True),
    "store": dict(name="Fox Store", icon="store", cls=FoxStore, core=True, desk=True),
    "notepad": dict(name="Notepad", icon="notepad", cls=Notepad, core=True, desk=True),
    "settings": dict(name="Settings", icon="settings", cls=Settings, core=True, desk=True),
    "calc": dict(name="Calculator", icon="calc", cls=Calculator, core=True, desk=False),
    "calendar": dict(name="Calendar", icon="calendar", cls=CalendarApp, core=True, desk=False),
    "taskmgr": dict(name="Task Manager", icon="taskmgr", cls=TaskManager, core=True, desk=False),
    "about": dict(name="About Blue Fox", icon="about", cls=About, core=True, desk=False),
    "programs": dict(name="Programs", icon="programs", cls=ProgramsApp, core=True, desk=True, only_session=True),
    "prompt": dict(name="Prompt", icon="prompt", cls=Terminal, kw=dict(dialect="prompt"), desk=True),
    "bash": dict(name="Bash", icon="bash", cls=Terminal, kw=dict(dialect="bash"), desk=True),
    "foxcode": dict(name="Blue Fox Code", icon="foxcode", cls=Terminal, kw=dict(dialect="foxcode"), desk=True),
    "snake": dict(name="Snake", icon="snake", cls=Snake, desk=True),
    "mines": dict(name="Minesweeper", icon="mines", cls=Minesweeper, desk=True),
    "2048": dict(name="2048", icon="2048", cls=Game2048, desk=True),
    "ttt": dict(name="Tic-Tac-Toe", icon="ttt", cls=TicTacToe, desk=True),
    "pong": dict(name="Pong", icon="pong", cls=Pong, desk=True),
    "paint": dict(name="Paint", icon="paint", cls=Paint, desk=True),
    "python": dict(name="Python", icon="python", cls=PythonIDE, desk=True),
    "turtle": dict(name="Fox Turtle", icon="turtle", cls=FoxTurtle, desk=True),
    "firefox": dict(name="Firefox", icon="firefox", cls=HostBrowserApp, kw=dict(which="firefox"), desk=True),
    "brave": dict(name="Brave", icon="brave", cls=HostBrowserApp, kw=dict(which="brave"), desk=True),
}
TERMINAL_KEYS = ("prompt", "bash", "foxcode")


def get_volume():
    if have("pactl"):
        code, out = sh(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], timeout=5)
        m = re.search(r"(\d+)%", out)
        if code == 0 and m:
            return int(m.group(1))
    if have("amixer"):
        code, out = sh(["amixer", "get", "Master"], timeout=5)
        m = re.search(r"\[(\d+)%\]", out)
        if code == 0 and m:
            return int(m.group(1))
    return None


def set_volume(v):
    if have("pactl"):
        sh(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], timeout=5)
        if sh(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%"], timeout=5)[0] == 0:
            return
    sh(["amixer", "-q", "set", "Master", f"{v}%", "unmute"], timeout=5)


def get_brightness():
    if not have("brightnessctl"):
        return None
    code, cur = sh(["brightnessctl", "g"], timeout=5)
    code2, mx = sh(["brightnessctl", "m"], timeout=5)
    try:
        return int(int(cur) * 100 / max(1, int(mx))) if code == 0 and code2 == 0 else None
    except ValueError:
        return None


def set_brightness(v):
    sh(["brightnessctl", "-q", "s", f"{max(5, v)}%"], timeout=5)


def mix(c1, c2, f):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


class OS:
    def __init__(self, root):
        self.root = root
        self.boot_time = time.time()
        self.windows = []
        self.active = None
        self.launching = None
        self.fs_listeners = set()
        self.store_listeners = set()
        self.start_open = False
        self.online = None
        self._wall_cache = (None, None)
        self._icon_imgs = {}
        self.load()
        self.ext_windows = []
        if SESSION:
            root.title("BlueFoxDesktop")
            root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
            try:
                root.attributes("-fullscreen", True)
            except tk.TclError:
                pass
        else:
            root.title(f"{APP_NAME} {VERSION}")
            root.geometry("1280x780")
            root.minsize(940, 620)
        root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.build()
        root.bind_all("<Button-1>", self.global_click, add="+")
        root.bind_all("<Control-Escape>", lambda e: self.toggle_start())
        root.bind_all("<Control-Alt-t>", lambda e: self.open_default_terminal())
        root.bind_all("<Control-Shift-Escape>", lambda e: self.launch("taskmgr"))
        if self.settings["setup_done"]:
            self.boot_screen(then=self.login_screen)
        else:
            self.boot_screen(then=lambda: SetupWizard(self))
        self.root.after(1500, self.check_online_loop)
        if SESSION and have("wmctrl"):
            self.root.after(2500, self.poll_ext_windows)
        self.root.after(2000, self.battery_loop)

    # ---------- data ----------
    def load(self):
        data = {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa
            pass
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        self.settings.update(data.get("settings", {}))
        LANG["code"] = self.settings.get("lang", "en")
        self.vfs = VFS(data.get("fs"))

    def save(self):
        try:
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"settings": self.settings, "fs": self.vfs.root}, f, ensure_ascii=False)
            os.replace(tmp, DATA_FILE)
        except Exception as e:  # noqa
            print("Could not save:", e)

    def fs_changed(self):
        for fn in list(self.fs_listeners):
            try:
                fn()
            except tk.TclError:
                self.fs_listeners.discard(fn)
        self.draw_icons()

    @property
    def theme(self):
        return THEMES.get(self.settings["theme"], THEMES["dark"])

    def ask_text(self, prompt, initial=""):
        return simpledialog.askstring(APP_NAME, prompt, initialvalue=initial, parent=self.root)

    def run_async(self, fn, cb):
        """Run fn() in the background (e.g. internet) and call cb(ok, result) when done."""
        q = queue.Queue()

        def worker():
            try:
                q.put((True, fn()))
            except Exception as e:  # noqa
                q.put((False, str(getattr(e, "reason", e))))
        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                ok, res = q.get_nowait()
            except queue.Empty:
                self.root.after(60, poll)
                return
            cb(ok, res)
        self.root.after(60, poll)

    # ---------- apps ----------
    def app_name(self, key):
        return _(APPS[key]["name"]) if key in APPS else key

    def app_available(self, key):
        if key in APPS and APPS[key].get("only_session") and not SESSION:
            return False
        return key in APPS and (APPS[key].get("core") or key in self.settings["installed"])

    def available_apps(self):
        return [k for k in APPS if self.app_available(k)]

    def store_missing(self):
        return [k for k, *_r in STORE if k not in self.settings["installed"]]

    def find_app(self, text):
        q = text.strip().lower().replace(" ", "").replace("-", "")
        aliases = {"terminal": self.default_terminal() or "bash", "cmd": "prompt", "browser": "web",
                   "store": "store", "minesweeper": "mines", "tictactoe": "ttt", "calculator": "calc",
                   "tasks": "taskmgr", "foxturtle": "turtle", "bluefoxcode": "foxcode", "fox": "foxcode"}
        if q in APPS:
            return q
        if q in aliases:
            return aliases[q]
        for k, a in APPS.items():
            if q in (a["name"].lower().replace(" ", "").replace("-", ""),
                     _(a["name"]).lower().replace(" ", "").replace("-", "")):
                return k
        return None

    def launch(self, key, **kw):
        self.hide_start()
        if not self.app_available(key):
            if key in STORE_KEYS and messagebox.askyesno("Fox Store", _("{a} is not installed. Install it now?",
                                                                        a=self.app_name(key)), parent=self.root):
                self.store_install(key)
            else:
                return None
        a = APPS[key]
        args = dict(a.get("kw", {}))
        args.update(kw)
        self.launching = key
        try:
            return a["cls"](self, **args)
        except Exception as ex:  # noqa
            traceback.print_exc()
            messagebox.showerror(_("App error"), f"{self.app_name(key)}: {ex}", parent=self.root)
        finally:
            self.launching = None

    def default_terminal(self):
        d = self.settings.get("default_terminal")
        if d in self.settings["installed"]:
            return d
        return next((k for k in TERMINAL_KEYS if k in self.settings["installed"]), None)

    def open_default_terminal(self):
        k = self.default_terminal()
        if k:
            self.launch(k)
        else:
            self.launch("store", category="Terminals")

    def open_path(self, path):
        if self.vfs.is_dir(path):
            self.launch("files", path=path)
        elif self.vfs.is_file(path):
            node = self.vfs.get(path)
            if VFS.is_binary(node):
                self.launching = "image"
                try:
                    ImageViewer(self, path=path)
                finally:
                    self.launching = None
            elif path.endswith(".py") and self.app_available("python"):
                self.launch("python", path=path)
            else:
                self.launch("notepad", path=path)

    def store_install(self, key):
        if key not in self.settings["installed"]:
            self.settings["installed"].append(key)
        d = self.settings.get("desk_apps")
        if d is not None and APPS[key]["desk"] and key not in d:
            d.append(key)
        self.save()
        self.after_apps_changed()

    def store_uninstall(self, key):
        if key in self.settings["installed"]:
            self.settings["installed"].remove(key)
        for w in [w for w in self.windows if w.app_key == key]:
            w.on_close = None
            w.close()
        if self.settings.get("default_terminal") == key:
            self.settings.pop("default_terminal", None)
        if self.settings.get("browser") == key:
            self.settings["browser"] = "none"
        self.save()
        self.after_apps_changed()

    def after_apps_changed(self):
        self.draw_icons()
        self.fill_start()
        for fn in list(self.store_listeners):
            try:
                fn()
            except tk.TclError:
                self.store_listeners.discard(fn)

    def set_browser(self, key, page=None):
        old = self.settings.get("browser")
        if old in HOST_BROWSERS and old != key and old in self.settings["installed"]:
            self.settings["installed"].remove(old)
        self.settings["browser"] = key
        if key in HOST_BROWSERS and key not in self.settings["installed"]:
            self.settings["installed"].append(key)
        self.save()
        self.after_apps_changed()
        if page:
            self.reopen_settings(page)

    def open_host_browser(self, which, url):
        if which not in HOST_BROWSERS:
            self.launch("web", url=url)
            return
        name, download = HOST_BROWSERS[which]
        if not self.settings.get("internet", True):
            messagebox.showinfo(name, _("The internet is turned off in Settings → Internet."), parent=self.root)
            return
        exe = find_host_browser(which)
        if exe:
            try:
                if platform.system() == "Darwin" and exe.endswith(("firefox", "Brave Browser")):
                    subprocess.Popen(["open", "-a", exe.split("/Contents/")[0], url])
                else:
                    subprocess.Popen([exe, url])
                self.toast(_("Opening {b}…", b=name))
                return
            except OSError as e:
                messagebox.showerror(name, str(e), parent=self.root)
                return
        if messagebox.askyesno(name, _("{b} is not installed on this computer yet.\n\nOpen the official {b} "
                                       "download page?", b=name), parent=self.root):
            webbrowser.open(download)

    # ---------- real programs of the computer (Blue Fox as OS) ----------
    apt_busy = {}
    _pkg_cache = {}
    _apt_updated = False

    def pkg_installed(self, pkg):
        if pkg not in self._pkg_cache:
            code, out = sh(["dpkg-query", "-W", "-f=${Status}", pkg], timeout=10)
            self._pkg_cache[pkg] = code == 0 and "install ok installed" in out
        return self._pkg_cache[pkg]

    def apt(self, action, pkg, name):
        if action == "remove" and not messagebox.askyesno("Fox Store", _("Remove {a}?", a=name), parent=self.root):
            return
        if action == "install" and not online_check():
            messagebox.showinfo("Fox Store", _("You need the internet to install computer apps. "
                                               "Connect in Settings → Internet."), parent=self.root)
            return
        self.apt_busy[pkg] = _("Installing…") if action == "install" else _("Removing…")
        self.after_apps_changed()
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")

        def job():
            if action == "install" and not OS._apt_updated:
                subprocess.run(["sudo", "-n", "apt-get", "update"], capture_output=True, env=env, timeout=600)
                OS._apt_updated = True
            p = subprocess.run(["sudo", "-n", "apt-get", "-y", action, pkg], capture_output=True, text=True,
                               env=env, timeout=3600)
            return p.returncode, (p.stdout + p.stderr)[-600:]

        def done(ok, res):
            self.apt_busy.pop(pkg, None)
            self._pkg_cache.pop(pkg, None)
            if ok and res[0] == 0:
                self.toast((_("Installed: {a}") if action == "install" else _("Removed: {a}")).format(a=name))
            else:
                messagebox.showerror("Fox Store", _("It did not work:") + "\n\n" + str(res[1] if ok else res)[-400:],
                                     parent=self.root)
            self.after_apps_changed()
        self.run_async(job, done)

    def run_program(self, args):
        try:
            subprocess.Popen(args, cwd=REAL_HOME, start_new_session=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.toast(_("Opening {b}…", b=args[0]))
        except OSError as e:
            messagebox.showerror("Blue Fox", str(e), parent=self.root)

    # ---------- files in / out ----------
    MAX_IMPORT = 25 * 1024 * 1024

    def _import_one(self, real, target):
        if os.path.getsize(real) > self.MAX_IMPORT:
            raise ValueError(_("file too big (limit 25 MB)"))
        with open(real, "rb") as f:
            self.vfs.write_bytes(target, f.read())

    def _after_import(self, n, errors, dest):
        if n:
            self.save()
            self.fs_changed()
            self.toast(_("{n} files arrived in {p}", n=n, p=dest))
        if errors:
            messagebox.showwarning(_("Bring in files"), _("Some files were not copied:") + "\n\n" +
                                   "\n".join(errors[:15]), parent=self.root)

    def import_files(self, dest):
        paths = filedialog.askopenfilenames(title=_("Choose files from your computer for Blue Fox"), parent=self.root)
        n, errors = 0, []
        for p in paths:
            try:
                self._import_one(p, self.vfs.free_name(dest, os.path.basename(p)))
                n += 1
            except Exception as ex:  # noqa
                errors.append(f"{os.path.basename(p)}: {err_text(ex)}")
        self._after_import(n, errors, dest)
        return n

    def import_folder(self, dest):
        src = filedialog.askdirectory(title=_("Choose a folder from your computer for Blue Fox"), parent=self.root)
        if not src:
            return 0
        root_target = self.vfs.free_name(dest, os.path.basename(os.path.normpath(src)) or "Folder")
        n, errors = 0, []
        try:
            self.vfs.mkdir(root_target)
            for cur, _dirs, files in os.walk(src):
                rel = os.path.relpath(cur, src).replace("\\", "/")
                vdir = root_target if rel == "." else self.vfs.norm(rel, root_target)
                if not self.vfs.get(vdir):
                    self.vfs.mkdir(vdir, parents=True)
                for fname in files:
                    if n >= 2000:
                        raise ValueError(_("too many files (limit 2000)"))
                    try:
                        self._import_one(os.path.join(cur, fname), self.vfs.norm(fname, vdir))
                        n += 1
                    except (OSError, ValueError) as ex:
                        errors.append(f"{fname}: {err_text(ex)}")
        except Exception as ex:  # noqa
            errors.append(err_text(ex))
        self._after_import(n, errors, dest)
        return n

    def export_path(self, path):
        name = VFS.split(path)[1] or "BlueFox"
        try:
            if self.vfs.is_dir(path):
                dest = filedialog.askdirectory(title=_("Where on your computer should the folder go?"), parent=self.root)
                if not dest:
                    return
                out = os.path.join(dest, name)
                if os.path.exists(out):
                    out += " (Blue Fox)"

                def rec(vpath, real):
                    os.makedirs(real, exist_ok=True)
                    for child in self.vfs.listdir(vpath):
                        cp = self.vfs.norm(child, vpath)
                        rp = os.path.join(real, re.sub(r'[<>:"|?*]', "_", child))
                        if self.vfs.is_dir(cp):
                            rec(cp, rp)
                        else:
                            with open(rp, "wb") as f:
                                f.write(self.vfs.get_bytes(cp))
                rec(path, out)
            else:
                out = filedialog.asksaveasfilename(title=_("Save to your computer"), initialfile=name, parent=self.root)
                if not out:
                    return
                with open(out, "wb") as f:
                    f.write(self.vfs.get_bytes(path))
            self.toast(_("Saved to your computer: {p}", p=out))
        except Exception as ex:  # noqa
            messagebox.showerror(_("Save to computer"), err_text(ex), parent=self.root)

    # ---------- user interface ----------
    def build(self):
        t = self.theme
        self.root.configure(bg=t["title"])
        self.taskbar = tk.Frame(self.root, bg=t["taskbar"], height=44)
        self.taskbar.pack(side="bottom", fill="x")
        self.taskbar.pack_propagate(False)
        self.start_btn = tk.Label(self.taskbar, text=f"  {icon('start')}  Blue Fox  ", bg=t["taskbar"], fg=t["accent"],
                                  font=("Segoe UI", 11, "bold"), cursor="hand2")
        self.start_btn.pack(side="left", fill="y", padx=(2, 4))
        self.start_btn.bind("<ButtonRelease-1>", lambda e: self.toggle_start())
        self.start_btn.bind("<Enter>", lambda e: self.start_btn.config(bg=t["hover"]))
        self.start_btn.bind("<Leave>", lambda e: self.start_btn.config(bg=t["taskbar"]))
        self.quick = tk.Frame(self.taskbar, bg=t["taskbar"])
        self.quick.pack(side="left", fill="y")
        tk.Frame(self.taskbar, bg=t["hover"], width=1).pack(side="left", fill="y", pady=8, padx=6)
        self.task_area = tk.Frame(self.taskbar, bg=t["taskbar"])
        self.task_area.pack(side="left", fill="both", expand=True)
        self.clock = tk.Label(self.taskbar, bg=t["taskbar"], fg=t["fg"], font=("Segoe UI", 9), justify="right",
                              cursor="hand2")
        self.clock.pack(side="right", padx=12)
        self.clock.bind("<ButtonRelease-1>", lambda e: self.launch("calendar"))
        self.net_label = tk.Label(self.taskbar, bg=t["taskbar"], fg=t["muted"], font=("Segoe UI", 9), cursor="hand2")
        self.net_label.pack(side="right", padx=6)
        self.net_label.bind("<ButtonRelease-1>", lambda e: self.launch("settings", page="internet"))
        self.bat_label = tk.Label(self.taskbar, bg=t["taskbar"], fg=t["muted"], font=("Segoe UI", 9))
        self.bat_label.pack(side="right", padx=4)
        self.lang_label = tk.Label(self.taskbar, text=self.settings["lang"].upper(), bg=t["taskbar"], fg=t["muted"],
                                   font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.lang_label.pack(side="right", padx=4)
        self.lang_label.bind("<ButtonRelease-1>", lambda e: self.set_language("el" if self.settings["lang"] == "en" else "en"))
        self.tick_clock()
        self.show_net()

        self.desktop = tk.Canvas(self.root, highlightthickness=0, bg=self.settings["wall1"])
        self.desktop.pack(fill="both", expand=True)
        self.desktop.bind("<Configure>", lambda e: self.draw_desktop())
        self.desktop.bind("<ButtonPress-1>", self._desk_press)
        self.desktop.bind("<B1-Motion>", self._icon_motion)
        self.desktop.bind("<ButtonRelease-1>", self._icon_release)
        self.desktop.bind("<Double-Button-1>", self._desk_double)
        self.desktop.bind("<Button-3>", self.desktop_menu)
        self.desktop.bind("<Button-2>", self.desktop_menu)
        self.build_start_menu()

    # ---------- taskbar (pinned items) ----------
    def pinned(self):
        p = self.settings.get("pinned")
        if p is None:
            p = ["app:files", "app:web", "app:store"]
            if self.default_terminal():
                p.append("app:" + self.default_terminal())
        return p

    def toggle_pin(self, iid):
        p = list(self.pinned())
        if iid in p:
            p.remove(iid)
        else:
            p.append(iid)
        self.settings["pinned"] = p
        self.save()
        self.fill_quick()

    # drag pinned taskbar icons to change their order (click without moving = open)
    def _pin_press(self, e, iid, widget):
        self._pdrag = dict(iid=iid, w=widget, x=e.x_root, moved=False)

    def _pin_motion(self, e):
        d = getattr(self, "_pdrag", None)
        if d and not d["moved"] and abs(e.x_root - d["x"]) > 8:
            d["moved"] = True
            d["w"].config(cursor="fleur", bg=self.theme["accent"])

    def _pin_release(self, e, open_fn):
        d, self._pdrag = getattr(self, "_pdrag", None), None
        if not d:
            return
        if not d["moved"]:
            open_fn()
            return
        others = [(i, w) for i, w in self._pin_widgets if i != d["iid"]]
        pos = sum(1 for _i, w in others if w.winfo_rootx() + w.winfo_width() / 2 < e.x_root)
        p = [i for i in self.pinned() if i != d["iid"]]
        if pos < len(others):
            p.insert(p.index(others[pos][0]), d["iid"])
        else:
            p.append(d["iid"])
        self.settings["pinned"] = p
        self.save()
        self.fill_quick()

    def fill_quick(self):
        if not hasattr(self, "quick") or not self.quick.winfo_exists():
            return
        t = self.theme
        for w in self.quick.winfo_children():
            w.destroy()
        self._pin_widgets = []
        for iid in self.pinned():
            info = self.item_info(iid)
            if not info:
                continue
            name, sym, cmd = info
            c = tk.Canvas(self.quick, width=40, height=40, bg=t["taskbar"], highlightthickness=0, cursor="hand2")
            c.pack(side="left", padx=1, pady=2)
            self.draw_tile(c, 20, 20, self.icon_look(iid), sym, 28, ())
            c.bind("<ButtonPress-1>", lambda e, i=iid, c=c: self._pin_press(e, i, c))
            c.bind("<B1-Motion>", self._pin_motion)
            c.bind("<ButtonRelease-1>", lambda e, f=cmd: self._pin_release(e, f))
            self._pin_widgets.append((iid, c))
            c.bind("<Enter>", lambda e, c=c: c.config(bg=t["hover"]))
            c.bind("<Leave>", lambda e, c=c: c.config(bg=t["taskbar"]))
            c.bind("<Button-3>", lambda e, i=iid: self.icon_menu(e, i))
            c.bind("<Button-2>", lambda e, i=iid: self.icon_menu(e, i))

    def draw_desktop(self):
        cv = self.desktop
        cv.delete("wall")
        w, h = cv.winfo_width(), cv.winfo_height()
        steps = 64
        for i in range(steps):
            cv.create_rectangle(0, h * i / steps, w, h * (i + 1) / steps + 1, outline="", tags="wall",
                                fill=mix(self.settings["wall1"], self.settings["wall2"], i / (steps - 1)))
        pic = self.settings.get("wall_image")
        if pic and self.vfs.is_file(pic) and w > 10:
            key = (pic, w, h)
            if self._wall_cache[0] != key:
                try:
                    img = tk.PhotoImage(data=self.vfs.get(pic)["b64"])
                    iw, ih = img.width(), img.height()
                    if iw < w or ih < h:
                        z = min(4, math.ceil(max(w / iw, h / ih)))
                        img = img.zoom(z)
                    else:
                        s = max(1, int(min(iw / w, ih / h)))
                        img = img.subsample(s) if s > 1 else img
                    self._wall_cache = (key, img)
                except (tk.TclError, KeyError, TypeError):
                    self._wall_cache = (key, None)
            if self._wall_cache[1] is not None:
                cv.create_image(w // 2, h // 2, image=self._wall_cache[1], tags="wall")
        cv.create_text(w - 30, h - 26, text="Blue Fox", anchor="se", fill="#ffffff", font=("Segoe UI", 22, "bold"),
                       tags="wall")
        cv.create_text(w - 32, h - 60, text=f"{_('Version')} {VERSION}", anchor="se", fill="#cfe3ff",
                       font=("Segoe UI", 9), tags="wall")
        cv.tag_lower("wall")
        self.draw_icons()

    # ---------- desktop icons ----------
    def desk_apps(self):
        d = self.settings.get("desk_apps")
        return list(d) if d is not None else [k for k, a in APPS.items() if a["desk"]]

    def set_on_desktop(self, key, on):
        d = self.desk_apps()
        if on and key not in d:
            d.append(key)
        elif not on and key in d:
            d.remove(key)
        self.settings["desk_apps"] = d
        self.save()
        self.draw_icons()

    def desktop_items(self):
        items = ["app:" + k for k in self.desk_apps() if self.app_available(k)]
        desk = HOME + "/Desktop"
        if self.vfs.is_dir(desk):
            items += [f"file:{desk}/{n}" for n in self.vfs.listdir(desk)]
        return items

    def item_info(self, iid):
        """(label, default symbol, open function) - or None if the item no longer exists."""
        if iid.startswith("app:"):
            key = iid[4:]
            if not self.app_available(key):
                return None
            return self.app_name(key), icon(APPS[key]["icon"]), lambda: self.launch(key)
        path = iid[5:]
        node = self.vfs.get(path)
        if not node:
            return None
        if node["type"] == "dir":
            sym = icon("folder")
        elif path.lower().endswith((".png", ".gif", ".jpg", ".jpeg")):
            sym = icon("image")
        else:
            sym = icon("file")
        return VFS.split(path)[1], sym, lambda: self.open_path(path)

    def item_color(self, iid):
        if not iid:
            return "#2f7de1"
        if iid.startswith("app:"):
            return APP_COLORS.get(iid[4:], "#2f7de1")
        path = iid[5:]
        if self.vfs.is_dir(path):
            return APP_COLORS["folder"]
        return APP_COLORS["image" if path.lower().endswith((".png", ".gif", ".jpg", ".jpeg")) else "file"]

    def icon_look(self, iid=None):
        look = dict(ICON_LOOK)
        look.update(style_look(self.settings.get("icon_style", "plain"), self.item_color(iid)))
        look.update(self.settings.get("icon_default", {}))
        if iid:
            look.update(self.settings.get("icons", {}).get(iid, {}))
        return look

    def icon_photo(self, path, size):
        key = (path, size)
        if key not in self._icon_imgs:
            try:
                img = tk.PhotoImage(data=self.vfs.get(path)["b64"])
                f = max(1, math.ceil(max(img.width(), img.height()) / size))
                self._icon_imgs[key] = img.subsample(f) if f > 1 else img
            except (tk.TclError, KeyError, TypeError):
                self._icon_imgs[key] = None
        return self._icon_imgs[key]

    def draw_tile(self, cv, cx, cy, look, default_sym, size, tags):
        """Draw one icon (shape + symbol, or a picture) centred on cx, cy."""
        r = size / 2
        shape, bg = look.get("shape", "none"), look.get("bg", "#2f7de1")
        if shape == "circle":
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=bg, outline="", tags=tags)
        elif shape == "square":
            cv.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill=bg, outline="", tags=tags)
        elif shape == "rounded":
            cv.create_polygon(rounded_pts(cx - r, cy - r, cx + r, cy + r, r * 0.45), smooth=True, fill=bg,
                              outline="", tags=tags)
        pic = look.get("image")
        if pic and self.vfs.is_file(pic):
            img = self.icon_photo(pic, int(size * (0.8 if shape != "none" else 1)))
            if img is not None:
                cv.create_image(cx, cy, image=img, tags=tags)
                return
        sym = look.get("symbol") or default_sym
        scale = 0.46 if len(sym) <= 1 else (0.36 if len(sym) == 2 else 0.27)
        cv.create_text(cx, cy, text=sym, fill=look.get("fg", "#ffffff"), tags=tags,
                       font=("Segoe UI", max(7, int(size * scale)), "bold"))

    def draw_icons(self):
        cv = self.desktop
        cv.delete("icon")
        w, h = max(cv.winfo_width(), 400), max(cv.winfo_height(), 400)
        pos = self.settings.setdefault("icon_pos", {})
        items = self.desktop_items()
        taken = [tuple(pos[i]) for i in items if i in pos]
        per_col = max(1, (h - 20) // 92)
        slot = 0
        self._icon_xy, self._icon_tags, self._icon_cmds = {}, {}, {}
        self._tag_of = {}
        for i, iid in enumerate(items):
            info = self.item_info(iid)
            if not info:
                continue
            name, sym, cmd = info
            if iid in pos:
                x = min(max(46, pos[iid][0]), w - 46)
                y = min(max(4, pos[iid][1]), h - 88)
            else:
                while True:   # next free grid place
                    x, y = 60 + (slot // per_col) * 96, 14 + (slot % per_col) * 92
                    slot += 1
                    if all(abs(x - tx) > 60 or abs(y - ty) > 60 for tx, ty in taken):
                        break
            self._icon_xy[iid] = (x, y)
            tag = f"icon{i}"
            self._icon_tags[tag] = iid
            self._tag_of[iid] = tag
            label = name if len(name) <= 14 else name[:12] + "…"
            cv.create_rectangle(x - 42, y, x + 42, y + 84, outline="", fill="", tags=("icon", tag, tag + "bg"))
            self.draw_tile(cv, x, y + 30, self.icon_look(iid), sym, 50, ("icon", tag))
            cv.create_text(x + 1, y + 70, text=label, font=("Segoe UI", 9), fill="black", width=88,
                           justify="center", tags=("icon", tag))
            cv.create_text(x, y + 69, text=label, font=("Segoe UI", 9), fill="white", width=88,
                           justify="center", tags=("icon", tag))
            self._icon_cmds[iid] = cmd
            cv.tag_bind(tag, "<Enter>", lambda e, t=tag: cv.itemconfig(t + "bg", fill="#ffffff", stipple="gray25"))
            cv.tag_bind(tag, "<Leave>", lambda e, t=tag: cv.itemconfig(t + "bg", fill=""))
        self.fill_quick()

    # dragging icons around: hold the click on an icon and move the mouse
    def icon_at(self, x, y):
        for iid, (ix, iy) in reversed(list(getattr(self, "_icon_xy", {}).items())):
            if ix - 42 <= x <= ix + 42 and iy <= y <= iy + 86:
                return iid
        return None

    def _desk_press(self, e):
        iid = self.icon_at(e.x, e.y)
        self._drag = None
        if iid:
            tag = self._tag_of[iid]
            self._drag = dict(tag=tag, iid=iid, sx=e.x, sy=e.y, lx=e.x, ly=e.y, moved=False)
            self.desktop.itemconfig(tag + "bg", fill="#ffffff", stipple="gray25")

    def _desk_double(self, e):
        iid = self.icon_at(e.x, e.y)
        if iid and iid in self._icon_cmds:
            self._drag = None
            self._icon_cmds[iid]()

    def _icon_motion(self, e):
        d = getattr(self, "_drag", None)
        if not d:
            return
        if not d["moved"] and abs(e.x - d["sx"]) + abs(e.y - d["sy"]) < 6:
            return
        d["moved"] = True
        self.desktop.move(d["tag"], e.x - d["lx"], e.y - d["ly"])
        self.desktop.tag_raise(d["tag"])
        d["lx"], d["ly"] = e.x, e.y

    def _icon_release(self, e):
        d, self._drag = getattr(self, "_drag", None), None
        if d and not d["moved"]:
            self.desktop.itemconfig(d["tag"] + "bg", fill="")
        if not d or not d["moved"]:
            return
        x0, y0 = self._icon_xy.get(d["iid"], (60, 14))
        self.settings["icon_pos"][d["iid"]] = [int(round((x0 + e.x - d["sx"]) / 8) * 8),
                                                int(round((y0 + e.y - d["sy"]) / 8) * 8)]
        self.save()
        self.draw_icons()

    def set_icon_style(self, style):
        self.settings["icon_style"] = style
        self.settings["icon_default"] = {}
        self._icon_imgs = {}
        self.save()
        self.draw_icons()
        self.toast(_("Icon style: {s}", s=_(dict(ICON_STYLES)[style])))

    def arrange_icons(self):
        self.settings["icon_pos"] = {}
        self.save()
        self.draw_icons()

    def icon_menu(self, e, iid):
        info = self.item_info(iid)
        if not info:
            return
        t = self.theme
        m = tk.Menu(self.root, tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"],
                    activeforeground="white", font=UI_FONT)
        m.add_command(label=_("Open"), command=info[2])
        m.add_command(label=_("Change icon…"), command=lambda: IconEditor(self, iid))
        m.add_command(label=_("Unpin from taskbar") if iid in self.pinned() else _("Pin to taskbar"),
                      command=lambda: self.toggle_pin(iid))
        if iid.startswith("app:") and iid[4:] in self.desk_apps():
            m.add_command(label=_("Remove from desktop"), command=lambda: self.set_on_desktop(iid[4:], False))
        m.add_separator()
        if iid in self.settings.get("icons", {}):
            m.add_command(label=_("Original icon"), command=lambda: self.reset_icon(iid))
        if iid in self.settings.get("icon_pos", {}):
            m.add_command(label=_("Put back in its place"), command=lambda: self.reset_pos(iid))
        st = tk.Menu(m, tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"],
                     activeforeground="white", font=UI_FONT)
        cur_style = self.settings.get("icon_style", "plain")
        for key, name in ICON_STYLES:
            st.add_command(label=("●  " if key == cur_style else "○  ") + _(name),
                           command=lambda k=key: self.set_icon_style(k))
        m.add_cascade(label=_("Icon style (all icons)"), menu=st)
        m.add_command(label=_("Change the look of all icons…"), command=lambda: IconEditor(self, None))
        m.tk_popup(e.x_root, e.y_root)

    def reset_icon(self, iid):
        self.settings.get("icons", {}).pop(iid, None)
        self.save()
        self.draw_icons()

    def reset_pos(self, iid):
        self.settings.get("icon_pos", {}).pop(iid, None)
        self.save()
        self.draw_icons()

    def build_start_menu(self):
        t = self.theme
        m = self.start_menu = tk.Frame(self.desktop, bg=t["panel"], highlightthickness=1, highlightbackground=t["hover"])
        head = tk.Frame(m, bg=t["panel"])
        head.pack(fill="x", padx=14, pady=(14, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.fill_start())
        self.search = entry(head, t, self.search_var, font=("Segoe UI", 11))
        self.search.pack(fill="x", ipady=6)
        self.search.bind("<Return>", lambda e: self._start_matches and self.launch(self._start_matches[0]))
        self.search.bind("<Escape>", lambda e: self.hide_start())
        tk.Label(m, text=_("Apps"), bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16)
        self.start_sf = ScrollFrame(m, t["panel"])
        self.start_sf.pack(fill="both", expand=True, padx=6, pady=4)
        foot = tk.Frame(m, bg=t["title"])
        foot.pack(fill="x", side="bottom")
        self.user_label = tk.Label(foot, bg=t["title"], fg=t["fg"], font=UI_BOLD)
        self.user_label.pack(side="left", padx=14, pady=10)
        for ic, cmd in (("power", self.shutdown), ("restart", self.restart), ("lock", self.lock_screen)):
            flat_button(foot, icon(ic), lambda c=cmd: (self.hide_start(), c()), t, bg=t["title"],
                        font=("Segoe UI", 13), width=3).pack(side="right", fill="y")
        self.fill_start()

    def fill_start(self):
        if not hasattr(self, "start_sf"):
            return
        t = self.theme
        for w in self.start_sf.inner.winfo_children():
            w.destroy()
        q = self.search_var.get().strip().lower()
        self._start_matches = []
        keys = sorted(self.available_apps(), key=lambda k: self.app_name(k).lower())
        for key in keys:
            name = self.app_name(key)
            if q and q not in name.lower() and q not in key:
                continue
            self._start_matches.append(key)
            b = flat_button(self.start_sf.inner, f"   {icon(APPS[key]['icon'])}    {name}", lambda k=key: self.launch(k),
                            t, anchor="w", font=("Segoe UI", 11), pady=5)
            b.pack(fill="x")
            b.bind("<Button-3>", lambda e, k=key: self.start_item_menu(e, k))
            b.bind("<Button-2>", lambda e, k=key: self.start_item_menu(e, k))
        if not self._start_matches:
            tk.Label(self.start_sf.inner, text=_("No app found"), bg=t["panel"], fg=t["muted"], font=UI_FONT).pack(pady=20)

    def start_item_menu(self, e, key):
        t = self.theme
        iid = "app:" + key
        m = tk.Menu(self.root, tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"],
                    activeforeground="white", font=UI_FONT)
        m.add_command(label=_("Open"), command=lambda: self.launch(key))
        m.add_command(label=_("Unpin from taskbar") if iid in self.pinned() else _("Pin to taskbar"),
                      command=lambda: self.toggle_pin(iid))
        on = key in self.desk_apps()
        m.add_command(label=_("Remove from desktop") if on else _("Add to desktop"),
                      command=lambda: self.set_on_desktop(key, not on))
        m.add_command(label=_("Change icon…"), command=lambda: (self.hide_start(), IconEditor(self, iid)))
        m.tk_popup(e.x_root, e.y_root)

    def toggle_start(self):
        if self.start_open:
            self.hide_start()
            return
        self.user_label.config(text=f"●  {self.settings['username']}")
        self.search_var.set("")
        self.start_menu.place(x=6, rely=1.0, y=-6, anchor="sw", width=320, height=500)
        self.start_menu.lift()
        self.start_open = True
        self.search.focus_set()

    def hide_start(self):
        if hasattr(self, "start_menu"):
            self.start_menu.place_forget()
        self.start_open = False

    def global_click(self, e):
        w = e.widget
        if isinstance(w, str):
            return
        node, win, in_start = w, None, False
        while node is not None:
            if isinstance(node, Window) and win is None:
                win = node
            if node is getattr(self, "start_menu", None) or node is getattr(self, "start_btn", None):
                in_start = True
            node = getattr(node, "master", None)
        if win is not None and win in self.windows:
            self.focus_window(win)
        if self.start_open and not in_start:
            self.hide_start()

    def desktop_menu(self, e):
        hit = self.icon_at(e.x, e.y)
        if hit:
            return self.icon_menu(e, hit)
        t = self.theme
        kw = dict(tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"], activeforeground="white", font=UI_FONT)
        m = tk.Menu(self.root, **kw)
        m.add_command(label=_("New folder"), command=lambda: self.desk_new(True))
        m.add_command(label=_("New text file"), command=lambda: self.desk_new(False))
        m.add_command(label=_("Bring files from my computer here…"), command=lambda: self.import_files(HOME + "/Desktop"))
        m.add_separator()
        m.add_command(label=_("Open terminal"), command=self.open_default_terminal)
        m.add_command(label="Fox Store", command=lambda: self.launch("store"))
        m.add_separator()
        sub = tk.Menu(m, **kw)
        for name, (c1, c2) in WALLPAPERS.items():
            sub.add_command(label=_(name), command=lambda a=c1, b=c2: self.set_wallpaper(a, b))
        m.add_cascade(label=_("Wallpaper"), menu=sub)
        st = tk.Menu(m, **kw)
        cur_style = self.settings.get("icon_style", "plain")
        for key, name in ICON_STYLES:
            st.add_command(label=("●  " if key == cur_style else "○  ") + _(name),
                           command=lambda k=key: self.set_icon_style(k))
        m.add_cascade(label=_("Icon style"), menu=st)
        m.add_command(label=_("Change the look of all icons…"), command=lambda: IconEditor(self, None))
        m.add_command(label=_("Arrange icons"), command=self.arrange_icons)
        m.add_command(label=_("Personalize…"), command=lambda: self.launch("settings", page="personal"))
        m.add_command(label=_("Refresh"), command=self.draw_desktop)
        m.tk_popup(e.x_root, e.y_root)

    def desk_new(self, folder):
        name = self.ask_text(_("Name:"), _("New folder") if folder else "new.txt")
        if not name:
            return
        p = HOME + "/Desktop/" + name.replace("/", "_")
        try:
            self.vfs.mkdir(p) if folder else self.vfs.write(p, "")
        except Exception as ex:  # noqa
            messagebox.showerror(_("Error"), err_text(ex), parent=self.root)
        self.save()
        self.fs_changed()

    # ---------- windows ----------
    def register(self, win):
        self.windows.append(win)
        self.focus_window(win)

    def unregister(self, win):
        if win in self.windows:
            self.windows.remove(win)
        if self.active is win:
            self.active = None
            visible = [w for w in self.windows if not w.minimized]
            if visible:
                self.focus_window(visible[-1])
        self.refresh_taskbar()

    def focus_window(self, win):
        win.lift()
        if self.start_open:
            self.start_menu.lift()
        if self.active is not win:
            self.active = win
            for w in self.windows:
                w.config(highlightbackground=self.theme["accent"] if w is win else self.theme["hover"])
            self.refresh_taskbar()

    def refresh_taskbar(self):
        t = self.theme
        for w in self.task_area.winfo_children():
            w.destroy()
        for win in self.windows:
            active = win is self.active and not win.minimized
            bg = t["hover"] if active else t["taskbar"]
            f = tk.Frame(self.task_area, bg=bg)
            f.pack(side="left", fill="y", padx=2, pady=4)
            title = win.title if len(win.title) <= 18 else win.title[:17] + "…"
            lbl = tk.Label(f, text=f" {win.icon} {title} ", bg=bg, fg=t["muted"] if win.minimized else t["fg"],
                           font=("Segoe UI", 9), cursor="hand2")
            lbl.pack(fill="both", expand=True)
            tk.Frame(f, bg=t["accent"] if active else bg, height=2).pack(fill="x", side="bottom")
            lbl.bind("<ButtonRelease-1>", lambda e, w=win: self.taskbar_click(w))

        for wid, title in self.ext_windows:
            f = tk.Frame(self.task_area, bg=t["taskbar"])
            f.pack(side="left", fill="y", padx=2, pady=4)
            short = title if len(title) <= 18 else title[:17] + "…"
            lbl = tk.Label(f, text=f" ↗ {short} ", bg=t["taskbar"], fg=t["fg"], font=("Segoe UI", 9), cursor="hand2")
            lbl.pack(fill="both", expand=True)
            lbl.bind("<ButtonRelease-1>", lambda e, w=wid: sh(["wmctrl", "-i", "-a", w], timeout=5))
            lbl.bind("<Button-3>", lambda e, w=wid, n=title: self.ext_menu(e, w, n))

    def ext_menu(self, e, wid, title):
        t = self.theme
        m = tk.Menu(self.root, tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"],
                    activeforeground="white", font=UI_FONT)
        m.add_command(label=_("Show"), command=lambda: sh(["wmctrl", "-i", "-a", wid], timeout=5))
        m.add_command(label=_("Close"), command=lambda: sh(["wmctrl", "-i", "-c", wid], timeout=5))
        m.tk_popup(e.x_root, e.y_root)

    def poll_ext_windows(self):
        """List the windows of real programs (Firefox, games...) so they appear in the taskbar."""
        def job():
            code, out = sh(["wmctrl", "-lx"], timeout=5)
            wins = []
            for line in out.splitlines() if code == 0 else []:
                parts = line.split(None, 4)
                if len(parts) < 5:
                    continue
                wid, _desk, cls, _host, title = parts
                if "bluefox" in cls.lower() or title.startswith(("BlueFoxDesktop", "Blue Fox")) or not title.strip():
                    continue
                wins.append((wid, title.strip()))
            return wins

        def done(ok, res):
            if ok and res != self.ext_windows:
                self.ext_windows = res
                try:
                    self.refresh_taskbar()
                except tk.TclError:
                    pass
            self.root.after(2000, self.poll_ext_windows)
        self.run_async(job, done)

    def battery_loop(self):
        try:
            bats = [p for p in os.listdir("/sys/class/power_supply") if p.startswith("BAT")]
        except OSError:
            bats = []
        if bats:
            base = "/sys/class/power_supply/" + bats[0]
            try:
                cap = int(open(base + "/capacity").read().strip())
                status = open(base + "/status").read().strip()
                plug = "⚡" if status in ("Charging", "Full") else ""
                col = "#ff6b6b" if cap <= 15 and not plug else self.theme["muted"]
                if self.bat_label.winfo_exists():
                    self.bat_label.config(text=f"▮ {cap}%{plug}", fg=col)
            except (OSError, ValueError, tk.TclError):
                pass
        self.root.after(30000, self.battery_loop)

    def taskbar_click(self, win):
        if win.minimized:
            win.restore()
        elif win is self.active:
            win.minimize()
        else:
            self.focus_window(win)

    # ---------- look & language ----------
    def set_wallpaper(self, c1, c2):
        self.settings.update(wall1=c1, wall2=c2, wall_image="")
        self.save()
        self.draw_desktop()

    def set_wall_image(self, path):
        if path:
            try:
                tk.PhotoImage(data=self.vfs.get(path)["b64"])
            except (tk.TclError, KeyError, TypeError):
                messagebox.showerror(_("Wallpaper"), _("Only PNG and GIF pictures can be used as wallpaper."),
                                     parent=self.root)
                return
        self.settings["wall_image"] = path
        self._wall_cache = (None, None)
        self.save()
        self.draw_desktop()

    def set_theme(self, name, page=None):
        self.settings["theme"] = name
        self.save()
        self.rebuild(reopen_settings=page)

    def set_language(self, code, page=None):
        self.settings["lang"] = code
        LANG["code"] = code
        self.save()
        self.rebuild(reopen_settings=page)

    def reopen_settings(self, page):
        for w in [w for w in self.windows if w.app_key == "settings"]:
            w.close()
        self.launch("settings", page=page)

    def rebuild(self, reopen_settings=None):
        """Rebuild the desktop (new theme / language) and reopen the open apps."""
        for w in list(self.windows):
            if w.on_close and w.on_close() is False:
                return
        reopen = []
        for w in list(self.windows):
            if w.app_key and w.app_key not in reopen and w.app_key != "settings":
                reopen.append(w.app_key)
            w.on_close = None
            w.destroy()
        self.windows.clear()
        self.active = None
        self.fs_listeners.clear()
        self.store_listeners.clear()
        self.taskbar.destroy()
        self.desktop.destroy()
        self.start_open = False
        self._wall_cache = (None, None)
        self.build()
        self.root.update_idletasks()
        for key in reopen:
            if self.app_available(key) and key not in ("firefox", "brave"):
                self.launch(key)
        if reopen_settings:
            self.launch("settings", page=reopen_settings)

    # ---------- clock & internet ----------
    def tick_clock(self):
        if not self.clock.winfo_exists():
            return
        self.clock.config(text=datetime.datetime.now().strftime("%H:%M:%S\n%d/%m/%Y"))
        self.clock.after(1000, self.tick_clock)

    def show_net(self):
        if not self.net_label.winfo_exists():
            return
        if not self.settings.get("internet", True):
            self.net_label.config(text="○ " + _("Offline"), fg=self.theme["muted"])
        elif self.online is None:
            self.net_label.config(text="◌ " + _("Internet…"), fg=self.theme["muted"])
        elif self.online:
            self.net_label.config(text="● " + _("Online"), fg="#4caf50")
        else:
            self.net_label.config(text="● " + _("No internet"), fg="#ff6b6b")

    def check_online(self):
        if not self.settings.get("internet", True):
            self.online = False
            self.show_net()
            return

        def done(ok, res):
            self.online = bool(ok and res)
            try:
                self.show_net()
            except tk.TclError:
                pass
        self.run_async(online_check, done)

    def check_online_loop(self):
        self.check_online()
        self.root.after(60000, self.check_online_loop)

    def toast(self, msg):
        t = self.theme
        try:
            f = tk.Label(self.desktop, text=f"  {msg}  ", bg=t["panel"], fg=t["fg"], font=UI_FONT, highlightthickness=1,
                         highlightbackground=t["accent"], padx=10, pady=10)
            f.place(relx=1.0, rely=1.0, x=-16, y=-16, anchor="se")
            f.after(2800, f.destroy)
        except tk.TclError:
            pass

    # ---------- start, login, power ----------
    def overlay(self, bg="#000000"):
        f = tk.Frame(self.root, bg=bg)
        f.place(x=0, y=0, relwidth=1, relheight=1)
        f.lift()
        return f

    def boot_screen(self, then=None):
        f = self.overlay("#020814")
        tk.Label(f, text="Blue Fox", bg="#020814", fg="#5ea8ff", font=("Segoe UI", 46, "bold")).place(
            relx=0.5, rely=0.40, anchor="center")
        msg = tk.Label(f, bg="#020814", fg="#7f9bb5", font=MONO)
        msg.place(relx=0.5, rely=0.52, anchor="center")
        bar = tk.Canvas(f, width=300, height=6, bg="#0f1d33", highlightthickness=0)
        bar.place(relx=0.5, rely=0.58, anchor="center")
        steps = [_("Starting the core..."), _("Loading files..."), _("Starting services..."),
                 _("Loading the desktop..."), _("Ready!")]

        def step(i=0):
            if i > 20:
                f.destroy()
                if then:
                    then()
                return
            msg.config(text=steps[min(i // 5, len(steps) - 1)])
            bar.delete("all")
            bar.create_rectangle(0, 0, 300 * i / 20, 6, fill="#5ea8ff", outline="")
            self.root.after(65, step, i + 1)
        step()

    def login_screen(self, locked=False):
        self.hide_start()
        s = self.settings
        bg = mix(s["wall1"], "#000000", 0.35)
        f = self.overlay(bg)
        clock = tk.Label(f, bg=bg, fg="white", font=("Segoe UI", 60, "bold"))
        clock.place(relx=0.5, rely=0.26, anchor="center")
        date = tk.Label(f, bg=bg, fg="#dfe9ff", font=("Segoe UI", 15))
        date.place(relx=0.5, rely=0.37, anchor="center")
        tk.Label(f, text="●", bg=bg, fg="#5ea8ff", font=("Segoe UI", 40)).place(relx=0.5, rely=0.50, anchor="center")
        tk.Label(f, text=s["username"], bg=bg, fg="white", font=("Segoe UI", 16, "bold")).place(
            relx=0.5, rely=0.57, anchor="center")
        var = tk.StringVar()
        ent = tk.Entry(f, textvariable=var, show="●", font=("Segoe UI", 13), justify="center", relief="flat")
        ent.place(relx=0.5, rely=0.64, anchor="center", width=260, height=36)
        hint = tk.Label(f, text=_("Type your password and press Enter"), bg=bg, fg="#cfd8ea", font=UI_FONT)
        hint.place(relx=0.5, rely=0.70, anchor="center")
        forgot = tk.Label(f, text=_("Forgot your password?"), bg=bg, fg="#8fb8ff", font=("Segoe UI", 9, "underline"),
                          cursor="hand2")
        forgot.place(relx=0.5, rely=0.75, anchor="center")
        tk.Label(f, text=f"{icon('power')}  " + _("Shut down"), bg=bg, fg="#cfd8ea", font=UI_FONT, cursor="hand2").place(
            relx=0.98, rely=0.97, anchor="se")
        f.winfo_children()[-1].bind("<Button-1>", lambda e: self.power("poweroff") if SESSION else self.root.destroy())

        def tick():
            if f.winfo_exists():
                now = datetime.datetime.now()
                clock.config(text=now.strftime("%H:%M"))
                date.config(text=now.strftime("%d/%m/%Y"))
                f.after(1000, tick)

        def unlock(e=None):
            if var.get() == s["password"]:
                f.destroy()
                if not locked:
                    self.toast(_("Welcome back, {u}!", u=s["username"]))
            else:
                var.set("")
                hint.config(text=_("Wrong password, try again"), fg="#ff8080")

        def forgot_pw(e=None):
            if messagebox.askyesno(_("Forgot your password?"),
                                   _("The password cannot be shown, for safety.\n\nThe only way in is to reset Blue "
                                     "Fox: all Blue Fox files and settings will be erased (your computer's own files "
                                     "are not touched).\n\nReset Blue Fox?"), parent=self.root):
                f.destroy()
                self.factory_reset(ask=False)
        ent.bind("<Return>", unlock)
        forgot.bind("<Button-1>", forgot_pw)
        f.bind("<Button-1>", lambda e: ent.focus_set())
        tick()
        f.after(100, ent.focus_set)

    def lock_screen(self):
        self.login_screen(locked=True)

    def factory_reset(self, ask=True):
        if ask and not messagebox.askyesno(_("Reset Blue Fox"), _("Erase ALL Blue Fox files and settings and "
                                                                  "start the setup again?"), parent=self.root):
            return
        for w in list(self.windows):
            w.on_close = None
            w.close()
        try:
            os.remove(DATA_FILE)
        except OSError:
            pass
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        LANG["code"] = "en"
        self.vfs = VFS()
        self.rebuild()
        SetupWizard(self)

    def power(self, action):
        """action = 'poweroff' or 'reboot' - only used when Blue Fox is the operating system."""
        self.save()
        f = self.overlay("#020814")
        tk.Label(f, text=_("Shutting down...") if action == "poweroff" else _("Restarting..."), bg="#020814",
                 fg="white", font=("Segoe UI", 20)).place(relx=0.5, rely=0.5, anchor="center")
        self.root.update()
        for cmd in (["systemctl", action], ["sudo", "-n", "systemctl", action], ["loginctl", action]):
            code, _out = sh(cmd, timeout=15)
            if code == 0:
                return
        f.destroy()
        messagebox.showerror("Blue Fox", _("The computer could not be turned off from here."), parent=self.root)

    def restart(self):
        if SESSION:
            if messagebox.askyesno(_("Restart"), _("Restart the computer?"), parent=self.root):
                for w in list(self.windows):
                    if w.on_close and w.on_close() is False:
                        return
                self.power("reboot")
            return
        self.save()
        for w in list(self.windows):
            w.on_close = None
            w.close()
        self.boot_time = time.time()
        self.boot_screen(then=self.login_screen)

    def shutdown(self):
        if not messagebox.askyesno(_("Shut down"), _("Shut down Blue Fox?"), parent=self.root):
            return
        for w in list(self.windows):
            if w.on_close and w.on_close() is False:
                return
        if SESSION:
            self.power("poweroff")
            return
        self.save()
        f = self.overlay("#020814")
        tk.Label(f, text=_("Shutting down..."), bg="#020814", fg="white", font=("Segoe UI", 20)).place(
            relx=0.5, rely=0.5, anchor="center")
        self.root.after(900, self.root.destroy)


# ════════════════════════════════════════════════════════════════════
#  ICON EDITOR (right-click an icon → Change icon…)
# ════════════════════════════════════════════════════════════════════
ICON_LOOK = dict(shape="none", bg="#2f7de1", fg="#ffffff", symbol="", image="")
APP_COLORS = {
    "files": "#f9a825", "web": "#1e88e5", "store": "#8e24aa", "notepad": "#5c6bc0", "settings": "#546e7a",
    "calc": "#00897b", "calendar": "#e53935", "taskmgr": "#43a047", "about": "#3949ab", "prompt": "#37474f",
    "bash": "#2e7d32", "foxcode": "#ff6f00", "snake": "#7cb342", "mines": "#6d4c41", "2048": "#f57c00",
    "ttt": "#d81b60", "pong": "#00acc1", "paint": "#ec407a", "python": "#3776ab", "turtle": "#009688",
    "firefox": "#ff7139", "brave": "#fb542b", "programs": "#5e35b1", "folder": "#f9a825", "file": "#78909c", "image": "#26a69a",
}
ICON_STYLES = [("plain", "Plain"), ("colorful", "Colourful"), ("bubbles", "Bubbles"), ("neon", "Neon")]


def style_look(style, color):
    """The look an icon gets from an icon style, given the app's own colour."""
    if style == "colorful":
        return dict(shape="rounded", bg=color, fg="#ffffff")
    if style == "bubbles":
        return dict(shape="circle", bg=color, fg="#ffffff")
    if style == "neon":
        return dict(shape="none", fg=mix(color, "#ffffff", 0.45))
    return {}


ICON_SHAPES = [("none", "No shape"), ("circle", "Circle"), ("square", "Square"), ("rounded", "Rounded")]
ICON_COLORS = ["#2f7de1", "#0b3d91", "#00b4d8", "#2e7d32", "#7cb342", "#f9a825", "#ff6f00", "#e53935",
               "#d81b60", "#8e24aa", "#5d4037", "#37474f", "#000000", "#ffffff"]
ICON_SYMBOLS = ["★", "☆", "♥", "♦", "♣", "♠", "☀", "☁", "☂", "☾", "❄", "✿", "♫", "♪", "✉", "✎", "✂", "✈",
                "⚑", "⌂", "▲", "●", "■", "◆", "✔", "✚", "∞", "Ω", "π", "∑", "♛", "♞", "☺", "☼", "▶", "◉",
                ">_", "$_", "{ }", "</>", "#", "@", "?", "!", "A", "B", "C", "1", "2", "3"]
ICON_EMOJI = ["🦊", "🎮", "🎵", "📷", "🚀", "🔥", "💎", "🌙", "⭐", "🐉", "🍕", "⚽", "🏆", "💡", "🎯", "🧩",
              "🐱", "🐶", "🌍", "❤️", "🎨", "📚", "🛡️", "⚡"]


def rounded_pts(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


class IconEditor:
    """iid = one icon ("app:files", "file:/home/user/Desktop/x.txt"); None = the look of ALL icons."""

    def __init__(self, osys, iid=None):
        self.os = osys
        self.iid = iid
        t = self.t = osys.theme
        self.base = osys.icon_look(None)            # look of all icons
        self.look = osys.icon_look(iid) if iid else dict(self.base)
        info = osys.item_info(iid) if iid else ("Blue Fox", icon("files"), None)
        if not info:
            return
        self.name, self.default_sym = info[0], info[1]
        title = _("Change icon") + f" — {self.name}" if iid else _("Look of all icons")
        osys.launching = "iconeditor"
        try:
            self.win = Window(osys, title, "settings", 600, 600 if iid else 560, resizable=False)
        finally:
            osys.launching = None
        body = tk.Frame(self.win.body, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=8)

        if not iid:
            self.label(body, _("Ready styles"))
            row = tk.Frame(body, bg=t["bg"])
            row.pack(anchor="w", pady=(0, 6))
            for key, name in ICON_STYLES:
                cell = tk.Frame(row, bg=t["panel"], cursor="hand2")
                cell.pack(side="left", padx=3)
                c = tk.Canvas(cell, width=124, height=46, bg=self.os.settings["wall1"], highlightthickness=0, cursor="hand2")
                c.pack()
                for n, app in enumerate(("files", "web", "store", "snake")):
                    osys.draw_tile(c, 18 + n * 30, 23, dict(ICON_LOOK, **style_look(key, APP_COLORS[app])),
                                   icon(APPS[app]["icon"]), 26, ())
                lab = tk.Label(cell, text=_(name), bg=t["panel"], fg=t["fg"], font=("Segoe UI", 9))
                lab.pack(fill="x")
                for w in (cell, c, lab):
                    w.bind("<Button-1>", lambda e, k=key: (self.os.set_icon_style(k), self.win.close()))
            tk.Label(body, text=_("…or make your own look for all icons:"), bg=t["bg"], fg=t["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w")
        top = tk.Frame(body, bg=t["bg"])
        top.pack(fill="x")
        self.prev = tk.Canvas(top, width=150, height=130, highlightthickness=0, bg=self.os.settings["wall1"])
        self.prev.pack(side="left", padx=(0, 14))
        side = tk.Frame(top, bg=t["bg"])
        side.pack(side="left", fill="both", expand=True)
        self.label(side, _("Shape"))
        row = tk.Frame(side, bg=t["bg"])
        row.pack(anchor="w")
        self.shape_btns = {}
        for key, name in ICON_SHAPES:
            b = flat_button(row, _(name), lambda k=key: self.set("shape", k), t, padx=8, pady=4)
            b.pack(side="left", padx=2, pady=2)
            self.shape_btns[key] = b
        self.label(side, _("Shape colour"))
        self.swatches(side, "bg")
        self.label(side, _("Symbol colour"))
        self.swatches(side, "fg")

        if iid:
            self.label(body, _("Symbol"))
            row = tk.Frame(body, bg=t["bg"])
            row.pack(anchor="w", fill="x")
            self.sym_var = tk.StringVar(value=self.look.get("symbol", ""))
            ent = entry(row, t, self.sym_var, width=8, font=("Segoe UI", 14))
            ent.pack(side="left", ipady=2)
            self.sym_var.trace_add("write", lambda *a: self.set("symbol", self.sym_var.get()[:3], redraw_var=False))
            tk.Label(row, text=_("type up to 3 letters or pick one below"), bg=t["bg"], fg=t["muted"],
                     font=("Segoe UI", 9)).pack(side="left", padx=8)
            grid = tk.Frame(body, bg=t["bg"])
            grid.pack(anchor="w", pady=2)
            symbols = ICON_SYMBOLS + (ICON_EMOJI if USE_EMOJI else [])
            for i, sym in enumerate(symbols):
                b = flat_button(grid, sym, lambda s=sym: self.sym_var.set(s), t, width=3, font=("Segoe UI", 12))
                b.grid(row=i // 16, column=i % 16, padx=1, pady=1)
            self.label(body, _("Picture"))
            row = tk.Frame(body, bg=t["bg"])
            row.pack(anchor="w")
            self.pic_label = tk.Label(row, bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9))
            self.pic_label.pack(side="left", padx=(0, 8))
            flat_button(row, _("Choose picture…"), self.choose_pic, t, padx=8, pady=3).pack(side="left", padx=2)
            flat_button(row, _("⇩ From my computer…"), self.import_pic, t, padx=8, pady=3).pack(side="left", padx=2)
            flat_button(row, _("No picture"), lambda: self.set("image", ""), t, padx=8, pady=3).pack(side="left", padx=2)

        foot = tk.Frame(self.win.body, bg=t["panel"])
        foot.pack(fill="x", side="bottom")
        flat_button(foot, _("Save"), self.save, t, bg=t["accent"], fg="white", padx=16, pady=5).pack(side="right", padx=8, pady=6)
        flat_button(foot, _("Cancel"), self.win.close, t, padx=12, pady=5).pack(side="right", pady=6)
        flat_button(foot, _("Original"), self.reset, t, padx=12, pady=5).pack(side="left", padx=8, pady=6)
        self.redraw()

    def label(self, parent, text):
        tk.Label(parent, text=text, bg=self.t["bg"], fg=self.t["accent"], font=UI_BOLD).pack(anchor="w", pady=(8, 2))

    def swatches(self, parent, field):
        row = tk.Frame(parent, bg=self.t["bg"])
        row.pack(anchor="w")
        for c in ICON_COLORS:
            lab = tk.Label(row, bg=c, width=2, relief="ridge", bd=1, cursor="hand2")
            lab.pack(side="left", padx=1)
            lab.bind("<Button-1>", lambda e, c=c: self.set(field, c))
        flat_button(row, _("More…"), lambda: self.pick(field), self.t, padx=6).pack(side="left", padx=4)

    def pick(self, field):
        c = colorchooser.askcolor(self.look.get(field), parent=self.os.root)[1]
        if c:
            self.set(field, c)

    def set(self, field, value, redraw_var=True):
        self.look[field] = value
        if field == "image" and value and self.look.get("shape") == "none":
            pass
        self.redraw()

    def redraw(self):
        cv = self.prev
        cv.delete("all")
        self.os.draw_tile(cv, 75, 50, self.look, self.default_sym, 70, ())
        cv.create_text(75, 108, text=self.name[:16], fill="white", font=("Segoe UI", 9))
        for k, b in self.shape_btns.items():
            sel = self.look.get("shape") == k
            b.config(bg=self.t["accent"] if sel else self.t["panel"], fg="white" if sel else self.t["fg"])
            b.bind("<Leave>", lambda e, b=b, s=sel: b.config(bg=self.t["accent"] if s else self.t["panel"]))
        if hasattr(self, "pic_label"):
            p = self.look.get("image")
            self.pic_label.config(text=(VFS.split(p)[1] if p else _("no picture")))

    def choose_pic(self):
        pics = [p for p in self.os.vfs.walk_find(HOME, ".") if p.lower().endswith((".png", ".gif"))]
        if not pics:
            messagebox.showinfo(_("Picture"), _("There are no PNG or GIF pictures in Blue Fox yet. "
                                                "Use \"From my computer\" to bring one in."), parent=self.os.root)
            return
        t = self.t
        m = tk.Menu(self.os.root, tearoff=0, bg=t["panel"], fg=t["fg"], activebackground=t["accent"], font=UI_FONT)
        for p in pics[:40]:
            m.add_command(label=p.replace(HOME, "~"), command=lambda p=p: self.set("image", p))
        x, y = self.os.root.winfo_pointerxy()
        m.tk_popup(x, y)

    def import_pic(self):
        before = set(self.os.vfs.listdir(HOME + "/Pictures"))
        self.os.import_files(HOME + "/Pictures")
        new = [n for n in self.os.vfs.listdir(HOME + "/Pictures") if n not in before and n.lower().endswith((".png", ".gif"))]
        if new:
            self.set("image", HOME + "/Pictures/" + new[0])
        elif set(self.os.vfs.listdir(HOME + "/Pictures")) != before:
            messagebox.showinfo(_("Picture"), _("Only PNG and GIF pictures can be used for icons."), parent=self.os.root)

    def reset(self):
        self.look = dict(self.base) if self.iid else dict(ICON_LOOK)
        if hasattr(self, "sym_var"):
            self.sym_var.set("")
        self.redraw()

    def save(self):
        s = self.os.settings
        if self.iid:
            changed = {k: v for k, v in self.look.items() if self.base.get(k) != v}
            if changed:
                s.setdefault("icons", {})[self.iid] = changed
            else:
                s.setdefault("icons", {}).pop(self.iid, None)
        else:
            s["icon_default"] = {k: self.look[k] for k in ("shape", "bg", "fg")}
        self.os.save()
        self.os.draw_icons()
        self.win.close()
        self.os.toast(_("Icon saved"))


# ════════════════════════════════════════════════════════════════════
#  FIRST-RUN SETUP
# ════════════════════════════════════════════════════════════════════
class SetupWizard:
    def __init__(self, osys):
        self.os = osys
        self.bg = "#04122e"
        self.f = osys.overlay(self.bg)
        self.data = dict(lang=osys.settings.get("lang", "en"), username="", hostname="bluefox", pw="", pw2="",
                         terms={"bash"}, browser="firefox")
        self.card = None
        self.step = 0
        self.render()

    def render(self):
        LANG["code"] = self.data["lang"]
        if self.card:
            self.card.destroy()
        c = self.card = tk.Frame(self.f, bg="#0d1f40", highlightthickness=1, highlightbackground="#2b4f8a")
        c.place(relx=0.5, rely=0.5, anchor="center", width=620, height=500)
        dots = tk.Frame(c, bg="#0d1f40")
        dots.pack(pady=(14, 0))
        for i in range(5):
            tk.Label(dots, text="●", bg="#0d1f40", fg="#5ea8ff" if i <= self.step else "#2b4f8a",
                     font=("Segoe UI", 10)).pack(side="left", padx=3)
        self.inner = tk.Frame(c, bg="#0d1f40")
        self.inner.pack(fill="both", expand=True, padx=34, pady=10)
        self.msg = tk.Label(c, bg="#0d1f40", fg="#ff8080", font=UI_FONT)
        self.msg.pack()
        nav = tk.Frame(c, bg="#0d1f40")
        nav.pack(fill="x", padx=24, pady=14)
        t = THEMES["ocean"]
        if self.step > 0:
            flat_button(nav, "← " + _("Back"), self.back, t, bg="#16305c", fg="white", padx=16, pady=6).pack(side="left")
        flat_button(nav, (_("Install") if self.step == 4 else _("Next")) + " →", self.next, t, bg="#2f7de1",
                    fg="white", padx=18, pady=6).pack(side="right")
        [self.s_lang, self.s_account, self.s_terms, self.s_browser, self.s_ready][self.step]()

    def title(self, text, sub=""):
        tk.Label(self.inner, text=text, bg="#0d1f40", fg="white", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        if sub:
            tk.Label(self.inner, text=sub, bg="#0d1f40", fg="#a9c3e8", font=UI_FONT, wraplength=540,
                     justify="left").pack(anchor="w", pady=(2, 12))

    def choice(self, text, selected, cmd, sub=""):
        b = tk.Frame(self.inner, bg="#2f7de1" if selected else "#16305c", cursor="hand2")
        b.pack(fill="x", pady=4)
        lab = tk.Label(b, text=("●  " if selected else "○  ") + text, bg=b["bg"], fg="white",
                       font=("Segoe UI", 12, "bold"), anchor="w")
        lab.pack(fill="x", padx=12, pady=(8, 0 if sub else 8))
        widgets = [b, lab]
        if sub:
            s = tk.Label(b, text=sub, bg=b["bg"], fg="#d7e6ff", font=("Segoe UI", 9), anchor="w", wraplength=500,
                         justify="left")
            s.pack(fill="x", padx=34, pady=(0, 8))
            widgets.append(s)
        for w in widgets:
            w.bind("<Button-1>", lambda e: cmd())

    # ---------- steps ----------
    def s_lang(self):
        self.title(_("Welcome to Blue Fox"), _("Let's set up your computer. First, choose your language."))
        for code, name in LANGUAGES.items():
            self.choice(name, self.data["lang"] == code, lambda c=code: (self.data.update(lang=c), self.render()))

    def s_account(self):
        self.title(_("Your account"), _("Choose a user name and a password. You will need the password every "
                                        "time Blue Fox starts."))
        grid = tk.Frame(self.inner, bg="#0d1f40")
        grid.pack(anchor="w")
        self.vars = {}
        for r, (key, label, secret) in enumerate((("username", _("User name"), False),
                                                  ("hostname", _("Computer name"), False),
                                                  ("pw", _("Password"), True), ("pw2", _("Password again"), True))):
            tk.Label(grid, text=label, bg="#0d1f40", fg="#d7e6ff", font=UI_FONT).grid(row=r, column=0, sticky="w", pady=6)
            v = tk.StringVar(value=self.data[key])
            e = tk.Entry(grid, textvariable=v, show="●" if secret else "", font=("Segoe UI", 12), relief="flat",
                         bg="#16305c", fg="white", insertbackground="white", width=24)
            e.grid(row=r, column=1, padx=14, ipady=5)
            e.bind("<Return>", lambda ev: self.next())
            if r == 0:
                e.focus_set()
            self.vars[key] = v

    def s_terms(self):
        self.title(_("Terminals"), _("Which terminals do you want? You can pick more than one and change it later "
                                     "in Settings or the Fox Store."))

        def toggle(k):
            self.data["terms"] ^= {k}
            self.render()
        for k in TERMINAL_KEYS:
            desc = next(d for key, _c, d, _s in STORE if key == k)
            self.choice(TERMINAL_NAMES[k], k in self.data["terms"], lambda k=k: toggle(k), _(desc))

    def s_browser(self):
        self.title(_("Browser"), _("Blue Fox Web is always included. Which other browser do you want?"))
        for k in ("firefox", "brave", "none"):
            if k in HOST_BROWSERS:
                found = find_host_browser(k)
                sub = _("✓ found on this computer") if found else \
                    _("Not on this computer yet - Blue Fox will offer the official download page.")
                name = HOST_BROWSERS[k][0]
            else:
                sub, name = "", _("Only Blue Fox Web")
            self.choice(name, self.data["browser"] == k, lambda k=k: (self.data.update(browser=k), self.render()), sub)

    def s_ready(self):
        self.title(_("Ready to install"), _("Check your choices and press Install."))
        d = self.data
        rows = [(_("Language"), LANGUAGES[d["lang"]]), (_("User name"), d["username"]),
                (_("Computer name"), d["hostname"]),
                (_("Terminals"), ", ".join(TERMINAL_NAMES[k] for k in TERMINAL_KEYS if k in d["terms"])),
                (_("Browser"), "Blue Fox Web" + (" + " + HOST_BROWSERS[d["browser"]][0] if d["browser"] in HOST_BROWSERS else "")),
                (_("Games"), _("Snake (more in the Fox Store)"))]
        for k, v in rows:
            r = tk.Frame(self.inner, bg="#0d1f40")
            r.pack(anchor="w", pady=2)
            tk.Label(r, text=k + ":", width=16, anchor="w", bg="#0d1f40", fg="#a9c3e8", font=UI_FONT).pack(side="left")
            tk.Label(r, text=v, bg="#0d1f40", fg="white", font=UI_BOLD).pack(side="left")

    # ---------- navigation ----------
    def back(self):
        self.step -= 1
        self.render()

    def next(self):
        d = self.data
        if self.step == 1:
            for k, v in self.vars.items():
                d[k] = v.get().strip() if k in ("username", "hostname") else v.get()
            d["username"] = d["username"].replace(" ", "_")
            d["hostname"] = d["hostname"].replace(" ", "_") or "bluefox"
            if not d["username"]:
                return self.msg.config(text=_("Please type a user name."))
            if len(d["pw"]) < 4:
                return self.msg.config(text=_("The password needs at least 4 characters."))
            if d["pw"] != d["pw2"]:
                return self.msg.config(text=_("The two passwords are not the same."))
        if self.step == 2 and not d["terms"]:
            return self.msg.config(text=_("Choose at least one terminal."))
        if self.step == 4:
            return self.install()
        self.step += 1
        self.render()

    def install(self):
        self.card.destroy()
        d = self.data
        box = tk.Frame(self.f, bg=self.bg)
        box.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(box, text="Blue Fox", bg=self.bg, fg="#5ea8ff", font=("Segoe UI", 36, "bold")).pack()
        msg = tk.Label(box, bg=self.bg, fg="#cfe3ff", font=UI_FONT)
        msg.pack(pady=10)
        bar = tk.Canvas(box, width=380, height=8, bg="#0f1d33", highlightthickness=0)
        bar.pack()
        items = [TERMINAL_NAMES[k] for k in TERMINAL_KEYS if k in d["terms"]]
        if d["browser"] in HOST_BROWSERS:
            items.append(HOST_BROWSERS[d["browser"]][0])
        jobs = [_("Preparing your files...")] + [_("Installing {a}...", a=a) for a in items + ["Snake", "Paint"]] + \
               [_("Finishing...")]

        def step(i=0):
            if i < len(jobs):
                msg.config(text=jobs[i])
                bar.delete("all")
                bar.create_rectangle(0, 0, 380 * (i + 1) / len(jobs), 8, fill="#5ea8ff", outline="")
                self.f.after(450, step, i + 1)
            else:
                self.finish()
        step()

    def finish(self):
        d, o = self.data, self.os
        s = o.settings
        installed = [k for k in TERMINAL_KEYS if k in d["terms"]] + ["snake", "paint"]
        if d["browser"] in HOST_BROWSERS:
            installed.append(d["browser"])
        s.update(setup_done=True, lang=d["lang"], username=d["username"], hostname=d["hostname"],
                 password=d["pw"], browser=d["browser"], installed=installed,
                 default_terminal=installed[0])
        LANG["code"] = d["lang"]
        o.vfs.write("/etc/hostname", d["hostname"] + "\n")
        o.save()
        self.f.destroy()
        o.rebuild()
        o.toast(_("Welcome, {u}! Blue Fox is ready.", u=d["username"]))


def main():
    if platform.system() == "Windows":
        try:  # sharp text on high resolution screens
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa
            pass
    root = tk.Tk(className="BlueFox")
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ico = os.path.join(base, "bluefox.ico")
    if platform.system() == "Windows" and os.path.exists(ico):
        try:
            root.iconbitmap(default=ico)
        except tk.TclError:
            pass
    OS(root)
    root.mainloop()


# ════════════════════════════════════════════════════════════════════
#  Greek translation  (Settings → Language → Ελληνικά)
# ════════════════════════════════════════════════════════════════════
EL = {
    # errors & general
    "no such file or folder": "δεν υπάρχει τέτοιο αρχείο ή φάκελος", "already exists": "υπάρχει ήδη",
    "is a folder": "είναι φάκελος", "not a folder": "δεν είναι φάκελος", "not allowed": "δεν επιτρέπεται",
    "invalid expression": "μη έγκυρη πράξη", "on": "ενεργό", "off": "ανενεργό",
    "this is a binary file (e.g. a picture) and cannot be shown as text":
        "είναι δυαδικό αρχείο (π.χ. εικόνα) και δεν εμφανίζεται σαν κείμενο",
    "folder is not empty": "ο φάκελος δεν είναι άδειος", "invalid destination": "μη έγκυρος προορισμός",
    "input cancelled": "ακυρώθηκε η εισαγωγή", "cannot append text to a binary file":
        "δεν γίνεται προσθήκη κειμένου σε δυαδικό αρχείο",
    "the internet is turned off in Settings": "το internet είναι κλειστό στις Ρυθμίσεις",
    "file too big (limit 25 MB)": "πολύ μεγάλο αρχείο (όριο 25 MB)",
    "too many files (limit 2000)": "πάρα πολλά αρχεία (όριο 2000)",
    "Error": "Σφάλμα", "App error": "Σφάλμα εφαρμογής", "Name:": "Όνομα:", "Saved": "Αποθηκεύτηκε",
    # app names
    "Files": "Αρχεία", "Notepad": "Σημειωματάριο", "Calculator": "Αριθμομηχανή", "Paint": "Ζωγραφική",
    "Calendar": "Ημερολόγιο", "Task Manager": "Διαχείριση εργασιών", "About Blue Fox": "Σχετικά με το Blue Fox",
    "Snake": "Φιδάκι", "Minesweeper": "Ναρκαλιευτής", "Tic-Tac-Toe": "Τρίλιζα", "Pong": "Πινγκ πονγκ",
    "Web": "Web", "Settings": "Ρυθμίσεις", "Terminal": "Τερματικό",
    # file manager
    "Folder name:": "Όνομα φακέλου:", "New folder": "Νέος φάκελος", "File name:": "Όνομα αρχείου:",
    "+ Folder": "+ Φάκελος", "+ File": "+ Αρχείο", "Rename": "Μετονομασία", "Delete": "Διαγραφή",
    "Terminal here": "Τερματικό εδώ", "⇧ Save to computer": "⇧ Αποθήκευση στον υπολογιστή",
    "⇩ Folder from computer": "⇩ Φάκελος από υπολογιστή", "⇩ Files from computer": "⇩ Αρχεία από υπολογιστή",
    "Quick access": "Γρήγορη πρόσβαση", "Home": "Αρχική", "Desktop": "Επιφάνεια εργασίας",
    "Documents": "Έγγραφα", "Pictures": "Εικόνες", "Music": "Μουσική", "Downloads": "Λήψεις", "Code": "Κώδικας",
    "Root /": "Ρίζα /", "New name:": "Νέο όνομα:", "Delete {p}?": "Να διαγραφεί το {p};",
    "Save to computer": "Αποθήκευση στον υπολογιστή",
    "First select a file or folder in the list.": "Διάλεξε πρώτα ένα αρχείο ή φάκελο από τη λίστα.",
    "No terminal is installed. Get one from the Fox Store.":
        "Δεν υπάρχει τερματικό. Κατέβασε ένα από το Fox Store.",
    "Folder not found:": "Ο φάκελος δεν βρέθηκε:", "{n} items": "{n} στοιχεία",
    # notepad
    "Untitled": "Χωρίς τίτλο", "File path:": "Διαδρομή αρχείου:", "Save as (file path):": "Αποθήκευση ως (διαδρομή):",
    "New": "Νέο", "Open": "Άνοιγμα", "Save": "Αποθήκευση", "Save as": "Αποθήκευση ως",
    "Save your changes?": "Να αποθηκευτούν οι αλλαγές;", "Word wrap": "Αναδίπλωση",
    "Line {l}, Column {c}": "Γραμμή {l}, Στήλη {c}",
    # paint / pictures / misc apps
    "More…": "Άλλο…", "Eraser": "Γόμα", "Clear": "Καθαρισμός", "Size:": "Πάχος:",
    "'{n}' cannot be shown inside Blue Fox (PNG and GIF work).\n\nSave it to your computer instead?":
        "Το «{n}» δεν εμφανίζεται μέσα στο Blue Fox (δουλεύουν PNG και GIF).\n\nΝα αποθηκευτεί στον υπολογιστή σου;",
    "Set as wallpaper": "Ορισμός ως ταπετσαρία",
    "Processes: {n}     Up time: {m}m {s}s": "Διεργασίες: {n}     Χρόνος λειτουργίας: {m}λ {s}δ",
    "End task": "Τερματισμός", "A complete operating system that runs in a window.":
        "Ένα ολόκληρο λειτουργικό σύστημα που τρέχει σε παράθυρο.",
    "Made entirely in Python.": "Φτιαγμένο εξ ολοκλήρου σε Python.", "Version": "Έκδοση",
    # games
    "Score: {s}": "Σκορ: {s}", "Score: {s}    Best: {b}": "Σκορ: {s}    Ρεκόρ: {b}", "New game": "Νέο παιχνίδι",
    "Press Space to play again": "Πάτα Space για νέο παιχνίδι", "Your turn (X)": "Σειρά σου (X)",
    "Boom! You lost.": "Μπουμ! Έχασες.", "You won!": "Κέρδισες!", "Game over!": "Τέλος παιχνιδιού!",
    "The computer won.": "Κέρδισε ο υπολογιστής.", "Draw!": "Ισοπαλία!", "You": "Εσύ", "CPU": "Υπολ.",
    "Mines: {m}   Flags: {f}": "Νάρκες: {m}   Σημαίες: {f}",
    "Left click = open, right click = flag": "Αριστερό κλικ = άνοιγμα, δεξί κλικ = σημαία",
    "Use the arrow keys. Join the numbers to reach 2048!": "Με τα βελάκια ένωσε τους αριθμούς μέχρι το 2048!",
    "Up/Down or W/S": "Πάνω/Κάτω ή W/S",
    # web
    "Start page": "Αρχική σελίδα", "Quick links": "Γρήγοροι σύνδεσμοι", "Offline": "Εκτός σύνδεσης",
    "Type a web address or words to search in the bar above and press Enter.":
        "Γράψε μια διεύθυνση ή λέξεις για αναζήτηση στη μπάρα από πάνω και πάτα Enter.",
    "Blue Fox Web shows the text and links of web pages. For videos and full websites use the Firefox or Brave app.":
        "Το Blue Fox Web δείχνει το κείμενο και τους συνδέσμους των σελίδων. Για βίντεο και πλήρεις σελίδες "
        "χρησιμοποίησε το Firefox ή το Brave.",
    "You are offline": "Είσαι εκτός σύνδεσης", "Loading {u} ...": "Φόρτωση {u} ...",
    "This page could not be opened": "Η σελίδα δεν άνοιξε", "Picture": "Εικόνα", "Download": "Λήψη",
    "This is a file, not a web page.": "Αυτό είναι αρχείο, όχι ιστοσελίδα.", "Saved to {p}": "Αποθηκεύτηκε στο {p}",
    "Save to Downloads": "Αποθήκευση στις Λήψεις", "(This picture type cannot be shown here.)":
        "(Αυτός ο τύπος εικόνας δεν εμφανίζεται εδώ.)", "Open in {b}": "Άνοιγμα στο {b}",
    "The internet is turned off in Settings → Internet.": "Το internet είναι κλειστό στις Ρυθμίσεις → Internet.",
    "{b} is not installed on this computer yet.\n\nOpen the official {b} download page?":
        "Το {b} δεν είναι ακόμα εγκατεστημένο σε αυτόν τον υπολογιστή.\n\nΝα ανοίξει η επίσημη σελίδα λήψης του {b};",
    "Opening {b}…": "Άνοιγμα {b}…",
    # programming
    "Running…": "Εκτέλεση…", "Finished.": "Τέλος.", "Run": "Εκτέλεση", "Examples": "Παραδείγματα",
    "Draw": "Ζωγράφισε", "Speed:": "Ταχύτητα:", "Drawing {n} lines…": "Σχεδιάζω {n} γραμμές…", "Done!": "Έτοιμο!",
    "'[' expected after repeat": "λείπει το '[' μετά το repeat", "missing ']'": "λείπει το ']'",
    "a number is needed after '{w}'": "χρειάζεται αριθμός μετά το '{w}'", "too many steps": "πάρα πολλά βήματα",
    "unknown color '{c}'": "άγνωστο χρώμα '{c}'", "unknown word '{w}'": "άγνωστη λέξη '{w}'",
    "Hello": "Γεια", "Guess the number": "Μάντεψε τον αριθμό", "Times table": "Προπαίδεια",
    "Star": "Αστέρι", "Flower": "Λουλούδι", "Circles": "Κύκλοι", "House": "Σπίτι",
    # store
    "Everything is free. Install as many apps as you like.": "Όλα είναι δωρεάν. Κατέβασε όσες εφαρμογές θέλεις.",
    "Install": "Εγκατάσταση", "Remove": "Αφαίρεση", "Free": "Δωρεάν", "Remove {a}?": "Να αφαιρεθεί το {a};",
    "Installed: {a}": "Εγκαταστάθηκε: {a}", "Removed: {a}": "Αφαιρέθηκε: {a}", "Nothing found.": "Δεν βρέθηκε τίποτα.",
    "{a} is not installed. Install it now?": "Το {a} δεν είναι εγκατεστημένο. Να εγκατασταθεί τώρα;",
    "All": "Όλα", "Terminals": "Τερματικά", "Games": "Παιχνίδια", "Programming": "Προγραμματισμός",
    "Browsers": "Browsers", "Tools": "Εργαλεία",
    "Classic prompt with commands like dir, cls, type, del.": "Κλασικό prompt με εντολές όπως dir, cls, type, del.",
    "Bash style terminal with commands like ls, clear, cat, rm.": "Τερματικό τύπου Bash με εντολές όπως ls, clear, cat, rm.",
    "Blue Fox Code: the same power with our own easy words (look, wipe, show...).":
        "Blue Fox Code: η ίδια δύναμη με δικές μας εύκολες λέξεις (look, wipe, show...).",
    "The classic snake game. Eat, grow, don't hit the walls!": "Το κλασικό φιδάκι. Φάε, μεγάλωσε, μη χτυπήσεις τοίχο!",
    "Find all the safe squares without hitting a mine.": "Βρες όλα τα ασφαλή τετράγωνα χωρίς να πατήσεις νάρκη.",
    "Slide the tiles and join the numbers to reach 2048.": "Σπρώξε τα πλακίδια και ένωσε τους αριθμούς μέχρι το 2048.",
    "Tic-Tac-Toe against the computer.": "Τρίλιζα με τον υπολογιστή.",
    "Table tennis against the computer.": "Πινγκ πονγκ με τον υπολογιστή.",
    "Write and run real Python programs.": "Γράψε και τρέξε αληθινά προγράμματα Python.",
    "Fox Turtle: learn to code by drawing pictures.": "Fox Turtle: μάθε προγραμματισμό ζωγραφίζοντας.",
    "Opens the real Firefox browser of this computer.": "Ανοίγει τον πραγματικό Firefox του υπολογιστή.",
    "Opens the real Brave browser of this computer.": "Ανοίγει τον πραγματικό Brave του υπολογιστή.",
    "Draw pictures with colours and brushes.": "Ζωγράφισε με χρώματα και πινέλα.",
    # settings
    "Personalization": "Εξατομίκευση", "Account": "Λογαριασμός", "Language": "Γλώσσα", "Browser": "Browser",
    "Internet": "Internet", "System": "Σύστημα", "Theme": "Θέμα", "Dark": "Σκοτεινό", "Light": "Φωτεινό",
    "Ocean blue": "Μπλε ωκεανού", "Wallpaper colours": "Χρώματα ταπετσαρίας", "Wallpaper picture": "Εικόνα ταπετσαρίας",
    "Choose my own colours…": "Δικά μου χρώματα…", "Top colour": "Χρώμα πάνω", "Bottom colour": "Χρώμα κάτω",
    "Current picture: {p}": "Τωρινή εικόνα: {p}",
    "No picture. Use a picture you downloaded or brought in from your computer (PNG or GIF).":
        "Καμία εικόνα. Βάλε μια εικόνα που κατέβασες ή έφερες από τον υπολογιστή σου (PNG ή GIF).",
    "Use": "Χρήση", "⇩ Bring a picture from my computer…": "⇩ Φέρε εικόνα από τον υπολογιστή μου…",
    "Remove picture": "Αφαίρεση εικόνας", "Your account": "Ο λογαριασμός σου", "User name": "Όνομα χρήστη",
    "Computer name": "Όνομα υπολογιστή", "Change password": "Αλλαγή κωδικού",
    "You need this password every time Blue Fox starts.": "Τον κωδικό τον χρειάζεσαι κάθε φορά που ανοίγει το Blue Fox.",
    "Current password": "Τωρινός κωδικός", "New password": "Νέος κωδικός", "New password again": "Νέος κωδικός ξανά",
    "The current password is wrong.": "Ο τωρινός κωδικός είναι λάθος.",
    "The new password needs at least 4 characters.": "Ο νέος κωδικός θέλει τουλάχιστον 4 χαρακτήρες.",
    "The new passwords are not the same.": "Οι νέοι κωδικοί δεν είναι ίδιοι.", "Password changed!": "Ο κωδικός άλλαξε!",
    "Choose the language of Blue Fox.": "Διάλεξε τη γλώσσα του Blue Fox.",
    "Choose which terminals you want. You can have one, two or all three.":
        "Διάλεξε ποια τερματικά θέλεις. Μπορείς να έχεις ένα, δύο ή και τα τρία.",
    "Default terminal": "Προεπιλεγμένο τερματικό",
    "Opens with Ctrl+Alt+T and with 'Terminal here' in Files.": "Ανοίγει με Ctrl+Alt+T και με «Τερματικό εδώ» στα Αρχεία.",
    "Blue Fox Web is always included. You can also choose Firefox or Brave. They open as real browsers on this "
    "computer, so they must be installed on it.":
        "Το Blue Fox Web υπάρχει πάντα. Μπορείς να διαλέξεις και Firefox ή Brave. Αυτά ανοίγουν σαν πραγματικοί "
        "browsers του υπολογιστή, οπότε πρέπει να είναι εγκατεστημένα σε αυτόν.",
    "Only Blue Fox Web": "Μόνο Blue Fox Web", "✓ found on this computer": "✓ βρέθηκε στον υπολογιστή",
    "not on this computer": "δεν υπάρχει στον υπολογιστή", "Download {b}": "Λήψη {b}",
    "Allow Blue Fox to use the internet": "Το Blue Fox μπορεί να χρησιμοποιεί το internet",
    "Used by Blue Fox Web, the Fox Store links and the curl / wget / ping commands.":
        "Το χρησιμοποιούν το Blue Fox Web, οι σύνδεσμοι του Fox Store και οι εντολές curl / wget / ping.",
    "Checking the connection…": "Έλεγχος σύνδεσης…", "Off": "Κλειστό",
    "Connected to the internet": "Συνδεδεμένο στο internet", "No internet connection": "Δεν υπάρχει σύνδεση στο internet",
    "Open Blue Fox Web": "Άνοιγμα Blue Fox Web", "Name": "Όνομα", "Engine": "Μηχανή", "Storage used": "Χώρος",
    "Data file": "Αρχείο δεδομένων", "Restart": "Επανεκκίνηση", "Shut down": "Τερματισμός", "Reset": "Επαναφορά",
    "Erases all Blue Fox files and settings and starts the setup again. Your computer's own files are not touched.":
        "Σβήνει όλα τα αρχεία και τις ρυθμίσεις του Blue Fox και ξεκινά ξανά την εγκατάσταση. Τα αρχεία του "
        "υπολογιστή σου δεν πειράζονται.",
    "Reset Blue Fox…": "Επαναφορά Blue Fox…", "Reset Blue Fox": "Επαναφορά Blue Fox",
    "Erase ALL Blue Fox files and settings and start the setup again?":
        "Να σβηστούν ΟΛΑ τα αρχεία και οι ρυθμίσεις του Blue Fox και να ξεκινήσει ξανά η εγκατάσταση;",
    "Blue Fox": "Blue Fox", "Ocean": "Ωκεανός", "Sunset": "Ηλιοβασίλεμα", "Aurora": "Σέλας", "Forest": "Δάσος",
    "Night": "Νύχτα",
    # desktop, taskbar, transfer
    "Apps": "Εφαρμογές", "No app found": "Δεν βρέθηκε εφαρμογή", "New text file": "Νέο αρχείο κειμένου",
    "Bring files from my computer here…": "Φέρε αρχεία από τον υπολογιστή μου εδώ…", "Open terminal": "Άνοιγμα τερματικού",
    "Wallpaper": "Ταπετσαρία", "Personalize…": "Εξατομίκευση…", "Refresh": "Ανανέωση",
    "{n} files arrived in {p}": "Ήρθαν {n} αρχεία στο {p}", "Bring in files": "Εισαγωγή αρχείων",
    "Some files were not copied:": "Κάποια αρχεία δεν αντιγράφηκαν:",
    "Choose files from your computer for Blue Fox": "Διάλεξε αρχεία από τον υπολογιστή σου για το Blue Fox",
    "Choose a folder from your computer for Blue Fox": "Διάλεξε φάκελο από τον υπολογιστή σου για το Blue Fox",
    "Where on your computer should the folder go?": "Πού στον υπολογιστή σου να πάει ο φάκελος;",
    "Save to your computer": "Αποθήκευση στον υπολογιστή σου",
    "Saved to your computer: {p}": "Αποθηκεύτηκε στον υπολογιστή σου: {p}",
    "Only PNG and GIF pictures can be used as wallpaper.": "Για ταπετσαρία μπαίνουν μόνο εικόνες PNG και GIF.",
    "Online": "Συνδεδεμένο", "No internet": "Χωρίς internet", "Internet…": "Internet…",
    # boot, login, setup
    "Starting the core...": "Εκκίνηση πυρήνα...", "Loading files...": "Φόρτωση αρχείων...",
    "Starting services...": "Εκκίνηση υπηρεσιών...", "Loading the desktop...": "Φόρτωση επιφάνειας εργασίας...",
    "Ready!": "Έτοιμο!", "Type your password and press Enter": "Γράψε τον κωδικό σου και πάτα Enter",
    "Forgot your password?": "Ξέχασες τον κωδικό;", "Wrong password, try again": "Λάθος κωδικός, δοκίμασε ξανά",
    "Welcome back, {u}!": "Καλώς ήρθες ξανά, {u}!",
    "The password cannot be shown, for safety.\n\nThe only way in is to reset Blue Fox: all Blue Fox files and "
    "settings will be erased (your computer's own files are not touched).\n\nReset Blue Fox?":
        "Ο κωδικός δεν μπορεί να εμφανιστεί, για ασφάλεια.\n\nΟ μόνος τρόπος είναι επαναφορά του Blue Fox: θα "
        "σβηστούν όλα τα αρχεία και οι ρυθμίσεις του Blue Fox (τα αρχεία του υπολογιστή σου δεν πειράζονται)."
        "\n\nΝα γίνει επαναφορά;",
    "Shut down Blue Fox?": "Τερματισμός του Blue Fox;", "Shutting down...": "Τερματισμός...",
    "Welcome to Blue Fox": "Καλώς ήρθες στο Blue Fox",
    "Let's set up your computer. First, choose your language.": "Ας στήσουμε τον υπολογιστή σου. Πρώτα διάλεξε γλώσσα.",
    "Choose a user name and a password. You will need the password every time Blue Fox starts.":
        "Διάλεξε όνομα χρήστη και κωδικό. Τον κωδικό θα τον χρειάζεσαι κάθε φορά που ανοίγει το Blue Fox.",
    "Password": "Κωδικός", "Password again": "Κωδικός ξανά",
    "Which terminals do you want? You can pick more than one and change it later in Settings or the Fox Store.":
        "Ποια τερματικά θέλεις; Μπορείς να διαλέξεις πάνω από ένα και να το αλλάξεις αργότερα στις Ρυθμίσεις "
        "ή στο Fox Store.",
    "Blue Fox Web is always included. Which other browser do you want?":
        "Το Blue Fox Web υπάρχει πάντα. Ποιον άλλο browser θέλεις;",
    "Not on this computer yet - Blue Fox will offer the official download page.":
        "Δεν υπάρχει ακόμα στον υπολογιστή - το Blue Fox θα σου ανοίξει την επίσημη σελίδα λήψης.",
    "Ready to install": "Έτοιμο για εγκατάσταση", "Check your choices and press Install.":
        "Έλεγξε τις επιλογές σου και πάτα Εγκατάσταση.", "Snake (more in the Fox Store)": "Φιδάκι (περισσότερα στο Fox Store)",
    "Back": "Πίσω", "Next": "Επόμενο", "Please type a user name.": "Γράψε ένα όνομα χρήστη.",
    "The password needs at least 4 characters.": "Ο κωδικός θέλει τουλάχιστον 4 χαρακτήρες.",
    "The two passwords are not the same.": "Οι δύο κωδικοί δεν είναι ίδιοι.",
    "Choose at least one terminal.": "Διάλεξε τουλάχιστον ένα τερματικό.",
    "Preparing your files...": "Προετοιμασία αρχείων...", "Installing {a}...": "Εγκατάσταση {a}...",
    "Finishing...": "Ολοκλήρωση...", "Welcome, {u}! Blue Fox is ready.": "Καλώς ήρθες, {u}! Το Blue Fox είναι έτοιμο.",
    # terminal messages
    "Type 'help' for the list of commands.": "Γράψε 'help' για τη λίστα εντολών.",
    "Our own command language. Type 'help' to learn the words.": "Η δική μας γλώσσα εντολών. Γράψε 'help' για τις λέξεις.",
    "{name} - commands": "{name} - εντολές",
    "Tips: Up/Down = history, Tab = complete, cmd1 && cmd2 runs both":
        "Συμβουλές: Πάνω/Κάτω = ιστορικό, Tab = συμπλήρωση, εντολή1 && εντολή2 τρέχει και τις δύο",
    "usage: {u}": "χρήση: {u}", "syntax error: {e}": "σφάλμα σύνταξης: {e}", "error: {e}": "σφάλμα: {e}",
    "error: missing file name after >": "σφάλμα: λείπει όνομα αρχείου μετά το >",
    "{cmd}: command not found. Type 'help'.": "{cmd}: η εντολή δεν βρέθηκε. Γράψε 'help'.",
    "Installed apps:": "Εγκατεστημένες εφαρμογές:", "More in the Fox Store:": "Περισσότερα στο Fox Store:",
    "no app called '{a}' in the Fox Store": "δεν υπάρχει εφαρμογή '{a}' στο Fox Store",
    "'{a}' is not installed": "το '{a}' δεν είναι εγκατεστημένο",
    "'{a}' is not installed. Try: install {a}": "το '{a}' δεν είναι εγκατεστημένο. Δοκίμασε: install {a}",
    "Opened: {a}": "Άνοιξε: {a}", "  PID  APP": "  PID  ΕΦΑΡΜΟΓΗ", "that is a system process": "είναι διεργασία συστήματος",
    "no process {n}": "δεν υπάρχει διεργασία {n}", "Closed process {n} ({t})": "Έκλεισε η διεργασία {n} ({t})",
    "Connecting to {u} ...": "Σύνδεση με {u} ...", "Downloading {u} ...": "Λήψη {u} ...",
    "Saved {n} ({s}) to {p}": "Αποθηκεύτηκε το {n} ({s}) στο {p}", "Pinging {h} ...": "Ping στο {h} ...",
    "Request timed out.": "Δεν ήρθε απάντηση.", "Reply from {h}: time={ms}ms": "Απάντηση από {h}: χρόνος={ms}ms",
    "{g}/4 replies": "{g}/4 απαντήσεις", "Blue Fox network": "Δίκτυο Blue Fox", "Adapter": "Κάρτα δικτύου",
    "Imported {n} files into {p}": "Ήρθαν {n} αρχεία στο {p}",
    "[admin] Nice try! You are already the boss here.": "[admin] Ωραία προσπάθεια! Εδώ είσαι ήδη το αφεντικό.",
    "Directory of {p}": "Περιεχόμενα του {p}", "File(s)": "Αρχείο(α)", "Dir(s)": "Φάκελος(οι)",
    "you cannot delete that": "αυτό δεν μπορείς να το σβήσεις", "{d} folders, {f} files": "{d} φάκελοι, {f} αρχεία",
    # calendar
    "January": "Ιανουάριος", "February": "Φεβρουάριος", "March": "Μάρτιος", "April": "Απρίλιος", "May": "Μάιος",
    "June": "Ιούνιος", "July": "Ιούλιος", "August": "Αύγουστος", "September": "Σεπτέμβριος", "October": "Οκτώβριος",
    "November": "Νοέμβριος", "December": "Δεκέμβριος",
    "Mo": "Δε", "Tu": "Τρ", "We": "Τε", "Th": "Πε", "Fr": "Πα", "Sa": "Σα", "Su": "Κυ",
    # fortunes
    "The code you write today is someone's legacy tomorrow.": "Ο κώδικας που γράφεις σήμερα θα τον διαβάζει κάποιος αύριο.",
    "If it doesn't work, try turning it off and on again.": "Αν δεν δουλεύει, κλείσ' το και άνοιξέ το ξανά.",
    "There's no place like 127.0.0.1": "Πουθενά δεν είναι σαν το 127.0.0.1",
    "A fox is quick because it never stops learning.": "Η αλεπού είναι γρήγορη γιατί δεν σταματά να μαθαίνει.",
    "There are 10 types of people: those who know binary and those who don't.":
        "Υπάρχουν 10 είδη ανθρώπων: αυτοί που ξέρουν δυαδικό και αυτοί που δεν ξέρουν.",
    "The best operating system is the one you built yourself.": "Το καλύτερο λειτουργικό είναι αυτό που έφτιαξες μόνος σου.",
    # command descriptions (help)
    "show this help": "αυτή η βοήθεια", "list files": "λίστα αρχείων", "show or change the folder": "δείξε ή άλλαξε φάκελο",
    "make a folder": "νέος φάκελος", "show a file  (type nul > file  makes an empty file)":
        "εμφάνιση αρχείου  (type nul > αρχείο  φτιάχνει κενό αρχείο)",
    "show a file": "εμφάνιση αρχείου", "print text (> or >> writes to a file)": "γράψε κείμενο (> ή >> σε αρχείο)",
    "delete files": "διαγραφή αρχείων", "delete a folder": "διαγραφή φακέλου", "move": "μετακίνηση",
    "rename": "μετονομασία", "copy": "αντιγραφή", "show the folder tree": "δέντρο φακέλων",
    "search file names": "αναζήτηση ονομάτων αρχείων", "search inside a file": "αναζήτηση μέσα σε αρχείο",
    "edit a file in Notepad": "επεξεργασία στο Σημειωματάριο", "open an app or a file": "άνοιγμα εφαρμογής ή αρχείου",
    "list the apps": "λίστα εφαρμογών", "install an app from the Fox Store": "εγκατάσταση από το Fox Store",
    "remove an app": "αφαίρεση εφαρμογής", "running apps": "ανοιχτές εφαρμογές", "close an app": "κλείσιμο εφαρμογής",
    "run Python code": "εκτέλεση κώδικα Python", "calculator, e.g. 2*(3+4)": "αριθμομηχανή, π.χ. 2*(3+4)",
    "show a web page as text": "ιστοσελίδα σαν κείμενο", "download a file into Downloads": "λήψη αρχείου στις Λήψεις",
    "test the internet connection": "έλεγχος σύνδεσης internet", "network information": "πληροφορίες δικτύου",
    "bring files in from this computer": "φέρε αρχεία από τον υπολογιστή",
    "save a file out to this computer": "αποθήκευση αρχείου στον υπολογιστή",
    "system information": "πληροφορίες συστήματος", "Blue Fox version": "έκδοση Blue Fox",
    "your user name": "το όνομα χρήστη σου", "computer name": "όνομα υπολογιστή", "date": "ημερομηνία", "time": "ώρα",
    "command history": "ιστορικό εντολών", "change the theme": "αλλαγή θέματος", "change the language": "αλλαγή γλώσσας",
    "clear the screen": "καθαρισμός οθόνης", "close the terminal": "κλείσιμο τερματικού", "lock the screen": "κλείδωμα οθόνης",
    "shut down (/r = restart)": "τερματισμός (/r = επανεκκίνηση)",
    "change folder (.. = up, ~ = home)": "αλλαγή φακέλου (.. = πάνω, ~ = αρχική)",
    "show the current folder": "τρέχων φάκελος", "make an empty file": "νέο κενό αρχείο", "delete": "διαγραφή",
    "delete an empty folder": "διαγραφή άδειου φακέλου", "move or rename": "μετακίνηση ή μετονομασία",
    "first lines of a file": "πρώτες γραμμές αρχείου", "last lines of a file": "τελευταίες γραμμές αρχείου",
    "count lines, words and characters": "μέτρηση γραμμών, λέξεων, χαρακτήρων", "system name": "όνομα συστήματος",
    "date and time": "ημερομηνία και ώρα", "calendar": "ημερολόγιο", "a random saying": "ένα τυχαίο ρητό",
    "run as administrator": "εκτέλεση ως διαχειριστής", "restart Blue Fox": "επανεκκίνηση Blue Fox",
    "shut down Blue Fox": "τερματισμός Blue Fox", "delete (folders too)": "διαγραφή (και φακέλων)",
    "the fox says something": "η αλεπού λέει κάτι",
}


EL.update({
    "Change icon…": "Αλλαγή εικονιδίου…", "Change icon": "Αλλαγή εικονιδίου", "Pin to taskbar": "Καρφίτσωμα στη γραμμή εργασιών",
    "Unpin from taskbar": "Ξεκαρφίτσωμα από τη γραμμή εργασιών", "Remove from desktop": "Αφαίρεση από την επιφάνεια",
    "Add to desktop": "Προσθήκη στην επιφάνεια", "Original icon": "Αρχικό εικονίδιο",
    "Put back in its place": "Επιστροφή στη θέση του", "Change the look of all icons…": "Εμφάνιση όλων των εικονιδίων…",
    "Arrange icons": "Τακτοποίηση εικονιδίων", "Look of all icons": "Εμφάνιση όλων των εικονιδίων", "Shape": "Σχήμα",
    "Shape colour": "Χρώμα σχήματος", "Symbol colour": "Χρώμα συμβόλου", "Symbol": "Σύμβολο",
    "type up to 3 letters or pick one below": "γράψε έως 3 γράμματα ή διάλεξε ένα από κάτω",
    "Choose picture…": "Διάλεξε εικόνα…", "⇩ From my computer…": "⇩ Από τον υπολογιστή μου…", "No picture": "Χωρίς εικόνα",
    "no picture": "καμία εικόνα", "Cancel": "Ακύρωση", "Original": "Αρχικό", "Icon saved": "Το εικονίδιο αποθηκεύτηκε",
    "No shape": "Χωρίς σχήμα", "Circle": "Κύκλος", "Square": "Τετράγωνο", "Rounded": "Στρογγυλεμένο",
    "There are no PNG or GIF pictures in Blue Fox yet. Use \"From my computer\" to bring one in.":
        "Δεν υπάρχουν ακόμα εικόνες PNG ή GIF στο Blue Fox. Πάτα «Από τον υπολογιστή μου» για να φέρεις μία.",
    "Only PNG and GIF pictures can be used for icons.": "Για εικονίδια μπαίνουν μόνο εικόνες PNG και GIF.",
})


EL.update({
    "Icon style": "Στυλ εικονιδίων", "Icon style (all icons)": "Στυλ εικονιδίων (όλα)", "Plain": "Απλό",
    "Colourful": "Πολύχρωμο", "Bubbles": "Φούσκες", "Neon": "Νέον", "Icon style: {s}": "Στυλ εικονιδίων: {s}",
    "Ready styles": "Έτοιμα στυλ", "…or make your own look for all icons:": "…ή φτιάξε δική σου εμφάνιση για όλα:",
})

EL.update({
    "Programs": "Προγράμματα", "Installing…": "Εγκατάσταση…", "Removing…": "Αφαίρεση…",
    "The computer could not be turned off from here.": "Ο υπολογιστής δεν μπόρεσε να κλείσει από εδώ.",
    "'{p}' is not installed on this computer. Get it from the Fox Store (Computer apps).":
        "Το '{p}' δεν είναι εγκατεστημένο. Κατέβασέ το από το Fox Store (Εφαρμογές υπολογιστή).",
    "Running {p} in your real home folder ({h}) ...": "Εκτέλεση {p} στον πραγματικό φάκελό σου ({h}) ...",
    "Looking for Wi-Fi networks…": "Αναζήτηση δικτύων Wi-Fi…", "Connecting to {n}…": "Σύνδεση στο {n}…",
    "Sound and screen": "Ήχος και οθόνη", "Volume": "Ένταση", "Brightness": "Φωτεινότητα",
    "You need the internet to install computer apps. Connect in Settings → Internet.":
        "Για να εγκαταστήσεις εφαρμογές υπολογιστή χρειάζεσαι internet. Συνδέσου από Ρυθμίσεις → Internet.",
    "Show": "Εμφάνιση", "Close": "Κλείσιμο", "Restart the computer?": "Επανεκκίνηση του υπολογιστή;",
    "(finished with code {c})": "(τελείωσε με κωδικό {c})", "Get more": "Περισσότερα", "Password for {n}:": "Κωδικός για το {n}:",
    "Search again": "Ξανά αναζήτηση", "Connected to {n}!": "Συνδέθηκες στο {n}!", "It did not work:": "Δεν πέτυχε:",
    "Restarting...": "Επανεκκίνηση...", "Computer app": "Εφαρμογή υπολογιστή", "Computer apps": "Εφαρμογές υπολογιστή",
    "No Wi-Fi networks found.": "Δεν βρέθηκαν δίκτυα Wi-Fi.", "Connect": "Σύνδεση", "Connected": "Συνδεδεμένο",
    "Could not connect. Check the password.": "Η σύνδεση απέτυχε. Έλεγξε τον κωδικό.",
    "Computer apps (real programs, need internet to install)":
        "Εφαρμογές υπολογιστή (αληθινά προγράμματα, θέλουν internet για εγκατάσταση)",
    "3D kart racing game.": "Αγώνες με καρτ σε 3D.", "Jump-and-run platform game.": "Παιχνίδι πλατφόρμας με άλματα.",
    "Slide down snowy mountains.": "Γλίστρα σε χιονισμένα βουνά.",
    "Build and explore a world made of blocks.": "Χτίσε και εξερεύνησε έναν κόσμο από κύβους.",
    "Shoot and pop the coloured bubbles.": "Πέτα και σκάσε τις χρωματιστές φούσκες.",
    "Guide the penguins to safety.": "Οδήγησε τους πιγκουίνους σε ασφαλές μέρος.",
    "Solitaire and many other card games.": "Πασιέντζα και πολλά άλλα παιχνίδια με κάρτες.",
    "A friendly Python editor for beginners.": "Εύκολος επεξεργαστής Python για αρχάριους.",
    "Code editor for many languages (C, Java, JavaScript...).": "Επεξεργαστής κώδικα για πολλές γλώσσες (C, Java, JavaScript...).",
    "Run JavaScript programs (use: run node file.js).": "Τρέξε προγράμματα JavaScript (γράψε: run node αρχείο.js).",
    "Compile C and C++ programs (use: run gcc).": "Μεταγλώττισε προγράμματα C και C++ (γράψε: run gcc).",
    "Write and run Java programs (use: run java).": "Γράψε και τρέξε προγράμματα Java (γράψε: run java).",
    "Open source web browser.": "Browser ανοιχτού κώδικα.", "Plays videos and music.": "Παίζει βίντεο και μουσική.",
    "Edit photos and pictures.": "Επεξεργασία φωτογραφιών και εικόνων.", "Write documents.": "Γράψε έγγραφα.",
    "run a real program of the computer (e.g. run node -v)": "τρέξε αληθινό πρόγραμμα του υπολογιστή (π.χ. run node -v)",
    "run a real program of the computer (e.g. unleash node -v)": "τρέξε αληθινό πρόγραμμα του υπολογιστή (π.χ. unleash node -v)",
})


if __name__ == "__main__":
    main()

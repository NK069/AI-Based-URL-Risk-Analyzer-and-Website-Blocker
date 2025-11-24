#!/usr/bin/env python3
import sys
from pathlib import Path

HOSTS = Path("/etc/hosts")
START = "# WEBSITE_BLOCKER_START"
END = "# WEBSITE_BLOCKER_END"

def read_hosts():
    text = HOSTS.read_text()
    if START in text and END in text:
        pre, rest = text.split(START,1)
        inner, post = rest.split(END,1)
        return pre, inner.strip().splitlines(), post
    else:
        return text, [], ""

def write_hosts(pre, inner, post):
    content = pre + START + "\n"
    for l in inner:
        content += l + "\n"
    content += END + "\n" + post
    HOSTS.write_text(content)

def list_blocked():
    pre, inner, post = read_hosts()
    for l in inner:
        print(l)

def add_domain(domain):
    pre, inner, post = read_hosts()
    line = f"127.0.0.1\t{domain}"
    if line not in inner:
        inner.append(line)
        write_hosts(pre, inner, post)
    print("Blocked", domain)

def remove_domain(domain):
    pre, inner, post = read_hosts()
    line = f"127.0.0.1\t{domain}"
    inner = [l for l in inner if l.strip() != line]
    write_hosts(pre, inner, post)
    print("Removed", domain)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: list|add|remove domain")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_blocked()
    elif cmd == "add":
        add_domain(sys.argv[2])
    elif cmd == "remove":
        remove_domain(sys.argv[2])

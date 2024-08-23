#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0

import sys
import argparse
import os
import struct
import pickle
from packaging import version

import elftools
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
import elftools.elf.enums

if version.parse(elftools.__version__) < version.parse('0.24'):
    sys.exit("pyelftools is out of date, need version 0.24 or later")

scr = os.path.basename(sys.argv[0])

def parse_args():
    global args

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-k", "--kernel", required=True,
                        help="Input zephyr ELF binary")
    parser.add_argument("-o", "--gperf", required=True,
            help="Output list of ebus subscriber for gperf use")

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print extra debugging information")

    args = parser.parse_args()
    if "VERBOSE" in os.environ:
        args.verbose = 1

class Slot:
    def __init__(self, elf, section):
        symbols = {sym.name: sym.entry.st_value for sym in section.iter_symbols()}
        assert "__ebus_namespace_start" in symbols , "required __ebus_namespace_start symbol"
        assert "__ebus_namespace_end" in symbols , "required __ebus_namespace_end symbol"
        assert "__ebus_subscriber_start" in symbols , "required __ebus_subscriber_start symbol"
        assert "__ebus_subscriber_end" in symbols , "required __ebus_subscriber_end symbol"
                            
        self.elf = elf
        (self.size, self.pointer) = (16, "Q") if "CONFIG_64BIT" in symbols else (8, "I")
        self.slot = (symbols['__ebus_slot_subscriber_start'], symbols['__ebus_slot_subscriber_end'])
        self.namespace = (symbols['__ebus_namespace_start'], symbols['__ebus_namespace_end'])
        self.subscriber = (symbols['__ebus_subscriber_start'], symbols['__ebus_subscriber_end'])

    def make(self, sym):
        (event, namespace, subscriber) = self.symbol_handle_data(sym)
        assert self.namespace[0] <= namespace < self.namespace[1], f"{sym.name} Not a valid ebus namespace"
        assert self.subscriber[0] <= subscriber < self.subscriber[1], f"{sym.name} Not a valid ebus subscriber"
        namespace = int((namespace - self.namespace[0]))
        subscriber = int((subscriber - self.subscriber[0]) / self.size)
        return Subscriber(sym, event, namespace, subscriber)

    def symbol_data(self, sym):
        addr = sym.entry.st_value
        len = sym.entry.st_size
        for section in self.elf.iter_sections():
            start = section['sh_addr']
            end = start + section['sh_size']
            if (start <= addr) and (addr + len) <= end:
                offset = addr - section['sh_addr']
                return bytes(section.data()[offset:offset + len])

    def valid(self, sym):
        return sym.name.startswith("__ebus_slot_subscriber_") and (self.slot[0] <= sym.entry.st_value < self.slot[1])

    def symbol_handle_data(self, sym):
        data = self.symbol_data(sym)
        if data:
            return struct.unpack(f"{'<' if self.elf.little_endian else '>'}{self.pointer}{self.pointer}{self.pointer}", data)

class Subscriber:
    def __init__(self, sym, event, namespace, subscriber):
        self.sym = sym
        self.event = event
        self.namespace = namespace
        self.subscriber = subscriber
        self.ebus = (self.namespace << 16) | event

# -- GPERF generation logic

header = """%compare-lengths
%define lookup-function-name z_ebus_entry_lookup
%readonly-tables
%global-table
%language=ANSI-C
%struct-type
%{
#include <ebus.h>
#include <string.h>
%}
struct ebus_entry;

struct ebus_entry {
    const char *name;
    const uint32_t *subscriber;
};

"""

# Different versions of gperf have different prototypes for the lookup
# function, best to implement the wrapper here. The pointer value itself is
# turned into a string, we told gperf to expect binary strings that are not
# NULL-terminated.
footer = """%%
__ebustext const uint32_t *z_ebus_subscriber_lookup(uintptr_t ebus)
{
    static const uint32_t dummy = { -1 };
    const struct ebus_entry *entry = z_ebus_entry_lookup((const char *)ebus, sizeof(void *));
    if (entry) {
        return entry->subscriber;
    }

    return &dummy;
}
"""

def write_gperf(fp, subscribers):
    sber_tbl = ""
    ebus_tbl = ""
    fp.write(header)
    for ebus, sber in subscribers.items():
        count = 0
        sber_tbl += f"static const uint32_t __ebus_ord_subscriber_{ebus:08X}[] = {{"
        for it in sber:
            sber_tbl += f"{' ' if count % 16 else '\n\t'}{it.subscriber:d},"
            count = count + 1

        sber_tbl += f"\n\t-1\n}};\n\n"
        ebus_tbl += f"\"\\x{ebus&0xff:02X}\\x{(ebus >> 8) & 0xff:02X}\\x{(ebus >> 16)  & 0xff:02X}\\x{(ebus >> 24) & 0xff:02X}\", __ebus_ord_subscriber_{ebus:08X}\n"

    fp.write(sber_tbl)
    fp.write("%%\n")
    fp.write(ebus_tbl)
    fp.write(footer)

def main():
    parse_args()

    assert args.kernel, "--kernel ELF required to extract data"
    elf = ELFFile(open(args.kernel, "rb"))

    subscribers = {}
    want_constants = set(["__ebus_subscriber_start",
                          "__ebus_subscriber_end",
                          "__ebus_namespace_start",
                          "__ebus_namespace_end",
                          "__ebus_slot_subscriber_start",
                          "__ebus_slot_subscriber_end"])

    for section in elf.iter_sections():
        if not isinstance(section, SymbolTableSection):
            continue

        slot = Slot(elf, section)
        for sym in section.iter_symbols():
            if sym.name in want_constants:
                continue
            if sym.entry.st_info.type != 'STT_OBJECT':
                continue

            if not slot.valid(sym):
                    continue

            subscriber = slot.make(sym)
            if not subscriber.ebus in subscribers:
                subscribers[subscriber.ebus] = []
            subscribers[subscriber.ebus].append(subscriber)

    if args.gperf:
        with open(args.gperf, "w") as fp:
            write_gperf(fp, subscribers)
            


if __name__ == "__main__":
    main()

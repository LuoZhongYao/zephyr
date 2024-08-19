zephyr_sources(ebus.c)
zephyr_linker_sources(RODATA ebus-rom.ld)
zephyr_linker_sources(SECTIONS ebus-sections.ld)

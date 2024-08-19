	SECTION_PROLOGUE(.ebus.namespace, 0 (NOLOAD), AT(_end))
	{
		__ebus_namespace_start = .;
		KEEP(*(SORT(.__ebus_slot_namespace*)));
		__ebus_namespace_end = .;
	}

#ifndef LINKER_PASS2
	SECTION_PROLOGUE(.ebus.subscribe, 0, AT(LOADADDR(.ebus.namespace) + SIZEOF(.ebus.namespace)))
	{
		. = ALIGN(4);
		__ebus_slot_subscriber_start = .;
		KEEP(*(SORT(.__ebus_slot_subscriber*)));
		__ebus_slot_subscriber_end = .;
	}
#else
/DISCARD/ :
{
		KEEP(*(SORT(.__ebus_slot_subscriber*)));
}
#endif

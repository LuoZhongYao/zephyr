	. = ALIGN(4);
  __ebus_subscriber_start = .;
  *(SORT(.__ebus_subscriber*));
  __ebus_subscriber_end = .;


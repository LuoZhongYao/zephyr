/*
 * Copyright (c) 2024 LuoZhongYao@gmail.com
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#if !defined(CONFIG_EBUS)

#define EBUS_NAMESPACE_REGISTER(name)
#define EBUS_NAMESPACE_DECLARE(name)
#define EBUS_PUBLISH(_namespace, _ev, ...)
#define EBUS_SUBSCRIBE(_namespace, _ev, _callback, _userdata)

#else /* CONFIG_EBUS */

#include <stdint.h>
#include <toolchain.h>

#define __ebustext __attribute__((__section__(".TEXT.ebus")))

typedef void (*ebus_subscriber_t)(uint32_t ebus, void *userdata, void *appendix);

struct ebus_subscriber {
	void *userdata;
	ebus_subscriber_t subscriber;
};

struct ebus_slot_subscriber {
	uintptr_t ev;
	const uint8_t *namespace;
	const struct ebus_subscriber *subscriber;
} ;

struct ebus_publish {
	void *appendix;
	void (*drop)(struct ebus_publish *publish);
};

extern uint8_t __ebus_namespace_start[];
extern uint8_t __ebus_namespace_end[];
extern const struct ebus_subscriber __ebus_subscriber_start[];
extern const struct ebus_subscriber __ebus_subscriber_end[];
extern int ebus_publish(uint32_t ebus, struct ebus_publish *publish);

#define EBUS_ORIGINAL(_namespace, _ev) (((uint32_t)(&EBUS_NAMESPACE(_namespace)) << 16) | (_ev))

#define EBUS_NAMESPACE(_name) UTIL_CAT(__ebus_namespace_, _name)

#define EBUS_NAMESPACE_REGISTER(_name)                                                             \
	const uint8_t __attribute__((__section__(".__ebus_slot_namespace"))) EBUS_NAMESPACE(_name)

#define EBUS_NAMESPACE_DECLARE(_name) extern const uint8_t EBUS_NAMESPACE(_name)

#define EBUS_PUBLISH(_namespace, _ev, ...)                                                         \
	ebus_publish(EBUS_ORIGINAL(_namespace, _ev), GET_ARG_N(1, ##__VA_ARGS__, NULL))

#define _EBUS_SUBSCRIBE(_namespace, _ev, _subscriber, _userdata, _idx)                             \
	static __attribute__((__section__(".__ebus_subscriber")))                                  \
	const struct ebus_subscriber MACRO_MAP_CAT(UTIL_EXPAND, __ebus_, _namespace, _, _ev, _,    \
						   _idx) = {                                       \
		.userdata = _userdata,                                                             \
		.subscriber = _subscriber,                                                         \
	};                                                                                         \
                                                                                                   \
	static __used __attribute__((__section__(".__ebus_slot_subscriber")))                      \
	const struct ebus_slot_subscriber                                                          \
	MACRO_MAP_CAT(UTIL_EXPAND, __ebus_slot_subscriber_, _namespace, _, _ev, _, _idx) = {       \
		.ev = _ev,                                                                         \
		.namespace = &EBUS_NAMESPACE(_namespace),                                          \
		.subscriber = &MACRO_MAP_CAT(UTIL_EXPAND, __ebus_, _namespace, _, _ev, _, _idx),   \
	}

#define EBUS_SUBSCRIBE(_namespace, _ev, _subscriber, _userdata)                                    \
	_EBUS_SUBSCRIBE(_namespace, _ev, _subscriber, _userdata, __COUNTER__)

#endif /* CONFIG_EBUS */

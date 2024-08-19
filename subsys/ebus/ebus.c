#include <ebus.h>
#include <init.h>
#include <zephyr.h>

struct ebus_item {
	uint32_t ebus;
	struct ebus_publish *publish;
};

K_MSGQ_DEFINE(ebus_msgq, sizeof(struct ebus_item), CONFIG_EBUS_NUM_MSGQ, 4);

int ebus_publish(uint32_t ebus, struct ebus_publish *publish)
{
	struct ebus_item item = {ebus, publish};
	return k_msgq_put(&ebus_msgq, &item, K_NO_WAIT);
}

__ebustext __weak const uint32_t *z_ebus_subscriber_lookup(uintptr_t ebus)
{
	static const uint32_t dummy ={-1};
	return &dummy;
}

static void ebus_issue(void)
{
	struct ebus_item item;

	while (1) {
		void *appendix = NULL;
		int rc = k_msgq_get(&ebus_msgq, &item, K_FOREVER);
		if (rc != 0) {
			continue;
		}
		if (item.publish) {
			appendix = item.publish->appendix;
		}

		for (const uint32_t *subscriber = z_ebus_subscriber_lookup(item.ebus);
		     *subscriber != -1; subscriber++) {
			const struct ebus_subscriber *entry = __ebus_subscriber_start + *subscriber;
			entry->subscriber(item.ebus, entry->userdata, appendix);
			if (!IS_ENABLED(CONFIG_EBUS_NO_YIELD)) {
				k_yield();
			}
		}

		if (item.publish && item.publish->drop) {
			item.publish->drop(item.publish);
		}
	}
}

K_THREAD_DEFINE(ebus_thread, CONFIG_EBUS_THREAD_STACK_SIZE, (k_thread_entry_t)ebus_issue, NULL,
		NULL, NULL, CONFIG_EBUS_THREAD_PRIORITY, 0, 0);

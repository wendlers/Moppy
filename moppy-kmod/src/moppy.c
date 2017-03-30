/*
 * Moppy as a kernel module :-)
 *
 * Author:
 * 	Stefan Wendler (devnull@kaltpost.de)
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/gpio.h>
#include <linux/delay.h>
#include <linux/hrtimer.h>


static struct hrtimer hr_timer;

#define PERIOD					40000		// 25kHZ (40usec)
#define LOW						 	0
#define HIGH					 	1
#define DISABLED			 	0
#define ENABLED 			 	1

#define MAX_TRACKS			7
#define MAX_DRIVE_POS		158			// for 3.5" floppy

struct track_t {
		int pin_step;
		char *label_step;
		int pin_dir;
		char *label_dir;
		int enabled;
		int current_pos;
		int current_state_step;
		int current_state_dir;
		unsigned int current_period;
		unsigned int current_tick;
};

static struct track_t tracks[] = {
	{17, "ST#0", 18, "DI#0", ENABLED,  0, LOW, LOW, 0, 0},
	{27, "ST#1", 22, "DI#1", ENABLED,  0, LOW, LOW, 0, 0},
	{23, "ST#2", 24, "DI#2", ENABLED,  0, LOW, LOW, 0, 0},
	{25, "ST#3",  4, "DI#3", ENABLED,  0, LOW, LOW, 0, 0},
	{-1, "ST#4", -1, "DI#4", DISABLED, 0, LOW, LOW, 0, 0},
	{-1, "ST#5", -1, "DI#5", DISABLED, 0, LOW, LOW, 0, 0},
	{-1, "ST#7", -1, "DI#7", DISABLED, 0, LOW, LOW, 0, 0},
	{-1, "ST#6", -1, "DI#6", DISABLED, 0, LOW, LOW, 0, 0},
};

void update_track(int track)
{
	if(track < 0 || track > MAX_TRACKS || !tracks[track].enabled) {
		return;
	}

	// Switch directions if end has been reached
	if(tracks[track].current_pos >= MAX_DRIVE_POS) {
		tracks[track].current_state_dir = HIGH;
		gpio_set_value(tracks[track].pin_dir, HIGH);
	}
	else if(tracks[track].current_pos <= 0)	{
		tracks[track].current_state_dir = LOW;
		gpio_set_value(tracks[track].pin_dir, LOW);
	}

	// Update currentPosition
	if(tracks[track].current_state_dir == HIGH)	{
		tracks[track].current_pos--;
	}
	else {
		tracks[track].current_pos++;
	}

	// toggle step pin
	gpio_set_value(tracks[track].pin_step, tracks[track].current_state_step);
	tracks[track].current_state_step = ~tracks[track].current_state_step;
}

void reset(void)
{
	int i = 0;
	int j = 0;

	for(i = 0; i <= MAX_DRIVE_POS / 2; i++) {
		for(j = 0; j <= MAX_TRACKS; j++) {
			if(tracks[j].enabled) {
				gpio_set_value(tracks[j].pin_dir, HIGH);
				gpio_set_value(tracks[j].pin_step, HIGH);
				gpio_set_value(tracks[j].pin_step, LOW);
			}
		}
		mdelay(5);
	}

	for(i = 0; i <= MAX_TRACKS; i++) {
		if(tracks[i].enabled) {
				gpio_set_value(tracks[i].pin_dir, LOW);
				tracks[i].current_period = 0;
				tracks[i].current_pos = 0;
				tracks[i].current_state_dir = LOW;
				tracks[i].current_state_step = LOW;
				tracks[i].current_tick = 0;
		}
	}
}

static ssize_t sysfs_command_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
	int pin = 0;
	int track = 0;
	int value = 0;

	if(sscanf(buf, "%d, %d", &pin, &value) == 2) {

		track = (pin - 2) / 2;

		if(pin == 100 && (value == 0 || value > 4)) {
			printk(KERN_INFO "moppy: reset\n");
			reset();
		}
		else if(track >= 0 && track <= MAX_TRACKS) {
			// printk(KERN_INFO "moppy: pin %d, track %d, value %d\n", pin, track, value);
			tracks[track].current_period = value;
		}
		else {
			printk(KERN_ERR "moppy: unable to map pin %d track\n", pin);
		}
	}
	else {
		printk(KERN_ERR "moppy: received invalid coammnd\n");
	}

	return count;
}

static struct kobj_attribute command_attribute = __ATTR(command, 0220, NULL, sysfs_command_store);

/* SYSFS: List of all attributes exported to sysfs */
static struct attribute *attrs[] = {
		&command_attribute.attr,
		NULL,
};

/* SYSFS: Attributes for sysfs in a group */
static struct attribute_group attr_group = {
		.attrs = attrs,
};

/* SYSFS: Kernel object for sysfs */
static struct kobject *moppy_kobj;

/**
 * Timer function called periodically
 */
enum hrtimer_restart tick(struct hrtimer *timer_for_restart)
{
	int i = 0;

	ktime_t currtime;
	ktime_t interval;

	currtime  = ktime_get();
	interval = ktime_set(0, PERIOD);

	hrtimer_forward(timer_for_restart, currtime, interval);

	for(i = 0; i <= MAX_TRACKS; i++) {
		if(tracks[i].current_period > 0) {

			tracks[i].current_tick++;

			if (tracks[i].current_tick >= tracks[i].current_period)
			{
					update_track(i);
					tracks[i].current_tick = 0;
			}
		}
	}

	return HRTIMER_RESTART;
}


/**
 * Module init function
 */
static int __init moppy_init(void)
{
	int i = 0;
	int ret = 0;

	ktime_t interval;

	printk(KERN_INFO "%s\n", __func__);

	/* register sysfs entry */
	moppy_kobj = kobject_create_and_add("moppy", kernel_kobj);

	if(!moppy_kobj) {
		return -ENOMEM;
	}

	ret = sysfs_create_group(moppy_kobj, &attr_group);

	if(ret) {
		kobject_put(moppy_kobj);
		return ret;
	}

	printk(KERN_INFO "moppy: registered command interface: /sys/kernel/moppy/command\n");

	for(i = 0; i <= MAX_TRACKS; i++) {
		if(tracks[i].enabled) {
			ret = gpio_request_one(tracks[i].pin_step, GPIOF_OUT_INIT_LOW, tracks[i].label_step);
			if(!ret) {
				ret = gpio_request_one(tracks[i].pin_dir, GPIOF_OUT_INIT_LOW, tracks[i].label_dir);

				if(!ret) {
					printk(KERN_INFO "moppy: registered GPIOs #%d/#%d (%s/%s)\n",
						tracks[i].pin_step, tracks[i].pin_dir, tracks[i].label_step, tracks[i].label_dir);
				}
			}
			if(ret) {
				printk(KERN_INFO "moppy: failed to registered GPIOs #%d/#%d (%s/%s)\n",
					tracks[i].pin_step, tracks[i].pin_dir, tracks[i].label_step, tracks[i].label_dir);
				tracks[i].enabled = 0;
			}
		}
	}

	reset();

	/* init timer, add timer function */
	interval = ktime_set(0, PERIOD);
	hrtimer_init(&hr_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
	hr_timer.function = &tick;
	hrtimer_start(&hr_timer, interval, HRTIMER_MODE_REL);

	return ret;
}

/**
 * Module exit function
 */
static void __exit moppy_exit(void)
{
	int i = 0;

	printk(KERN_INFO "%s\n", __func__);

	/* remove kobj */
	kobject_put(moppy_kobj);
	hrtimer_cancel(&hr_timer);

	for(i = 0; i <= MAX_TRACKS; i++) {
		if(tracks[i].enabled) {
			gpio_set_value(tracks[i].pin_step, LOW);
			gpio_set_value(tracks[i].pin_dir, LOW);
			gpio_free(tracks[i].pin_step);
			gpio_free(tracks[i].pin_dir);
		}
	}
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Stefan Wendler");
MODULE_DESCRIPTION("Moppy kernel module");

module_init(moppy_init);
module_exit(moppy_exit);

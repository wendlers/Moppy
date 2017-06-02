/*
 * Moppy as a kernel module :-)
 *
 * Author:
 *   Stefan Wendler (devnull@kaltpost.de)
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

#include "midi.h"

static struct hrtimer hr_timer;

#define PERIOD              40000       // 25kHZ (40usec)
#define FREQ_FACT           80          // (PERIOD / 1000) * 2
#define LOW                 0
#define HIGH                1
#define DISABLED            0
#define ENABLED             1

#define MAX_CHANNEL          7
#define MAX_DRIVE_POS       158         // for 3.5" floppy

/**
 * Definition of a single channel.
 */
struct channel_t {
    /* pin used for stepper */
    int pin_step;

    /* label given for stepper pin in GPIO subsytem */
    char *label_step;

    /* pin used for directoin */
    int pin_dir;

    /* label given for direction pin in GPIO subsytem */
    char *label_dir;

    /* Enable (1) or disable (0) this channel */
    int enabled;

    /* current stepper position */
    int pos;

    /* Current stepper pin state (HIGH/LOW) */
    int state_step;

    /* Current direction pin state (HIGH/LOW) */
    int state_dir;

    /* Target period to reach */
    unsigned int period;

    /* Current period */
    unsigned int period_current;
};

/**
 * Register available channels.
 */
static struct channel_t channels[] = {
	{ 2, "ST#0",  3, "DI#0", ENABLED, 0, LOW, LOW, 0, 0},	// green, blue
    {17, "ST#1", 27, "DI#1", ENABLED, 0, LOW, LOW, 0, 0},	// yellow, orange
    {22, "ST#2", 23, "DI#2", ENABLED, 0, LOW, LOW, 0, 0},	// red, brown
    {10, "ST#3",  9, "DI#3", ENABLED, 0, LOW, LOW, 0, 0},   // orange, yellow
    {11, "ST#4",  8, "DI#4", ENABLED, 0, LOW, LOW, 0, 0},	// gray, red
    { 5, "ST#5",  6, "DI#5", ENABLED, 0, LOW, LOW, 0, 0},	// black, white
    {13, "ST#6", 19, "DI#6", ENABLED, 0, LOW, LOW, 0, 0},	// braun, black
    {26, "ST#7", 20, "DI#7", ENABLED, 0, LOW, LOW, 0, 0},	// blue, green
};

/**
 * Update a single channel / floppy.
 */
void update_channel(int channel)
{
    if(channel < 0 || channel > MAX_CHANNEL || !channels[channel].enabled) {
        return;
    }

    // Switch directions if end has been reached
    if(channels[channel].pos >= MAX_DRIVE_POS) {
        gpio_set_value(channels[channel].pin_dir, (channels[channel].state_dir = HIGH));
    } else if(channels[channel].pos <= 0)  {
        gpio_set_value(channels[channel].pin_dir, (channels[channel].state_dir = LOW));
    }

    // Update currentPosition
    channels[channel].pos += channels[channel].state_dir ? -1 : 1;

    // toggle step pin
    gpio_set_value(channels[channel].pin_step, channels[channel].state_step);
    channels[channel].state_step = ~channels[channel].state_step;

    channels[channel].period_current = 0;
}

/**
 * Reset all floppys to default position.
 */
void reset(void)
{
    int i = 0;
    int j = 0;

    for(i = 0; i <= MAX_DRIVE_POS / 2; i++) {
        for(j = 0; j <= MAX_CHANNEL; j++) {
            if(channels[j].enabled) {
                gpio_set_value(channels[j].pin_dir, HIGH);
                gpio_set_value(channels[j].pin_step, HIGH);
                gpio_set_value(channels[j].pin_step, LOW);
            }
        }
        mdelay(5);
    }

    for(i = 0; i <= MAX_CHANNEL; i++) {
        if(channels[i].enabled) {
            gpio_set_value(channels[i].pin_dir, LOW);
            channels[i].period = 0;
            channels[i].pos = 0;
            channels[i].state_dir = LOW;
            channels[i].state_step = LOW;
            channels[i].period_current = 0;
        }
    }
}

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

    for(i = 0; i <= MAX_CHANNEL; i++) {
        if(channels[i].period > 0 && ++channels[i].period_current >= channels[i].period) {
            update_channel(i);
        }
    }

    return HRTIMER_RESTART;
}

/**
 * Handle writes to the sysfs entry 'ticks'.
 *
 * Format is: <channel>, <ticks>
 *
 * E.g. 440Hz / A4 to channel 0 (440Hz = 28 ticks)
 *
 *  echo "0, 28" > /sys/kernel/moppy/ticks
 */
static ssize_t sysfs_ticks_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    int channel = 0;
    int value = 0;

    if(sscanf(buf, "%d, %d", &channel, &value) == 2) {
        if(channel >= 0 && channel <= MAX_CHANNEL) {
            channels[channel].period = value;
        } else {
            printk(KERN_ERR "moppy: invalid channel number %d\n", channel);
        }
    } else {
        printk(KERN_ERR "moppy: received invalid coammnd\n");
    }

    return count;
}
static struct kobj_attribute ticks_attribute = __ATTR(ticks, (S_IWUSR | S_IWGRP), NULL, sysfs_ticks_store);

/**
 * Handle writes to the sysfs entry 'note'.
 *
 * Format is: <channel>, <note>
 *
 * E.g. 69 / A4 to channel 0 (440Hz = 28 ticks)
 *
 *  echo "0, 69" > /sys/kernel/moppy/note
 */
static ssize_t sysfs_note_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    int channel = 0;
    int value = 0;

    if(sscanf(buf, "%d, %d", &channel, &value) == 2) {
        if(channel >= 0 && channel <= MAX_CHANNEL && value >= 0 && value <= 127) {
            channels[channel].period = midi_note_period[value];
        } else {
            printk(KERN_ERR "moppy: invalid channel number %d\n", channel);
        }
    } else {
        printk(KERN_ERR "moppy: received invalid coammnd\n");
    }

    return count;
}
static struct kobj_attribute note_attribute = __ATTR(note, (S_IWUSR | S_IWGRP), NULL, sysfs_note_store);

/**
 * Handle writes to the sysfs entry 'freq'.
 *
 * Format is: <channel>, <freq>
 *
 * E.g. 440Hz / A4 to channel 0
 *
 *  echo "0, 440" > /sys/kernel/moppy/freq
 */
static ssize_t sysfs_freq_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    int channel = 0;
    int value = 0;
    int period = 0;

    if(sscanf(buf, "%d, %d", &channel, &value) == 2) {
        if(channel >= 0 && channel <= MAX_CHANNEL) {
          if(value > 0) {
            period = (1000000 / value) / FREQ_FACT;
          }
          channels[channel].period = (int)(period);
        } else {
            printk(KERN_ERR "moppy: invalid channel number %d\n", channel);
        }
    } else {
        printk(KERN_ERR "moppy: received invalid coammnd\n");
    }

    return count;
}
static struct kobj_attribute freq_attribute = __ATTR(freq, (S_IWUSR | S_IWGRP), NULL, sysfs_freq_store);

/**
 * Handle writes to the sysfs entry 'ctrl'.
 */
static ssize_t sysfs_ctrl_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    if(strncmp(buf, "reset", 5) == 0) {
        printk(KERN_INFO "moppy: reset\n");
        reset();
    }

    return count;
}
static struct kobj_attribute ctrl_attribute = __ATTR(ctrl, (S_IWUSR | S_IWGRP), NULL, sysfs_ctrl_store);

/**
 * Get some basic information about the setup.
 *
 * Returns a single line of the format:
 *
 *	<active_channels>, <freq_fact>
 */
static ssize_t sysfs_info_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf)
{
	int i = 0;
	int active_channels = 0;

	for(i = 0; i <= MAX_CHANNEL; i++) {
			active_channels += channels[i].enabled;
	}

  return sprintf(buf, "%d, %d\n", active_channels, FREQ_FACT);
}
static struct kobj_attribute info_attribute = __ATTR(info, (S_IRUSR | S_IRGRP), sysfs_info_show, NULL);

/**
 *  List of all attributes exported to sysfs
 */
static struct attribute *attrs[] = {
    &ticks_attribute.attr,
    &note_attribute.attr,
    &freq_attribute.attr,
    &ctrl_attribute.attr,
		&info_attribute.attr,
    NULL,
};

/* SYSFS: Attributes for sysfs in a group */
static struct attribute_group attr_group = {
    .attrs = attrs,
};

/* SYSFS: Kernel object for sysfs */
static struct kobject *moppy_kobj;

/**
 * Module init function.
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

    printk(KERN_INFO "moppy: registered command interface: /sys/kernel/moppy/\n");

    for(i = 0; i <= MAX_CHANNEL; i++) {
        if(channels[i].enabled) {
            ret = gpio_request_one(channels[i].pin_step, GPIOF_OUT_INIT_LOW, channels[i].label_step);
            if(!ret) {
                ret = gpio_request_one(channels[i].pin_dir, GPIOF_OUT_INIT_LOW, channels[i].label_dir);

                if(!ret) {
                    printk(KERN_INFO "moppy: registered GPIOs #%d/#%d (%s/%s)\n",
                           channels[i].pin_step, channels[i].pin_dir, channels[i].label_step, channels[i].label_dir);
                }
            }
            if(ret) {
                printk(KERN_INFO "moppy: failed to registered GPIOs #%d/#%d (%s/%s)\n",
                       channels[i].pin_step, channels[i].pin_dir, channels[i].label_step, channels[i].label_dir);
                channels[i].enabled = 0;
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
 * Module exit function.
 */
static void __exit moppy_exit(void)
{
    int i = 0;

    printk(KERN_INFO "%s\n", __func__);

    /* remove kobj */
    kobject_put(moppy_kobj);
    hrtimer_cancel(&hr_timer);

    for(i = 0; i <= MAX_CHANNEL; i++) {
        if(channels[i].enabled) {
            gpio_set_value(channels[i].pin_step, LOW);
            gpio_set_value(channels[i].pin_dir, LOW);
            gpio_free(channels[i].pin_step);
            gpio_free(channels[i].pin_dir);
        }
    }
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Stefan Wendler");
MODULE_DESCRIPTION("Moppy kernel module");

module_init(moppy_init);
module_exit(moppy_exit);

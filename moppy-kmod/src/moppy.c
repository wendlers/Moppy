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

#define PERIOD              40000       // 25kHZ (40usec)
#define FREQ_FACT           12500       // 1000000 / (PERIOD / 1000) * 2
#define LOW                 0
#define HIGH                1
#define DISABLED            0
#define ENABLED             1

#define MAX_TRACKS          7
#define MAX_DRIVE_POS       158         // for 3.5" floppy

/**
 * Definition of a single track.
 */
struct track_t {
    /* pin used for stepper */
    int pin_step;

    /* label given for stepper pin in GPIO subsytem */
    char *label_step;

    /* pin used for directoin */
    int pin_dir;

    /* label given for direction pin in GPIO subsytem */
    char *label_dir;

    /* Enable (1) or disable (0) this track */
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
 * Register available tracks.
 */
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

/**
 * Update a single track / floppy.
 */
void update_track(int track)
{
    if(track < 0 || track > MAX_TRACKS || !tracks[track].enabled) {
        return;
    }

    // Switch directions if end has been reached
    if(tracks[track].pos >= MAX_DRIVE_POS) {
        gpio_set_value(tracks[track].pin_dir, (tracks[track].state_dir = HIGH));
    } else if(tracks[track].pos <= 0)	{
        gpio_set_value(tracks[track].pin_dir, (tracks[track].state_dir = LOW));
    }

    // Update currentPosition
    tracks[track].pos += tracks[track].state_dir ? -1 : 1;

    // toggle step pin
    gpio_set_value(tracks[track].pin_step, tracks[track].state_step);
    tracks[track].state_step = ~tracks[track].state_step;

    tracks[track].period_current = 0;
}

/**
 * Reset all floppys to default position.
 */
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
            tracks[i].period = 0;
            tracks[i].pos = 0;
            tracks[i].state_dir = LOW;
            tracks[i].state_step = LOW;
            tracks[i].period_current = 0;
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

    for(i = 0; i <= MAX_TRACKS; i++) {
        if(tracks[i].period > 0 && ++tracks[i].period_current >= tracks[i].period) {
            update_track(i);
        }
    }

    return HRTIMER_RESTART;
}

/**
 * Handle writes to the sysfs entry 'ticks'.
 *
 * Format is: <track>, <ticks>
 *
 * E.g. 440Hz / A4 to track 0 (440Hz = 28 ticks)
 *
 *  echo "0, 28" > /sys/kernel/moppy/ticks
 */
static ssize_t sysfs_ticks_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    int track = 0;
    int value = 0;

    if(sscanf(buf, "%d, %d", &track, &value) == 2) {
        if(track >= 0 && track <= MAX_TRACKS) {
            tracks[track].period = value;
        } else {
            printk(KERN_ERR "moppy: invalid track number %d\n", track);
        }
    } else {
        printk(KERN_ERR "moppy: received invalid coammnd\n");
    }

    return count;
}
static struct kobj_attribute ticks_attribute = __ATTR(command, S_IWUSR, NULL, sysfs_ticks_store);

/**
 * Handle writes to the sysfs entry 'freq'.
 *
 * Format is: <track>, <freq>
 *
 * E.g. 440Hz / A4 to track 0
 *
 *  echo "0, 440" > /sys/kernel/moppy/freq
 */
static ssize_t sysfs_freq_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    int track = 0;
    int value = 0;

    if(sscanf(buf, "%d, %d", &track, &value) == 2) {
        if(track >= 0 && track <= MAX_TRACKS) {
            tracks[track].period = value > 0 ? FREQ_FACT / value : 0;
        } else {
            printk(KERN_ERR "moppy: invalid track number %d\n", track);
        }
    } else {
        printk(KERN_ERR "moppy: received invalid coammnd\n");
    }

    return count;
}
static struct kobj_attribute freq_attribute = __ATTR(command, S_IWUSR, NULL, sysfs_freq_store);

/**
 * Handle writes to the sysfs entry 'ctrl'.
 */
static ssize_t sysfs_ctrl_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    if(strcmp(buf, "reset") == 0) {
        printk(KERN_INFO "moppy: reset\n");
        reset();
    }

    return count;
}
static struct kobj_attribute ctrl_attribute = __ATTR(command, S_IWUSR, NULL, sysfs_ctrl_store);

/* SYSFS: List of all attributes exported to sysfs */
static struct attribute *attrs[] = {
    &ticks_attribute.attr,
    &freq_attribute.attr,
    &ctrl_attribute.attr,
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
 * Module exit function.
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

// SPDX-License-Identifier: GPL-2.0-only
/*
 *  linux/fs/namespace.c
 *
 * (C) Copyright Al Viro 2000, 2001
 *
 * Based on code from fs/super.c, copyright Linus Torvalds and others.
 * Heavily rewritten.
 */

#include <linux/syscalls.h>
#include <linux/export.h>
#include <linux/capability.h>
#include <linux/mnt_namespace.h>
#include <linux/user_namespace.h>
#include <linux/namei.h>
#include <linux/security.h>
#include <linux/cred.h>
#include <linux/idr.h>
#include <linux/init.h>		/* init_rootfs */
#include <linux/fs_struct.h>	/* get_fs_root et.al. */
#include <linux/fsnotify.h>	/* fsnotify_vfsmount_delete */
#include <linux/file.h>
#include <linux/uaccess.h>
#include <linux/proc_ns.h>
#include <linux/magic.h>
#include <linux/memblock.h>
#include <linux/proc_fs.h>
#include <linux/task_work.h>
#include <linux/sched/task.h>
#include <uapi/linux/mount.h>
#include <linux/fs_context.h>
#include <linux/shmem_fs.h>
#include <linux/mnt_idmapping.h>

#include "pnode.h"
#include "internal.h"

/* Maximum number of mounts in a mount namespace */
static unsigned int sysctl_mount_max __read_mostly = 100000;

static unsigned int m_hash_mask __read_mostly;
static unsigned int m_hash_shift __read_mostly;
static unsigned int mp_hash_mask __read_mostly;
static unsigned int mp_hash_shift __read_mostly;

static __initdata unsigned long mhash_entries;
static int __init set_mhash_entries(char *str)
{
	if (!str)
		return 0;
	mhash_entries = simple_strtoul(str, &str, 0);
	return 1;
}
__setup("mhash_entries=", set_mhash_entries);

static __initdata unsigned long mphash_entries;
static int __init set_mphash_entries(char *str)
{
	if (!str)
		return 0;
	mphash_entries = simple_strtoul(str, &str, 0);
	return 1;
}
__setup("mphash_entries=", set_mphash_entries);

static u64 event;
static DEFINE_IDA(mnt_id_ida);
static DEFINE_IDA(mnt_group_ida);


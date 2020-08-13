#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BiDirectional Sync using rclone"""

from __future__ import unicode_literals  # This sets py2.7 default string literal to unicode from str.  No 'u' required on strings.
from __future__ import print_function    # This redefines print as a function, as in py3.  Forces writing compatible code.


__version__ = "V2.11 200813"                         # Version number and date code


#==========================================================================================================
# Configure rclone, including authentication before using this tool.  rclone must be in the search path.
#
# Chris Nelson, November 2017 - 2020
# Revision and contributions:
#   Hildo G. Jr., e2t, kalemas, and silenceleaf
#
# See README.md for revision history
#
# Known bugs:
#   remove size compare since its not used - NO
#   Add file compares based on hashes - NO
#
#==========================================================================================================

import argparse
import sys
import re
import os.path
import io
import platform
import shutil
import subprocess
from datetime import datetime
import tempfile
import time
import logging
import inspect                                      # For getting the line number for error messages.
import collections                                  # For dictionary sorting.
import hashlib                                      # For checking if the filter file changed and force --first_sync.
import signal                                       # For keyboard interrupt handler


# Configurations and constants
is_Windows = False
is_Linux = False
if sys.platform == "win32":
    is_Windows = True
if "linux" in sys.platform:  # <linux2> on Py2, <linux> on Py3
    is_Linux = True
is_Py27 = False
is_Py3x = False
if sys.version_info[0] == 2 and sys.version_info[1] == 7:
    is_Py27 = True
if sys.version_info[0] == 3:
    is_Py3x = True
is_Windows_Py27 = is_Windows and is_Py27

if is_Windows_Py27:
    import win_subprocess                           # Win Py27 subprocess only supports ASCII in subprocess calls.
    import win32_unicode_argv                       # Win Py27 only supports ASCII on command line.

MAX_DELETE = 50                                     # % deleted allowed, else abort.  Use --force or --max_deletes to override.
CHK_FILE = 'RCLONE_TEST'

RTN_ABORT = 1                                       # Tokens for return codes based on criticality.
RTN_CRITICAL = 2                                    # Aborts allow rerunning.  Criticals block further runs.  See Readme.md.


def bidirSync():

    def print_msg(tag, msg, key=''):
        return "  {:9}{:35} - {}".format(tag, msg, key)

 
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    global path1_list_file, path2_list_file
    list_file_base  = workdir + "LSL_" + (path1_base + path2_base).replace(':','_').replace(r'/','_').replace('\\','_')
            # '/home/<user>/.rclonesyncwd/LSL_<path1_base><path2_base>'
    path1_list_file = list_file_base + '_Path1'
    path2_list_file = list_file_base + '_Path2'

    logging.info("Synching Path1  <{}>  with Path2  <{}>".format(path1_base, path2_base))


    args_string = ''                            # Build call args string for consistency across Linux/Windows/Py27/Py3x
    for arg in sorted(args.__dict__):
        argvalue = getattr(args, arg)
        if type(argvalue) is str and is_Py27:
            argvalue = argvalue.decode("utf-8")
        if type(argvalue) is int:
            argvalue = str(argvalue)
        if type(argvalue) is bool:
            if argvalue is False:
                argvalue = "False"
            else:
                argvalue = "True"
        if type(argvalue) is list:              # --rclone-args case
            rcargs = '=['
            for item in argvalue:
                rcargs += item + ' '
            argvalue = rcargs[:-1] + ']'
        if argvalue is None:
            argvalue = "None"
        args_string += arg + '=' + argvalue + ', '
    logging.info ("Command args: <{}>".format(args_string[:-2]))


    # ***** Handle filters_file, if provided *****
    filters = []
    if filters_file is not None:
        logging.info("Using filters-file  <{}>".format(filters_file))

        if not os.path.exists(filters_file):
            logging.error("Specified filters-file file does not exist:  " + filters_file)
            return RTN_CRITICAL

        filters_fileMD5 = filters_file + "-MD5"

        with io.open(filters_file, 'rb') as ifile:
            if is_Py27:
                current_file_hash = bytes(hashlib.md5(ifile.read()).hexdigest())
            else:
                current_file_hash = bytes(hashlib.md5(ifile.read()).hexdigest(), encoding='utf-8')

        stored_file_hash = ''
        if os.path.exists(filters_fileMD5):
            with io.open(filters_fileMD5, mode="rb") as ifile:
                stored_file_hash = ifile.read()
        elif not first_sync:
            logging.error("MD5 file not found for filters file <{}>.  Must run --first-sync.".format(filters_file))
            return RTN_CRITICAL

        if current_file_hash != stored_file_hash and not first_sync:
            logging.error("Filters-file <{}> has chanaged (MD5 does not match).  Must run --first-sync.".format(filters_file))
            return RTN_CRITICAL

        if first_sync:
            logging.info("Storing filters-file hash to <{}>".format(filters_fileMD5))
            with io.open(filters_fileMD5, 'wb') as ofile:
                ofile.write(current_file_hash)

        filters.append("--filter-from")
        filters.append(filters_file)


    # ***** Set up dry_run and rclone --verbose switches *****
    switches = []
    for _ in range(rc_verbose):
        switches.append("-v")
    if dry_run:
        switches.append("--dry-run")
        if os.path.exists(path2_list_file):          # If dry_run, original LSL files are preserved and lsl's are done to the _DRYRUN files.
            shutil.copy(path2_list_file, path2_list_file + '_DRYRUN')
            path2_list_file  += '_DRYRUN'
        if os.path.exists(path1_list_file):
            shutil.copy(path1_list_file, path1_list_file + '_DRYRUN')
            path1_list_file += '_DRYRUN'
    if args.no_datetime_log:
        switches.extend(['--log-format', '""'])
    # print (switches)


    # ***** rclone call wrapper functions with retries *****
    MAXTRIES=3
    def rclone_lsl(path, ofile, options=None, linenum=0):
        process_args = [rclone, "lsl", path, "--config", rcconfig]
        if options is not None:
            process_args.extend(options)
        if args.rclone_args is not None:
            process_args.extend(args.rclone_args)
        logging.debug("    rclone command:  {}".format(process_args))
        for x in range(MAXTRIES):
            with io.open(ofile, "wt", encoding='utf8') as of:
                if is_Windows_Py27:
                    p = win_subprocess.Popen(process_args, stdout=of, shell=True)
                    out, err = p.communicate()
                    if not err:
                        return(0)
                else:
                    if not subprocess.call(process_args, stdout=of):
                        return 0
                logging.info(print_msg("WARNING", "rclone lsl try {} failed.".format(x+1)))
        logging.error(print_msg("ERROR", "rclone lsl failed.  Specified path invalid?  (Line {})".format(linenum)))
        return 1

    def rclone_cmd(cmd, p1=None, p2=None, options=None, linenum=0):
        process_args = [rclone, cmd, "--config", rcconfig]
        if p1 is not None:
            process_args.append(p1)
        if p2 is not None:
            process_args.append(p2)
        if options is not None:
            process_args.extend(options)
        if args.rclone_args is not None:
            process_args.extend(args.rclone_args)
        logging.debug("    rclone command:  {}".format(process_args))
        for x in range(MAXTRIES):
            try:
                if is_Windows_Py27:
                    # On Windows and Python 2.7, the subprocess module only support ASCII in the process_args
                    # argument.  The win_subprocess mdoule supports extended characters (UTF-8), which is needed 
                    # when file and directory names contain extended characters.  However, win_subprocess 
                    # requires both shell=True and valid output files.  
                    with io.open(workdir + "deleteme.txt", "wt") as of:
                        p = win_subprocess.Popen(process_args, stdout=of, stderr=of, shell=True)
                else:
                    p = subprocess.Popen(process_args)
                p.wait()
                if p.returncode == 0:
                    return 0
            except Exception as e:
                logging.info(print_msg("WARNING", "rclone {} try {} failed.".format(cmd, x+1), p1))
                logging.info("message:  <{}>".format(e))
        logging.error(print_msg("ERROR", "rclone {} failed.  (Line {})".format(cmd, linenum), p1))
        return 1


    # ***** first_sync generate path1 and path2 file lists, and copy any unique path2 files to path1 ***** 
    if first_sync:
        logging.info(">>>>> --first-sync copying any unique Path2 files to Path1")
        if rclone_lsl(path1_base, path1_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        if rclone_lsl(path2_base, path2_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        status, path1_now = load_list(path1_list_file)
        if status:
            logging.error(print_msg("ERROR", "Failed loading Path1 list file <{}>".format(path1_list_file)))
            return RTN_CRITICAL

        status, path2_now  = load_list(path2_list_file)
        if status:
            logging.error(print_msg("ERROR", "Failed loading Path2 list file <{}>".format(path2_list_file)))
            return RTN_CRITICAL

        for key in path2_now:
            if key not in path1_now:
                src  = path2_base + key
                dest = path1_base + key
                logging.info(print_msg("Path2", "  --first-sync copying to Path1", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL

        if rclone_lsl(path1_base, path1_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL


    # ***** Check for existence of prior Path1 and Path2 lsl files *****
    if not os.path.exists(path1_list_file) or not os.path.exists(path2_list_file):
        # On prior critical error abort, the prior LSL files are renamed to _ERROR to lock out further runs
        logging.error("***** Cannot find prior Path1 or Path2 lsl files.")
        return RTN_CRITICAL


    # ***** Check basic access health to the Path1 and Path2 filesystems *****
    if check_access:
        if first_sync:
            logging.info(">>>>> --check-access skipped on --first-sync")
        else:
            logging.info(">>>>> Checking Path1 and Path2 rclone filesystems access health")
            path1_chk_list_file = list_file_base + '_Path1_CHK'
            path2_chk_list_file = list_file_base + '_Path2_CHK'

            xx = []
            if filters_file is not None:
                exclude_other = False
                with io.open(filters_file, mode='rt', encoding='utf8') as f:
                    for line in f:
                        line = line.strip()
                        if line == "- **":
                            exclude_other = True
                            continue
                        if line.startswith("-") and (line.endswith("/") or line.endswith("/*") or line.endswith("/**")):
                            xx.extend(['--filter', line])
                        if line.startswith("+") and (line.endswith("/*") or line.endswith("/**")):
                            xx.extend(['--filter', line + chk_file])

                xx.extend(['--filter', '- rclonesync/Test/'])   # Exclude any check files that may be in any rclonesync/Test source tree

                if "testdir" not in path1_base:                 # If not testing, exclude any check files in any remnant test directory tree.
                    xx.extend(['--filter', '- /testdir/'])
                
                if not exclude_other:
                    xx.extend(['--filter', '+ ' + chk_file])

                xx.extend(['--filter', '- **'])
            
            else:   # No filters_file case
                if "testdir" not in path1_base:         # Normally, disregard any check files in the test directory tree.
                    xx.extend(['--filter', '- /testdir/', '--filter', '- rclonesync/Test/', '--filter', '+ ' + chk_file, '--filter', '- **'])
                else:                                   # If testing, include check files within the test directory tree.
                    xx.extend(['--filter', '- rclonesync/Test/', '--filter', '+ ' + chk_file, '--filter', '- **'])
            
            if rclone_lsl(path1_base, path1_chk_list_file, options=xx, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                return RTN_ABORT

            if rclone_lsl(path2_base, path2_chk_list_file, options=xx, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                return RTN_ABORT

            status, path1_check = load_list(path1_chk_list_file)
            if status:
                logging.error(print_msg("ERROR", "Failed loading Path1 check list file <{}>".format(path1_chk_list_file)))
                return RTN_CRITICAL

            status, path2_check  = load_list(path2_chk_list_file)
            if status:
                logging.error(print_msg("ERROR", "Failed loading Path2 check list file <{}>".format(path2_chk_list_file)))
                return RTN_CRITICAL

            check_error = False
            if len(path1_check) < 1 or len(path1_check) != len(path2_check):
                logging.error(print_msg("ERROR", "Failed access health test:  <{}> Path1 count {}, Path2 count {}"
                                         .format(chk_file, len(path1_check), len(path2_check)), ""))
                check_error = True

            for key in path1_check:
                if key not in path2_check:
                    logging.error(print_msg("ERROR", "Failed access health test:  Path1 key <{}> not found in Path2".format(key), ""))
                    check_error = True
            for key in path2_check:
                if key not in path1_check:
                    logging.error(print_msg("ERROR", "Failed access health test:  Path2 key <{}> not found in Path1".format(key), ""))
                    check_error = True

            if check_error:
                return RTN_CRITICAL

            if not args.keep_chkfiles:
                os.remove(path1_chk_list_file)          # _PathX_CHK files will be left if the check fails.  Look at these files for clues.
                os.remove(path2_chk_list_file)


    # ***** Get current listings of the path1 and path2 trees *****
    path1_list_file_new = list_file_base + '_Path1_NEW'
    if rclone_lsl(path1_base, path1_list_file_new, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL

    path2_list_file_new = list_file_base + '_Path2_NEW'
    if rclone_lsl(path2_base, path2_list_file_new, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL


    # ***** Load Current and Prior listings of both Path1 and Path2 trees *****
    status, path1_prior =  load_list(path1_list_file)                    # Successful load of the file return status = 0.
    if status:                  logging.error(print_msg("ERROR", "Failed loading prior Path1 list file <{}>".format(path1_list_file))); return RTN_CRITICAL
    if len(path1_prior) == 0:   logging.error(print_msg("ERROR", "Zero length in prior Path1 list file <{}>".format(path1_list_file))); return RTN_CRITICAL

    status, path2_prior =  load_list(path2_list_file)
    if status:                  logging.error(print_msg("ERROR", "Failed loading prior Path2 list file <{}>".format(path2_list_file))); return RTN_CRITICAL
    if len(path2_prior) == 0:   logging.error(print_msg("ERROR", "Zero length in prior Path2 list file <{}>".format(path2_list_file))); return RTN_CRITICAL

    status, path1_now =    load_list(path1_list_file_new)
    if status:                  logging.error(print_msg("ERROR", "Failed loading current Path1 list file <{}>".format(path1_list_file_new))); return RTN_ABORT
    if len(path1_now) == 0:     logging.error(print_msg("ERROR", "Zero length in current Path1 list file <{}>".format(path1_list_file_new))); return RTN_ABORT

    status, path2_now =    load_list(path2_list_file_new)
    if status:                  logging.error(print_msg("ERROR", "Failed loading current Path2 list file <{}>".format(path2_list_file_new))); return RTN_ABORT
    if len(path2_now) == 0:     logging.error(print_msg("ERROR", "Zero length in current Path2 list file <{}>".format(path2_list_file_new))); return RTN_ABORT


    # ***** Check for Path1 deltas relative to the prior sync *****
    logging.info(">>>>> Path1 Checking for Diffs")
    path1_deltas = {}
    path1_deleted = 0
    path1_found_same = False
    for key in path1_prior:
        _newer=False; _older=False; _size=False; _deleted=False
        if key not in path1_now:
            logging.info(print_msg("Path1", "  File was deleted", key))
            path1_deleted += 1
            _deleted = True
        else:
            if path1_prior[key]['datetime'] != path1_now[key]['datetime']:
                if path1_prior[key]['datetime'] < path1_now[key]['datetime']:
                    logging.info(print_msg("Path1", "  File is newer", key))
                    _newer = True
                else:               # Current path1 version is older than prior sync.
                    logging.info(print_msg("Path1", "  File is OLDER", key))
                    _older = True
            if path1_prior[key]['size'] != path1_now[key]['size']:
                logging.info(print_msg("Path1", "  File size is different", key))
                _size = True

        if _newer or _older or _size or _deleted:
            path1_deltas[key] = {'new':False, 'newer':_newer, 'older':_older, 'size':_size, 'deleted':_deleted}
        else:
            path1_found_same = True

    for key in path1_now:
        if key not in path1_prior:
            logging.info(print_msg("Path1", "  File is new", key))
            path1_deltas[key] = {'new':True, 'newer':False, 'older':False, 'size':False, 'deleted':False}

    path1_deltas = collections.OrderedDict(sorted(path1_deltas.items()))    # Sort the deltas list.
    if len(path1_deltas) > 0:
        news = newers = olders = deletes = 0
        for key in path1_deltas:
            if path1_deltas[key]['new']:      news += 1
            if path1_deltas[key]['newer']:    newers += 1
            if path1_deltas[key]['older']:    olders += 1
            if path1_deltas[key]['deleted']:  deletes += 1
        logging.info("  {:4} file change(s) on Path1: {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(path1_deltas), news, newers, olders, deletes))


    # ***** Check for Path2 deltas relative to the prior sync *****
    logging.info(">>>>> Path2 Checking for Diffs")
    path2_deltas = {}
    path2_deleted = 0
    path2_found_same = False
    for key in path2_prior:
        _newer=False; _older=False; _size=False; _deleted=False
        if key not in path2_now:
            logging.info(print_msg("Path2", "  File was deleted", key))
            path2_deleted += 1
            _deleted = True
        else:
            if path2_prior[key]['datetime'] != path2_now[key]['datetime']:
                if path2_prior[key]['datetime'] < path2_now[key]['datetime']:
                    logging.info(print_msg("Path2", "  File is newer", key))
                    _newer = True
                else:               # Now Path2 version is older than prior sync.
                    logging.info(print_msg("Path2", "  File is OLDER", key))
                    _older = True
            if path2_prior[key]['size'] != path2_now[key]['size']:
                logging.info(print_msg("Path2", "  File size is different", key))
                _size = True

        if _newer or _older or _size or _deleted:
            path2_deltas[key] = {'new':False, 'newer':_newer, 'older':_older, 'size':_size, 'deleted':_deleted}
        else:
            path2_found_same = True

    for key in path2_now:
        if key not in path2_prior:
            logging.info(print_msg("Path2", "  File is new", key))
            path2_deltas[key] = {'new':True, 'newer':False, 'older':False, 'size':False, 'deleted':False}

    path2_deltas = collections.OrderedDict(sorted(path2_deltas.items()))      # Sort the deltas list.
    if len(path2_deltas) > 0:
        news = newers = olders = deletes = 0
        for key in path2_deltas:
            if path2_deltas[key]['new']:      news += 1
            if path2_deltas[key]['newer']:    newers += 1
            if path2_deltas[key]['older']:    olders += 1
            if path2_deltas[key]['deleted']:  deletes += 1
        logging.info("  {:4} file change(s) on Path2: {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(path2_deltas), news, newers, olders, deletes))


    # ***** Check for too many deleted files - possible error condition and don't want to start deleting on the other side !!! *****
    too_many_path1_deletes = False
    if not force and float(path1_deleted)/len(path1_prior) > float(max_deletes)/100:
        logging.error("Excessive number of deletes (>{}%, {} of {}) found on the Path1 filesystem <{}> - Aborting.  Run with --force if desired."
                       .format(max_deletes, path1_deleted, len(path1_prior), path1_base))
        too_many_path1_deletes = True

    too_many_path2_deletes = False
    if not force and float(path2_deleted)/len(path2_prior) > float(max_deletes)/100:
        logging.error("Excessive number of deletes (>{}%, {} of {}) found on the Path2 filesystem <{}> - Aborting.  Run with --force if desired."
                       .format(max_deletes, path2_deleted, len(path2_prior), path2_base))
        too_many_path2_deletes = True

    if too_many_path1_deletes or too_many_path2_deletes:
        return RTN_ABORT
    
    # ***** Check for all files changed, such as all dates changed due to DST change, to avoid errant copy everything.  See README.md. *****
    if not force and not path1_found_same:
        logging.error("All Path1 prior files were found to be changed.  Something is possibly wrong - Aborting.  Run with --force if desired.")
        return RTN_ABORT
        
    if not force and not path2_found_same:
        logging.error("All Path2 prior files were found to be changed.  Something is possibly wrong - Aborting.  Run with --force if desired.")
        return RTN_ABORT
        

    # ***** Update Path1 with all the changes on Path2 *****
    if len(path2_deltas) == 0:
        logging.info(">>>>> No changes on Path2 - Skipping ahead")
    else:
        logging.info(">>>>> Applying changes on Path2 to Path1")

    for key in path2_deltas:

        if path2_deltas[key]['new']:
            if key not in path1_now:
                # File is new on Path2, does not exist on Path1.
                src  = path2_base + key
                dest = path1_base + key
                logging.info(print_msg("Path2", "  Copying to Path1", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL

            else:
                # File is new on Path1 AND new on Path2.
                src  = path2_base + key 
                dest = path1_base + key + '_Path2' 
                logging.warning(print_msg("WARNING", "  Changed in both Path1 and Path2", key))
                logging.warning(print_msg("Path2", "  Copying to Path1", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL
                # Rename Path1.
                src  = path1_base + key 
                dest = path1_base + key + '_Path1' 
                logging.warning(print_msg("Path1", "  Renaming Path1 copy", dest))
                if rclone_cmd('moveto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL

        if path2_deltas[key]['newer']:
            if key not in path1_deltas:
                # File is newer on Path2, unchanged on Path1.
                src  = path2_base + key 
                dest = path1_base + key 
                logging.info(print_msg("Path2", "  Copying to Path1", dest))
                if rclone_cmd('copyto', src, dest, options=["--ignore-times"] + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL
            else:
                if key in path1_now:
                    # File is newer on Path2 AND also changed (newer/older/size) on Path1.
                    src  = path2_base + key 
                    dest = path1_base + key + '_Path2' 
                    logging.warning(print_msg("WARNING", "  Changed in both Path1 and Path2", key))
                    logging.warning(print_msg("Path2", "  Copying to Path1", dest))
                    if rclone_cmd('copyto', src, dest, options=["--ignore-times"] + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL
                    # Rename Path1.
                    src  = path1_base + key 
                    dest = path1_base + key + '_Path1' 
                    logging.warning(print_msg("Path1", "  Renaming Path1 copy", dest))
                    if rclone_cmd('moveto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL

        if path2_deltas[key]['deleted']:
            if key not in path1_deltas:
                if key in path1_now:
                    # File is deleted on Path2, unchanged on Path1.
                    src  = path1_base + key 
                    logging.info(print_msg("Path1", "  Deleting file", src))
                    if rclone_cmd('delete', src, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL


    for key in path1_deltas:
        if path1_deltas[key]['deleted']:
            if (key in path2_deltas) and (key in path2_now):
                # File is deleted on Path1 AND changed (newer/older/size) on Path2.
                src  = path2_base + key 
                dest = path1_base + key 
                logging.warning(print_msg("WARNING", "  Deleted on Path1 and also changed on Path2", key))
                logging.warning(print_msg("Path2", "  Copying to Path1", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL


    # ***** Sync Path1 changes to Path2 ***** 
    if len(path1_deltas) == 0 and len(path2_deltas) == 0 and not first_sync:
        logging.info(">>>>> No changes on Path1 or Path2 - Skipping sync from Path1 to Path2")
    else:
        logging.info(">>>>> Synching Path1 to Path2")
        # NOTE:  --min-size 0 added to block attempting to overwrite Google Doc files which have size -1 on Google Drive.  180729
        if rclone_cmd('sync', path1_base, path2_base, options=filters + switches + ['--min-size', '0'], linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL


    # ***** Optional rmdirs for empty directories *****
    if rmdirs:
        logging.info(">>>>> rmdirs Path1")
        if rclone_cmd('rmdirs', path1_base, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        logging.info(">>>>> rmdirs Path2")
        if rclone_cmd('rmdirs', path2_base, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL


    # ***** Clean up *****
    logging.info(">>>>> Refreshing Path1 and Path2 lsl files")
    os.remove(path1_list_file_new)
    os.remove(path2_list_file_new)

    if rclone_lsl(path1_base, path1_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL

    if rclone_lsl(path2_base, path2_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL

    return 0


# LINE_FORMAT = re.compile(u'\s*([0-9]+) ([\d\-]+) ([\d:]+).([\d]+) (.*)')
LINE_FORMAT = re.compile(r'\s*([0-9]+) ([\d\-]+) ([\d:]+).([\d]+) (.*)')
def load_list(infile):
    # Format ex:
    #  3009805 2013-09-16 04:13:50.000000000 12 - Wait.mp3
    #   541087 2017-06-19 21:23:28.610000000 DSC02478.JPG
    #     size <----- datetime (epoch) ----> key

    d = {}
    try:
        with io.open(infile, mode='rt', encoding='utf8') as f:
            for line in f:
                out = LINE_FORMAT.match(line)
                if out:
                    size = out.group(1)
                    date = out.group(2)
                    _time = out.group(3)
                    microsec = out.group(4)
                    date_time = time.mktime(datetime.strptime(date + ' ' + _time, '%Y-%m-%d %H:%M:%S').timetuple()) + float('.'+ microsec)
                    filename = out.group(5)
                    d[filename] = {'size': size, 'datetime': date_time}
                else:
                    logging.warning("Something wrong with this line (ignored) in {}.  (Google Doc files cannot be synced.):\n   <{}>".format(infile, line))
        return 0, collections.OrderedDict(sorted(d.items()))        # return Success and a sorted list

    except Exception as e:
        logging.error("Exception in load_list loading <{}>:  <{}>".format(infile, e))
        return 1, ""                                                # return False


def request_lock(caller, lock_file):
    for _ in range(5):
        if os.path.exists(lock_file):
            with io.open(lock_file, mode='rt', encoding='utf8',errors="replace") as fd:
                locked_by = fd.read()
                logging.info("Lock file exists - Waiting a sec: <{}>\n<{}>".format(lock_file, locked_by[:-1]))   # remove the \n
            time.sleep(1)
        else:  
            with io.open(lock_file, mode='wt', encoding='utf8') as fd:
                fd.write("Locked by {} at {}\n".format(caller, time.asctime(time.localtime())))
                logging.info("Lock file created: <{}>".format(lock_file))
            return 0
    logging.warning("Timed out waiting for lock file to be cleared: <{}>".format(lock_file))
    return -1

def release_lock(lock_file):
    if os.path.exists(lock_file):
        logging.info("Lock file removed: <{}>".format(lock_file))
        os.remove(lock_file)
        return 0
    else:
        logging.warning("Attempted to remove lock file but the file does not exist: <{}>".format(lock_file))
        return -1

def keyboardInterruptHandler(signal, frame):
    logging.error("***** KeyboardInterrupt Critical Error Abort - Must run --first-sync to recover.  See README.md *****\n")
    if os.path.exists(path2_list_file):
        shutil.move(path2_list_file, path2_list_file + '_ERROR')
    if os.path.exists(path1_list_file):
        shutil.move(path1_list_file, path1_list_file + '_ERROR')
    release_lock(lock_file)
    exit (2)
signal.signal(signal.SIGINT, keyboardInterruptHandler)
    

if __name__ == '__main__':
    pyversion = sys.version_info[0] + float(sys.version_info[1])/10
    if pyversion < 2.7:
        print("ERROR  The Python version must be >= 2.7.  Found version: {}".format(pyversion)); exit()
    
    parser = argparse.ArgumentParser(description="***** BiDirectional Sync for Cloud Services using rclone *****")
    parser.add_argument('Path1',
                        help="Local path, or cloud service with ':' plus optional path.  Type 'rclone listremotes' for list of configured remotes.")
    parser.add_argument('Path2',
                        help="Local path, or cloud service with ':' plus optional path.  Type 'rclone listremotes' for list of configured remotes.")
    parser.add_argument('-1', '--first-sync',
                        help="First run setup.  WARNING: Path2 files may overwrite path1 versions.  Consider using with --dry-run first.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-c', '--check-access',
                        help="Ensure expected RCLONE_TEST files are found on both path1 and path2 filesystems, else abort.",
                        action='store_true')
    parser.add_argument('--check-filename',
                        help="Filename for --check-access (default is <{}>).".format(CHK_FILE),
                        default=CHK_FILE)
    parser.add_argument('-D', '--max-deletes',
                        help="Safety check for percent maximum deletes allowed (default {}%%).  If exceeded the rclonesync run will abort.  See --force.".format(MAX_DELETE),
                        type=int,
                        default=MAX_DELETE)
    parser.add_argument('-F', '--force',
                        help="Bypass --max-deletes safety check and run the sync.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-e', '--remove-empty-directories',
                        help="Execute rclone rmdirs as a final cleanup step.",
                        action='store_true')
    parser.add_argument('-f','--filters-file',
                        help="File containing rclone file/path filters (needed for Dropbox).",
                        default=None)
    parser.add_argument('-r','--rclone',
                        help="Path to rclone executable (default is rclone in path environment var).",
                        default="rclone")
    parser.add_argument('--config',
                        help="Path to rclone config file (default is typically ~/.config/rclone/rclone.conf).",
                        default=None)
    parser.add_argument('--rclone-args',
                        help="Optional argument(s) to be passed to rclone.  Specify this switch and rclone ags at the end of rclonesync command line.",
                        nargs=argparse.REMAINDER)
    parser.add_argument('-v', '--verbose',
                        help="Enable event logging with per-file details.  Specify once for info and twice for debug detail.",
                        action='count', default=0)
    parser.add_argument('--rc-verbose',
                        help="Enable rclone's verbosity levels (May be specified more than once for more details.  Also asserts --verbose.)",
                        action='count')
    parser.add_argument('-d', '--dry-run',
                        help="Go thru the motions - No files are copied/deleted.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-w', '--workdir',
                        help="Specified working dir - useful for testing.  Default is ~user/.rclonesyncwd.",
                        default=os.path.expanduser("~/.rclonesyncwd"))
    parser.add_argument('--no-datetime-log',
                        help="Disable date-time from log output - useful for testing.",
                        action='store_true')
    parser.add_argument('--keep-chkfiles',
                        help="Disable deleting the --check-access phase CHK files - useful for testing.",
                        action='store_true')
    parser.add_argument('-V', '--version',
                        help="Return rclonesync's version number and exit.",
                        action='version',
                        version='%(prog)s ' + __version__)
    args = parser.parse_args()
    
    first_sync   =  args.first_sync
    check_access =  args.check_access
    chk_file     =  args.check_filename
    if is_Linux and is_Py27:                # Already unicode on Linux Py3 and Win Py2 with win32_unicode_argv module 
        chk_file     =  chk_file.decode("utf-8")
    max_deletes  =  args.max_deletes
    verbose      =  args.verbose
    rc_verbose   =  args.rc_verbose
    if rc_verbose == None: rc_verbose = 0
    filters_file =  args.filters_file
    if args.filters_file is not None and is_Linux and is_Py27:  # As with chk_file
        filters_file =  filters_file.decode("utf-8")
    rclone       =  args.rclone
    dry_run      =  args.dry_run
    force        =  args.force
    rmdirs       =  args.remove_empty_directories

    workdir      =  args.workdir
    if not (workdir.endswith('/') or workdir.endswith('\\')):   # 2nd check is for Windows paths
        workdir += '/'

    if not args.no_datetime_log:
        logging.basicConfig(format='%(asctime)s:  %(message)s') # /%(levelname)s/%(module)s/%(funcName)s
    else:
        logging.basicConfig(format='%(message)s')

    if verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)             # Log debug detail
    elif verbose>0 or rc_verbose>0 or force or first_sync or dry_run:
        # verbose = True
        logging.getLogger().setLevel(logging.INFO)              # Log each file transaction
    else:
        logging.getLogger().setLevel(logging.WARNING)           # Log only unusual events

    if is_Windows:
        chcp = subprocess.check_output(["chcp"], shell=True).decode("utf-8")
        err = False
        py_encode_env = ''
        if "PYTHONIOENCODING" in os.environ:
            py_encode_env = os.environ["PYTHONIOENCODING"]
        if "65001" not in chcp:
            print ("ERROR  In the Windows CMD shell execute <chcp 65001> to enable support for UTF-8.")
            err = True
        if py_encode_env.lower().replace('-','') != "utf8":
            print ("ERROR  In the Windows CMD shell execute <set PYTHONIOENCODING=UTF-8> to enable support for UTF-8.")
            err = True
        if err:
            exit()

    logging.info("***** BiDirectional Sync for Cloud Services using rclone ({}) *****".format(__version__))

    rcconfig = args.config
    if rcconfig is None:
        try:  # Extract the second line from the two line <rclone config file> output similar to:
                # Configuration file is stored at:
                # /home/<me>/.config/rclone/rclone.conf
            rcconfig = str(subprocess.check_output([rclone, "config", "file"]).decode("utf8")).split(':\n')[1].strip()
        except subprocess.CalledProcessError as e:
            print("ERROR  from <rclone config file> - can't get the config file path."); exit()
    if not os.path.exists(rcconfig):
        print("ERROR  rclone config file <{}> not found.".format(rcconfig)); exit()

    try:
        clouds = subprocess.check_output([rclone, "listremotes", "--config", rcconfig]).decode("utf8").split()
    except subprocess.CalledProcessError as e:
        print("ERROR  Can't get list of known remotes.  Have you run rclone config?"); exit()
    except:
        print("ERROR  rclone not installed, or invalid --rclone path?\nError message: {}\n".format(sys.exc_info()[1])); exit()

    def pathparse(path):
        """Handle variations in a path argument.
        Cloud:              - Root of the defined cloud
        Cloud:some/path     - Supported with our without path leading '/'s
        X:                  - Windows drive letter
        X:\\some\\path      - Windows drive letter with absolute or relative path
        some/path           - Relative path from cwd (and on current drive on Windows)
        //server/path       - UNC paths are supported
        On Windows a one-character cloud name is not supported - it will be interprested as a drive letter.
        """
        
        if is_Linux and is_Py27:
            path = path.decode("utf-8")
        
        _cloud = False
        if ':' in path:
            if len(path) == 1:                                  # Handle corner case of ':' only passed in
                logging.error("ERROR  Path argument <{}> not a legal path".format(path)); exit()
            if path[1] == ':' and is_Windows:                   # Windows drive letter case
                path_base = path
                if not path_base.endswith('\\'):                # For consistency ensure the path ends with '/'
                    path_base += '/'
            else:                                               # Cloud case with optional path part
                path_FORMAT = re.compile(r'([\w-]+):(.*)')
                out = path_FORMAT.match(path)
                if out:
                    _cloud = True
                    cloud_name = out.group(1) + ':'
                    if cloud_name not in clouds:
                        logging.error("ERROR  Path argument <{}> not in list of configured Clouds: {}"
                                      .format(cloud_name, clouds)); exit()
                    path_part = out.group(2)
                    if path_part:
                        # if not path_part.startswith('/'):       # NOT - For consistency ensure the cloud path part starts and ends with /'s
                        #     path_part = '/' + path_part         # For SFTP remotes adding a '/' makes reference to the filesystem root.  Bad.
                        if not (path_part.endswith('/') or path_part.endswith('\\')):    # 2nd check is for Windows paths
                            path_part += '/'
                    path_base = cloud_name + path_part
        else:                                                   # Local path (without Windows drive letter)
            path_base = path
            if not (path_base.endswith('/') or path_base.endswith('\\')):
                path_base += '/'

        if not _cloud:
            if not os.path.exists(path_base):
                logging.error("ERROR  Local path parameter <{}> cannot be accessed.  Path error?  Aborting"
                              .format(path_base)); exit()

        return path_base

    path1_base = pathparse(args.Path1)
    path2_base = pathparse(args.Path2)


    lock_file = os.path.join(tempfile.gettempdir(), 'rclonesync_LOCK_' + (
        path1_base + path2_base).replace(':','_').replace(r'/','_').replace('\\','_'))

    if request_lock(sys.argv, lock_file) == 0:
        status = bidirSync()
        release_lock(lock_file)
        if status == RTN_CRITICAL:
            logging.error("***** Critical Error Abort - Must run --first-sync to recover.  See README.md *****\n")
            if os.path.exists(path2_list_file):
                shutil.move(path2_list_file, path2_list_file + '_ERROR')
            if os.path.exists(path1_list_file):
                shutil.move(path1_list_file, path1_list_file + '_ERROR')
            exit (2)
        if status == RTN_ABORT:
            logging.error("***** Error Abort.  Try running rclonesync again. *****\n")
            exit (1)
        if status == 0:
            logging.info(">>>>> Successful run.  All done.\n")
            exit (0)
    else:
        logging.warning("***** Prior lock file in place, aborting.  Try running rclonesync again. *****\n")
        exit (1)

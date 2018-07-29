#!/usr/bin/env python
"""BiDirectional Sync using rclone"""

__version__ = "V2.1 180729"                          # Version number and date code


#==========================================================================================================
# Configure rclone, including authentication before using this tool.  rclone must be in the search path.
#
# Chris Nelson, November 2017 - 2018
# Revision and contributions:
#   Hildo G. Jr.
#
# See README.md for revision history
#
# Known bugs:
#   remove size compare since its not used
#
#==========================================================================================================

import argparse
import sys
import re
import os.path
import subprocess
from datetime import datetime
import time
import logging
import inspect                                      # For getting the line number for error messages.
import collections                                  # For dictionary sorting.
import hashlib                                      # For checking if the filter file changed and force --first_sync.


# Configurations and constants
MAX_DELETE = 50                                     # % deleted allowed, else abort.  Use --force or --max_deletess to override.

RTN_ABORT = 1                                       # Tokens for return codes based on criticality.
RTN_CRITICAL = 2                                    # Aborts allow rerunning.  Criticals block further runs.  See Readme.md.


def bidirSync():

    def print_msg(path2e, msg, key=''):
        return "  {:9}{:35} - {}".format(path2e, msg, key)

 
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    global path1_list_file, path2_list_file
    list_file_base  = workdir + "LSL_" + (path1_base + path2_base).replace(':','_').replace(r'/','_')
            # '/home/<user>/.rclonesyncwd/LSL_<path1_base><path2_base>'
    path1_list_file = list_file_base + '_Path1'
    path2_list_file = list_file_base + '_Path2'

    logging.warning("Synching Path1  <{}>  with Path2  <{}>".format(path1_base, path2_base))
    logging.info("Command line:  <{}>".format(args))


    # ***** Handle filters_file, if provided *****
    filters = []
    if filters_file is not None:
        logging.info("Using filters-file  <{}>".format(filters_file))

        if not os.path.exists(filters_file):
            logging.error("Specified filters-file file does not exist:  " + filters_file)
            return RTN_CRITICAL

        filters_fileMD5 = filters_file + "-MD5"

        with open(filters_file, 'r') as ifile:
            current_file_hash = hashlib.md5(ifile.read().replace("\r", "").encode('utf-8')).hexdigest()
            # If the filters file is written from windows it will have a \r in it.  Py2.7 on Windows discards
            # the \r, as does Py3.6 on Linux, but Py2.7 on Linux includes the \r in the calculated hash, resulting
            # in a different file hash than in other environments.  Removing the \r makes the calculation platform
            # agnostic.

        stored_file_hash = ''
        if os.path.exists(filters_fileMD5):
            with open(filters_fileMD5) as ifile:
                stored_file_hash = ifile.read()
        elif not first_sync:
            logging.error("MD5 file not found for filters file <{}>.  Must run --first-sync.".format(filters_file))
            return RTN_CRITICAL

        if current_file_hash != stored_file_hash and not first_sync:
            logging.error("Filters-file <{}> has chanaged (MD5 does not match).  Must run --first-sync.".format(filters_file))
            return RTN_CRITICAL

        if first_sync:
            logging.info("Storing filters-file hash to <{}>".format(filters_fileMD5))
            with open(filters_fileMD5, 'w') as ofile:
                ofile.write(current_file_hash) # + "\n")

        filters.append("--filter-from")
        filters.append(filters_file)


    # ***** Set up dry_run and rclone --verbose switches *****
    switches = []
    for x in range(rc_verbose):
        switches.append("-v")
    if dry_run:
        switches.append("--dry-run")
        if os.path.exists(path2_list_file):          # If dry_run, original LSL files are preserved and lsl's are done to the _DRYRUN files.
            subprocess.call(['cp', path2_list_file, path2_list_file + '_DRYRUN'])
            path2_list_file  += '_DRYRUN'
        if os.path.exists(path1_list_file):
            subprocess.call(['cp', path1_list_file, path1_list_file + '_DRYRUN'])
            path1_list_file += '_DRYRUN'


    # ***** rclone call wrapper functions with retries *****
    maxTries=3
    def rclone_lsl(path, ofile, options=None, linenum=0):
        for x in range(maxTries):
            with open(ofile, "w") as of:
                process_args = ["rclone", "lsl", path]
                if options is not None:
                    process_args.extend(options)
                if not subprocess.call(process_args, stdout=of):
                    return 0
                logging.warning(print_msg("WARNING", "rclone lsl try {} failed.".format(x+1), path))
        logging.error(print_msg("ERROR", "rclone lsl failed.  Specified path invalid?  (Line {})".format(linenum), path))
        return 1
        
    def rclone_cmd(cmd, p1=None, p2=None, options=None, linenum=0):
        for x in range(maxTries):
            process_args = ["rclone", cmd]
            if p1 is not None:
                process_args.append(p1)
            if p2 is not None:
                process_args.append(p2)
            if options is not None:
                process_args.extend(options)
            if not subprocess.call(process_args):
                return 0
            logging.warning(print_msg("WARNING", "rclone {} try {} failed.".format(cmd, x+1), p1))
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


    # ***** Check basic health of access to the Path1 and Path2 filesystems *****
    if check_access:
        if first_sync:
            logging.info(">>>>> --check-access skipped on --first-sync")
        else:
            logging.info(">>>>> Checking Path1 and Path2 rclone filesystems access health")
            path1_chk_list_file = list_file_base + '_Path1_CHK'
            path2_chk_list_file = list_file_base + '_Path2_CHK'
            CHK_FILE = 'RCLONE_TEST'

            if "testdir" not in path1_base:         # Normally, disregard any RCLONE_TEST files in the test directory tree.
                xx = ['--filter', '- /testdir/', '--filter', '- rclonesync/Test/', '--filter', '+ ' + CHK_FILE, '--filter', '- *']
            else:                                   # If testing, include RCLONE_TEST files within the test directory tree.
                xx = ['--filter', '- rclonesync/Test/', '--filter', '+ ' + CHK_FILE, '--filter', '- *']
            
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
                                         .format(CHK_FILE, len(path1_check), len(path2_check)), ""))
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

            os.remove(path1_chk_list_file)          # _*ChkLSL files will be left if the check fails.  Look at these files for clues.
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
        logging.warning("  {:4} file change(s) on Path1: {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(path1_deltas), news, newers, olders, deletes))


    # ***** Check for Path2 deltas relative to the prior sync *****
    logging.info(">>>>> Path2 Checking for Diffs")
    path2_deltas = {}
    path2_deleted = 0
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
        logging.warning("  {:4} file change(s) on Path2: {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(path2_deltas), news, newers, olders, deletes))


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


LINE_FORMAT = re.compile('\s*([0-9]+) ([\d\-]+) ([\d:]+).([\d]+) (.*)')
def load_list(infile):
    # Format ex:
    #  3009805 2013-09-16 04:13:50.000000000 12 - Wait.mp3
    #   541087 2017-06-19 21:23:28.610000000 DSC02478.JPG
    #    size  <----- datetime (epoch) ----> key

    d = {}
    try:
        with open(infile, 'r') as f:
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
    except:
        logging.error("Exception in load_list loading <{}>:  <{}>".format(infile, sys.exc_info()))
        return 1, ""                                                # return False


LOCK_FILE = "/tmp/rclonesync_LOCK"
def request_lock(caller):
    for xx in range(5):
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE) as fd:
                locked_by = fd.read()
                logging.debug("{}.  Waiting a sec.".format(locked_by[:-1]))   # remove the \n
            time.sleep(1)
        else:  
            with open(LOCK_FILE, 'w') as fd:
                fd.write("Locked by {} at {}\n".format(caller, time.asctime(time.localtime())))
                logging.debug("LOCKed by {} at {}.".format(caller, time.asctime(time.localtime())))
            return 0
    logging.warning("Timed out waiting for LOCK file to be cleared.  {}".format(locked_by))
    return -1

def release_lock(caller):
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE) as fd:
            locked_by = fd.read()
            logging.debug("Removed lock file:  {}.".format(locked_by))
        os.remove(LOCK_FILE)
        return 0
    else:
        logging.warning("<{}> attempted to remove /tmp/LOCK but the file does not exist.".format(caller))
        return -1
        


if __name__ == '__main__':

    try:
        clouds = subprocess.check_output(['rclone', 'listremotes'])
    except subprocess.CalledProcessError as e:
        print("ERROR  Can't get list of known path1s.  Have you run rclone config?"); exit()
    except:
        print("ERROR  rclone not installed?\nError message: {}\n".format(sys.exc_info()[1])); exit()
    clouds = str(clouds.decode("utf8")).split()     # Required for Python 3 so that clouds can be compared to a string

    parser = argparse.ArgumentParser(description="***** BiDirectional Sync for Cloud Services using rclone *****")
    parser.add_argument('Path1',
                        help="Local path, or cloud service ({}) plus optional path.".format(clouds))
    parser.add_argument('Path2',
                        help="Local path, or cloud service ({}) plus optional path.".format(clouds))
    parser.add_argument('-1', '--first-sync',
                        help="First run setup.  WARNING: Path2 files may overwrite path1 versions.  Consider using with --dry-run first.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-c', '--check-access',
                        help="Ensure expected RCLONE_TEST files are found on both path1 and path2 filesystems, else abort.",
                        action='store_true')
    parser.add_argument('-D', '--max-deletes',
                        help="Safety check for percent maximum deletes allowed (default {}%%).  If exceeded the rclonesync run will abort.  See --force.".format(MAX_DELETE),
                        type=int,
                        default=MAX_DELETE)
    parser.add_argument('-F', '--force',
                        help="Bypass --max-deletes safety check and run the sync.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-f','--filters-file',
                        help="File containing rclone file/path filters (needed for Dropbox).",
                        default=None)
    parser.add_argument('-v', '--verbose',
                        help="Enable event logging with per-file details.",
                        action='store_true')
    parser.add_argument('--rc-verbose',
                        help="Enable rclone's verbosity levels (May be specified more than once for more details.  Also asserts --verbose.)",
                        action='count')
    parser.add_argument('-d', '--dry-run',
                        help="Go thru the motions - No files are copied/deleted.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-w', '--workdir',
                        help="Specified working dir - used for testing.  Default is ~user/.rclonesyncwd.",
                        default=os.path.expanduser("~/.rclonesyncwd"))
    parser.add_argument('--no-datetime-log',
                        help="Disable date-time from log output - used for testing.",
                        action='store_true')
    parser.add_argument('-V', '--version',
                        help="Return rclonesync's version number and exit.",
                        action='version',
                        version='%(prog)s ' + __version__)
    args = parser.parse_args()

    first_sync   =  args.first_sync
    check_access =  args.check_access
    max_deletes  =  args.max_deletes
    verbose      =  args.verbose
    rc_verbose   =  args.rc_verbose
    if rc_verbose == None: rc_verbose = 0
    filters_file =   args.filters_file
    dry_run      =  args.dry_run
    force        =  args.force
    workdir      =  args.workdir + '/'

    if not args.no_datetime_log:
        logging.basicConfig(format='%(asctime)s:  %(message)s') # /%(levelname)s/%(module)s/%(funcName)s
    else:
        logging.basicConfig(format='%(message)s')

    logging.warning("***** BiDirectional Sync for Cloud Services using rclone *****")

    pathx_FORMAT = re.compile('([\w-]+):(.*)')                  # Handle variations in the Cloud argument -- Cloud: or Cloud:some/path or Cloud:/some/path
    out = pathx_FORMAT.match(args.Path1)
    path1_name = path1_path_part = path1_base = ''
    if out:
        path1_name = out.group(1) + ':'
        if path1_name not in clouds:
            logging.error("ERROR  Path1 argument <{}> not in list of configured Clouds: {}"
                          .format(path1_name, clouds)); exit()
        path1_path_part = out.group(2)
        if path1_path_part:
            if not path1_path_part.startswith('/'):
                path1_path_part = '/' + path1_path_part         # For consistency ensure the path part starts and ends with /'s
            if not path1_path_part.endswith('/'):
                path1_path_part += '/'
        path1_base = path1_name + path1_path_part               # 'path1:' or 'path1:/some/path/'
    else:
        path1_base = args.Path1
        if not path1_base.endswith('/'):                        # For consistency ensure the path ends with /
            path1_base += '/'
        if not os.path.exists(path1_base):
            logging.error("ERROR  Path1 parameter <{}> cannot be accessed.  Path error?  Aborting"
                          .format(path1_base)); exit()

    out = pathx_FORMAT.match(args.Path2)
    path2_name = path2_path_part = path2_base = ''
    if out:
        path2_name = out.group(1) + ':'
        if path2_name not in clouds:
            logging.error("ERROR  Path2 argument <{}> not in list of configured Clouds: {}"
                          .format(path2_name, clouds)); exit()
        path2_path_part = out.group(2)
        if path2_path_part:
            if not path2_path_part.startswith('/'):
                path2_path_part = '/' + path2_path_part
            if not path2_path_part.endswith('/'):
                path2_path_part += '/'
        path2_base = path2_name + path2_path_part
    else:
        path2_base = args.Path2
        if not path2_base.endswith('/'):
            path2_base += '/'
        if not os.path.exists(path2_base):
            logging.error("ERROR  path2 parameter <{}> cannot be accessed.  Path error?  Aborting"
                          .format(path2_base)); exit()


    if verbose or rc_verbose>0 or force or first_sync or dry_run:
        verbose = True
        logging.getLogger().setLevel(logging.INFO)              # Log each file transaction
    else:
        logging.getLogger().setLevel(logging.WARNING)           # Log only unusual events


    if request_lock(sys.argv) == 0:
        status = bidirSync()
        if status == RTN_CRITICAL:
            logging.error("***** Critical Error Abort - Must run --first-sync to recover.  See README.md *****\n")
            if os.path.exists(path2_list_file):
                subprocess.call(['mv', path2_list_file, path2_list_file + '_ERROR'])
            if os.path.exists(path1_list_file):
                subprocess.call(['mv', path1_list_file, path1_list_file + '_ERROR'])
        if status == RTN_ABORT:
            logging.error("***** Error Abort.  Try running rclonesync again. *****\n")
        if status == 0:            
            logging.warning(">>>>> Successful run.  All done.\n")
        release_lock(sys.argv)
    else:  logging.warning("***** Prior lock file in place, aborting.  Try running rclonesync again. *****\n")

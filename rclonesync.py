#!/usr/bin/env python
"""BiDirectional Sync using rclone"""

__version__ = "V2.0 180701"                          # Version number and date code


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

    def print_msg(locale, msg, key=''):
        return "  {:9}{:35} - {}".format(locale, msg, key)

 
    if not os.path.exists(local_wd):
        os.makedirs(local_wd)

    global local_list_file, remote_list_file
    list_file_base   = local_wd + remote_path_base.replace(':','_').replace(r'/','_')    # '/home/<user>/.rclonesyncwd/<Remote_><_some_path_>' or '/home/<user>/.rclonesyncwd/<Remote_>'.
    local_list_file  = list_file_base + '_llocalLSL'    # '/home/<user>/.rclonesyncwd/<Remote_><_some_path_>_llocalLSL' (extra 'l' to make the dir list pretty)
    remote_list_file = list_file_base + '_remoteLSL'    # '/home/<user>/.rclonesyncwd/<Remote_><_some_path_>_remoteLSL'

    logging.warning("Synching Remote path  <{}>  with Local path  <{}>".format(remote_path_base, local_path_base))
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
            # the \r, as does Py3.6 on Linux, but Py2.7 on Linux includes the \r in the calucated hash, resulting
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
        if os.path.exists(local_list_file):          # If dry_run, original LSL files are preserved and lsl's are done to the _DRYRUN files.
            subprocess.call(['cp', local_list_file, local_list_file + '_DRYRUN'])
            local_list_file  += '_DRYRUN'
        if os.path.exists(remote_list_file):
            subprocess.call(['cp', remote_list_file, remote_list_file + '_DRYRUN'])
            remote_list_file += '_DRYRUN'


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


    # ***** first_sync generate local and remote file lists, and copy any unique Remote files to Local ***** 
    if first_sync:
        logging.info(">>>>> Generating --first-sync Local and Remote lists")
        if rclone_lsl(local_path_base, local_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        if rclone_lsl(remote_path_base, remote_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        status, local_now  = load_list(local_list_file)
        if status:
            logging.error(print_msg("ERROR", "Failed loading local list file <{}>".format(local_list_file)))
            return RTN_CRITICAL

        status, remote_now = load_list(remote_list_file)
        if status:
            logging.error(print_msg("ERROR", "Failed loading remote list file <{}>".format(remote_list_file)))
            return RTN_CRITICAL

        for key in remote_now:
            if key not in local_now:
                src  = remote_path_base + key
                dest = local_path_base + key
                logging.info(print_msg("REMOTE", "  Copying to local", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL

        if rclone_lsl(local_path_base, local_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL


    # ***** Check for existance of prior local and remote lsl files *****
    if not os.path.exists(local_list_file) or not os.path.exists(remote_list_file):
        # On prior critical error abort, the prior LSL files are renamed to _ERRROR to lock out further runs
        logging.error("***** Cannot find prior local or remote lsl files.")
        return RTN_CRITICAL


    # ***** Check basic health of access to the local and remote filesystems *****
    if check_access:
        if first_sync:
            logging.info(">>>>> --check-access skipped on --first-sync")
        else:
            logging.info(">>>>> Checking rclone Local and Remote filesystems access health")
            local_chk_list_file  = list_file_base + '_llocalChkLSL'
            remote_chk_list_file = list_file_base + '_remoteChkLSL'
            chk_file = 'RCLONE_TEST'

            if "testdir" not in remote_path_base:   # Normally, disregard any RCLONE_TEST files in the test directory tree.
                xx = ['--filter', '- /testdir/', '--filter', '- rclonesync/Test/', '--filter', '+ RCLONE_TEST', '--filter', '- *']
            else:                                   # If testing, include RCLONE_TEST files within the test directory tree.
                xx = ['--filter', '- rclonesync/Test/', '--filter', '+ RCLONE_TEST', '--filter', '- *']
            
            if rclone_lsl(local_path_base, local_chk_list_file, options=xx, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                return RTN_ABORT

            if rclone_lsl(remote_path_base, remote_chk_list_file, options=xx, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                return RTN_ABORT

            status, local_check  = load_list(local_chk_list_file)
            if status:
                logging.error(print_msg("ERROR", "Failed loading local check list file <{}>".format(local_chk_list_file)))
                return RTN_CRITICAL

            status, remote_check = load_list(remote_chk_list_file)
            if status:
                logging.error(print_msg("ERROR", "Failed loading remote check list file <{}>".format(remote_chk_list_file)))
                return RTN_CRITICAL

            if len(local_check) < 1 or len(local_check) != len(remote_check):
                logging.error(print_msg("ERROR", "Failed access health test:  <{}> local count {}, remote count {}"
                                         .format(chk_file, len(local_check), len(remote_check)), ""))
                return RTN_CRITICAL
            else:
                for key in local_check:
                    logging.debug("Check key <{}>".format(key))
                    if key not in remote_check:
                        logging.error(print_msg("ERROR", "Failed access health test:  Local key <{}> not found in remote".format(key), ""))
                        return RTN_CRITICAL

            os.remove(local_chk_list_file)          # _*ChkLSL files will be left if the check fails.  Look at these files for clues.
            os.remove(remote_chk_list_file)


    # ***** Get current listings of the local and remote trees *****
    logging.info(">>>>> Generating Local and Remote lists")

    local_list_file_new = list_file_base + '_llocalLSL_new'
    if rclone_lsl(local_path_base, local_list_file_new, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL

    remote_list_file_new = list_file_base + '_remoteLSL_new'
    if rclone_lsl(remote_path_base, remote_list_file_new, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL


    # ***** Load Current and Prior listings of both Local and Remote trees *****
    status, local_prior =   load_list(local_list_file)                    # Successful load of the file return status = 0.
    if status:                  logging.error(print_msg("ERROR", "Failed loading prior local list file <{}>".format(local_list_file))); return RTN_CRITICAL
    if len(local_prior) == 0:    logging.error(print_msg("ERROR", "Zero length in prior local list file <{}>".format(local_list_file))); return RTN_CRITICAL

    status, remote_prior =  load_list(remote_list_file)
    if status:                  logging.error(print_msg("ERROR", "Failed loading prior remote list file <{}>".format(remote_list_file))); return RTN_CRITICAL
    if len(remote_prior) == 0:   logging.error(print_msg("ERROR", "Zero length in prior remote list file <{}>".format(remote_list_file))); return RTN_CRITICAL

    status, local_now =     load_list(local_list_file_new)
    if status:                  logging.error(print_msg("ERROR", "Failed loading current local list file <{}>".format(local_list_file_new))); return RTN_ABORT
    if len(local_now) == 0:      logging.error(print_msg("ERROR", "Zero length in current local list file <{}>".format(local_list_file_new))); return RTN_ABORT

    status, remote_now =    load_list(remote_list_file_new)
    if status:                  logging.error(print_msg("ERROR", "Failed loading current remote list file <{}>".format(remote_list_file_new))); return RTN_ABORT
    if len(remote_now) == 0:     logging.error(print_msg("ERROR", "Zero length in current remote list file <{}>".format(remote_list_file_new))); return RTN_ABORT


    # ***** Check for LOCAL deltas relative to the prior sync *****
    logging.info(print_msg("LOCAL", "Checking for Diffs", local_path_base))
    local_deltas = {}
    local_deleted = 0
    for key in local_prior:
        _newer=False; _older=False; _size=False; _deleted=False
        if key not in local_now:
            logging.info(print_msg("LOCAL", "  File was deleted", key))
            local_deleted += 1
            _deleted = True
        else:
            if local_prior[key]['datetime'] != local_now[key]['datetime']:
                if local_prior[key]['datetime'] < local_now[key]['datetime']:
                    logging.info(print_msg("LOCAL", "  File is newer", key))
                    _newer = True
                else:               # Now local version is older than prior sync.
                    logging.info(print_msg("LOCAL", "  File is OLDER", key))
                    _older = True
            if local_prior[key]['size'] != local_now[key]['size']:
                logging.info(print_msg("LOCAL", "  File size is different", key))
                _size = True

        if _newer or _older or _size or _deleted:
            local_deltas[key] = {'new':False, 'newer':_newer, 'older':_older, 'size':_size, 'deleted':_deleted}

    for key in local_now:
        if key not in local_prior:
            logging.info(print_msg("LOCAL", "  File is new", key))
            local_deltas[key] = {'new':True, 'newer':False, 'older':False, 'size':False, 'deleted':False}

    local_deltas = collections.OrderedDict(sorted(local_deltas.items()))      # Sort the deltas list.
    if len(local_deltas) > 0:
        news = newers = olders = deletes = 0
        for key in local_deltas:
            if local_deltas[key]['new']:      news += 1
            if local_deltas[key]['newer']:    newers += 1
            if local_deltas[key]['older']:    olders += 1
            if local_deltas[key]['deleted']:  deletes += 1
        logging.warning("  {:4} file change(s) on LOCAL:  {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(local_deltas), news, newers, olders, deletes))


    # ***** Check for REMOTE deltas relative to the prior sync *****
    logging.info(print_msg("REMOTE", "Checking for Diffs", remote_path_base))
    remote_deltas = {}
    remote_deleted = 0
    for key in remote_prior:
        _newer=False; _older=False; _size=False; _deleted=False
        if key not in remote_now:
            logging.info(print_msg("REMOTE", "  File was deleted", key))
            remote_deleted += 1
            _deleted = True
        else:
            if remote_prior[key]['datetime'] != remote_now[key]['datetime']:
                if remote_prior[key]['datetime'] < remote_now[key]['datetime']:
                    logging.info(print_msg("REMOTE", "  File is newer", key))
                    _newer = True
                else:               # Current remote version is older than prior sync.
                    logging.info(print_msg("REMOTE", "  File is OLDER", key))
                    _older = True
            if remote_prior[key]['size'] != remote_now[key]['size']:
                logging.info(print_msg("REMOTE", "  File size is different", key))
                _size = True

        if _newer or _older or _size or _deleted:
            remote_deltas[key] = {'new':False, 'newer':_newer, 'older':_older, 'size':_size, 'deleted':_deleted}

    for key in remote_now:
        if key not in remote_prior:
            logging.info(print_msg("REMOTE", "  File is new", key))
            remote_deltas[key] = {'new':True, 'newer':False, 'older':False, 'size':False, 'deleted':False}

    remote_deltas = collections.OrderedDict(sorted(remote_deltas.items()))    # Sort the deltas list.
    if len(remote_deltas) > 0:
        news = newers = olders = deletes = 0
        for key in remote_deltas:
            if remote_deltas[key]['new']:      news += 1
            if remote_deltas[key]['newer']:    newers += 1
            if remote_deltas[key]['older']:    olders += 1
            if remote_deltas[key]['deleted']:  deletes += 1
        logging.warning("  {:4} file change(s) on REMOTE: {:4} new, {:4} newer, {:4} older, {:4} deleted".format(len(remote_deltas), news, newers, olders, deletes))


    # ***** Check for too many deleted files - possible error condition and don't want to start deleting on the other side !!! *****
    to_many_local_deletes = False
    if not force and float(local_deleted)/len(local_prior) > float(max_deletes)/100:
        logging.error("Excessive number of deletes (>{}%, {} of {}) found on the Local system {} - Aborting.  Run with --force if desired."
                       .format(max_deletes, local_deleted, len(local_prior), local_path_base))
        to_many_local_deletes = True

    to_many_remote_deletes = False    # Local error message placed here so that it is at the end of the listed changes for both.
    if not force and float(remote_deleted)/len(remote_prior) > float(max_deletes)/100:
        logging.error("Excessive number of deletes (>{}%, {} of {}) found on the Remote system {} - Aborting.  Run with --force if desired."
                       .format(max_deletes, remote_deleted, len(remote_prior), remote_path_base))
        to_many_remote_deletes = True

    if to_many_local_deletes or to_many_remote_deletes:
        return RTN_ABORT


    # ***** Update LOCAL with all the changes on REMOTE *****
    if len(remote_deltas) == 0:
        logging.info(">>>>> No changes on Remote - Skipping ahead")
    else:
        logging.info(">>>>> Applying changes on Remote to Local")

    for key in remote_deltas:

        if remote_deltas[key]['new']:
            #logging.info(print_msg("REMOTE", "  New file", key))
            if key not in local_now:
                # File is new on remote, does not exist on local.
                src  = remote_path_base + key
                dest = local_path_base + key
                logging.info(print_msg("REMOTE", "  Copying to local", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL

            else:
                # File is new on remote AND new on local.
                src  = remote_path_base + key 
                dest = local_path_base + key + '_REMOTE' 
                logging.warning(print_msg("WARNING", "  Changed in both local and remote", key))
                logging.warning(print_msg("REMOTE", "  Copying to local", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL
                # Rename local.
                src  = local_path_base + key 
                dest = local_path_base + key + '_LOCAL' 
                logging.warning(print_msg("LOCAL", "  Renaming local copy", dest))
                if rclone_cmd('moveto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL


        if remote_deltas[key]['newer']:
            if key not in local_deltas:
                # File is newer on remote, unchanged on local.
                src  = remote_path_base + key 
                dest = local_path_base + key 
                logging.info(print_msg("REMOTE", "  Copying to local", dest))
                if rclone_cmd('copyto', src, dest, options=["--ignore-times"] + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL
            else:
                if key in local_now:
                    # File is newer on remote AND also changed (newer/older/size) on local.
                    src  = remote_path_base + key 
                    dest = local_path_base + key + '_REMOTE' 
                    logging.warning(print_msg("WARNING", "  Changed in both local and remote", key))
                    logging.warning(print_msg("REMOTE", "  Copying to local", dest))
                    if rclone_cmd('copyto', src, dest, options=["--ignore-times"] + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL
                    # Rename local.
                    src  = local_path_base + key 
                    dest = local_path_base + key + '_LOCAL' 
                    logging.warning(print_msg("LOCAL", "  Renaming local copy", dest))
                    if rclone_cmd('moveto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL
## 180622 - redundant with below.  Resulted in copying a file to local twice
##                else:
##                    # File is newer on remote AND also deleted locally.
##                    src  = remote_path_base + key 
##                    dest = local_path_base + key 
##                    logging.info(print_msg("REMOTE", "  Copying to local", dest))
##                    if rclone_cmd('copyto', src, dest, options=["--ignore-times"] + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
##                        return RTN_CRITICAL
                    

        if remote_deltas[key]['deleted']:
            if key not in local_deltas:
                if key in local_now:
                    # File is deleted on remote, unchanged locally.
                    src  = local_path_base + key 
                    logging.info(print_msg("LOCAL", "  Deleting file", src))
                    if rclone_cmd('delete', src, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                        return RTN_CRITICAL


    for key in local_deltas:     # 180622 above was redundant with this section.
        if local_deltas[key]['deleted']:
            if (key in remote_deltas) and (key in remote_now):
                # File is deleted on local AND changed (newer/older/size) on remote.
                src  = remote_path_base + key 
                dest = local_path_base + key 
                logging.warning(print_msg("WARNING", "  Deleted locally and also changed remotely", key))
                logging.warning(print_msg("REMOTE", "  Copying to local", dest))
                if rclone_cmd('copyto', src, dest, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
                    return RTN_CRITICAL


    # ***** Sync LOCAL changes to REMOTE ***** 
    if len(remote_deltas) == 0 and len(local_deltas) == 0 and not first_sync:
        logging.info(">>>>> No changes on Local  - Skipping sync from Local to Remote")
    else:
        logging.info(">>>>> Synching Local to Remote")
        if rclone_cmd('sync', local_path_base, remote_path_base, options=filters + switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        logging.info(">>>>> rmdirs Remote")
        if rclone_cmd('rmdirs', remote_path_base, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL

        logging.info(">>>>> rmdirs Local")
        if rclone_cmd('rmdirs', local_path_base, options=switches, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
            return RTN_CRITICAL


    # ***** Clean up *****
    logging.info(">>>>> Refreshing Local and Remote lsl files")
    os.remove(remote_list_file_new)
    os.remove(local_list_file_new)

    if rclone_lsl(local_path_base, local_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
        return RTN_CRITICAL

    if rclone_lsl(remote_path_base, remote_list_file, filters, linenum=inspect.getframeinfo(inspect.currentframe()).lineno):
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
                    logging.warning("Something wrong with this line (ignored) in {}:\n   <{}>".format(infile, line))

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
        print("ERROR  Can't get list of known remotes.  Have you run rclone config?"); exit()
    except:
        print("ERROR  rclone not installed?\nError message: {}\n".format(sys.exc_info()[1])); exit()
    clouds = str(clouds.decode("utf8")).split()

    parser = argparse.ArgumentParser(description="***** BiDirectional Sync for Cloud Services using rclone *****")
    parser.add_argument('Cloud',
                        help="Name of remote cloud service ({}) plus optional path.".format(clouds))
    parser.add_argument('LocalPath',
                        help="Path to local tree base.")
    parser.add_argument('-1', '--first-sync',
                        help="First run setup.  WARNING: Local files may overwrite Remote versions.  Consider using --dry-run.  Also asserts --verbose.",
                        action='store_true')
    parser.add_argument('-c', '--check-access',
                        help="Ensure expected RCLONE_TEST files are found on both Local and Remote filesystems, else abort.",
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
    local_wd     =  args.workdir + '/'

    if not args.no_datetime_log:
        logging.basicConfig(format='%(asctime)s:  %(message)s') # /%(levelname)s/%(module)s/%(funcName)s
    else:
        logging.basicConfig(format='%(message)s')

    logging.warning("***** BiDirectional Sync for Cloud Services using rclone *****")

    REMOTE_FORMAT = re.compile('([\w-]+):(.*)')                 # Handle variations in the Cloud argument -- Remote: or Remote:some/path or Remote:/some/path
    out = REMOTE_FORMAT.match(args.Cloud)
    remote_name = remote_path_part = remote_path_base = ''
    if out:
        remote_name = out.group(1) + ':'
        if remote_name not in clouds:
            logging.error("ERROR  Cloud argument <{}> not in list of configured remotes: {}".format(remote_name, clouds)); exit()
        remote_path_part = out.group(2)
        if remote_path_part != '':
            if remote_path_part[0] != '/':
                remote_path_part = '/' + remote_path_part       # For consistency ensure the path part starts and ends with /'s
            if remote_path_part[-1] != '/':
                remote_path_part += '/'
        remote_path_base = remote_name + remote_path_part       # 'Remote:' or 'Remote:/some/path/'
    else:
        logging.error("ERROR  Cloud parameter <{}> cannot be parsed. ':' missing?  Configured remotes: {}".format(args.Cloud, clouds)); exit()


    local_path_base = args.LocalPath
    if local_path_base[-1] != '/':                              # For consistency ensure the path ends with /
        local_path_base += '/'
    if not os.path.exists(local_path_base):
        logging.error("ERROR  LocalPath parameter <{}> cannot be accessed.  Path error?  Aborting".format(local_path_base)); exit()


    if verbose or rc_verbose>0 or force or first_sync or dry_run:
        verbose = True
        logging.getLogger().setLevel(logging.INFO)              # Log each file transaction
    else:
        logging.getLogger().setLevel(logging.WARNING)           # Log only unusual events


    if request_lock(sys.argv) == 0:
        status = bidirSync()
        if status == RTN_CRITICAL:
            logging.error("***** Critical Error Abort - Must run --first-sync to recover.  See README.md *****\n")
            if os.path.exists(local_list_file):
                subprocess.call(['mv', local_list_file, local_list_file + '_ERROR'])
            if os.path.exists(remote_list_file):
                subprocess.call(['mv', remote_list_file, remote_list_file + '_ERROR'])
        if status == RTN_ABORT:
            logging.error("***** Error Abort.  Try running rclonesync again. *****\n")
        if status == 0:            
            logging.warning(">>>>> Successful run.  All done.\n")
        release_lock(sys.argv)
    else:  logging.warning("***** Prior lock file in place, aborting.  Try running rclonesync again. *****\n")

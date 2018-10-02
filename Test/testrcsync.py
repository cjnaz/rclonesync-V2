#!/usr/bin/env python
"""Test engine for rclonesync test cases
Test cases are organized in subdirs beneath ./tests.
Results are compared against golden LSL files and the rclonesync log file.

Example for running all tests with output directed to a log file:
    ./testrcsync.py local GDrive: ALL > runlog.txt 2>&1
"""

version = "V1.2 181001"

# Revision history
# 181001  Add support for path to rclone
# 180729  Rework for rclonesync Path1/Path2 changes.  Added optional path to rclonesync.py.
# 180701  New

# Todos
#   none


import argparse
import sys
import re
import os.path
import os
import subprocess
import shutil
import filecmp

RCSEXEC = "../rclonesync.py"
LOCALTESTBASE = "./"
TESTDIR = "testdir/"
WORKDIR = "./testwd" + "/"
CONSOLELOGFILE = WORKDIR + "consolelog.txt"

def rcstest():
    path1 = path1base + TESTDIR + "path1/"
    path2 = path2base + TESTDIR + "path2/"
    print ("***** Test case <{}> using Path1 <{}>, Path2 <{}>, <{}>, and <{}>"
           .format(testcase, path1, path2, rcsexec, rclone))

    TESTCASEROOT = "./tests/" + testcase + "/"
    INITIALDIR   = TESTCASEROOT + "initial/"
    MODFILESDIR  = TESTCASEROOT + "modfiles/"
    GOLDENDIR    = TESTCASEROOT + "golden/"
    CHANGECMDS   = TESTCASEROOT + "/ChangeCmds.txt"         # File of commands for changes from initial setup state for a test
    SYNCCMD      = TESTCASEROOT + "/SyncCmds.txt"           # File of rclonesync (and other) commands

    print ("CLEAN UP any remnant test content and SET UP the INITIAL STATE on both Path1 and Path2")
    if os.path.exists(WORKDIR):
        shutil.rmtree(WORKDIR)
    os.mkdir(WORKDIR)

    testdirpath1 = TESTDIR + "path1/"
    if testdirpath1 in subprocess.check_output([rclone, "lsf", path1base, "-R"]).decode("utf8"):
        subprocess.call([rclone, "purge", path1])
    
    # git tends to change file mod dates.  For test stability, jam initial dates to a fix past date.
    # test cases that changes files (test_changes, for example) will touch specific files to fixed new dates.
    subprocess.call("find " + INITIALDIR + r' -type f -exec touch --date="2000-01-01" {} +', shell=True)

    subprocess.call([rclone, "copy", INITIALDIR, path1])
    subprocess.call([rclone, "sync", path1, path2])
    sys.stdout.flush()                                      # Force alignment of stdout and stderr in redirected output file.
    
    print ("\nDO <rclonesync --first-sync> to set LSL files baseline")
    subprocess.call([rcsexec, path1, path2, "--first-sync", "--workdir", WORKDIR,
                     "--no-datetime-log", "--rclone", rclone ])
    sys.stdout.flush()
    

    print ("RUN CHANGECMDS to apply changes from test case initial state")
    with open(CHANGECMDS) as ifile:
        for line in ifile:
            line = line[0:line.find('#')].lstrip().rstrip() # Throw away comment and any leading & trailing whitespace.
            if len(line) > 0:
                if ":MSG:" in line:
                    print ("    {}".format(line))
                else:
                    if ":RCSEXEC:" in line:
                        line += " --verbose --workdir :WORKDIR: --no-datetime-log --rclone :RCLONE:"
                    xx = line \
                         .replace(":TESTCASEROOT:", TESTCASEROOT) \
                         .replace(":PATH1:", path1) \
                         .replace(":PATH2:", path2) \
                         .replace(":RCSEXEC:", rcsexec) \
                         .replace(":RCLONE:", rclone) \
                         .replace(":WORKDIR:", WORKDIR)
                    print ("    {}".format(xx))
                    subprocess.call(xx, shell=True) # using shell=True so that touch commands can have quoted date strings
                sys.stdout.flush()


    print ("\nRUN SYNCCMDS (console output captured to consolelog.txt)")
    with open(CONSOLELOGFILE, "w") as logfile:
        with open(SYNCCMD) as ifile:
            for line in ifile:
                line = line[0:line.find('#')].lstrip().rstrip()
                if len(line) > 0:
                    if ":MSG:" in line:
                        print ("    {}".format(line))
                        subprocess.call(["echo", line], stdout=logfile, stderr=logfile)
                    else:
                        if ":RCSEXEC:" in line:
                            line += " --verbose --workdir :WORKDIR: --no-datetime-log --rclone :RCLONE:"
                        xx = line \
                            .replace(":TESTCASEROOT:", TESTCASEROOT) \
                            .replace(":PATH1:", path1) \
                            .replace(":PATH2:", path2) \
                            .replace(":RCSEXEC:", rcsexec) \
                            .replace(":RCLONE:", rclone) \
                            .replace(":WORKDIR:", WORKDIR)
                        print ("    {}".format(xx))
                        subprocess.call("echo " + xx, stdout=logfile, stderr=logfile, shell=True)
                        subprocess.call(xx, stdout=logfile, stderr=logfile, shell=True)
                    sys.stdout.flush()


    errcnt = 0
    if args.golden:
        print ("\nCopying run results to the testcase golden directory")
        if os.path.exists(GOLDENDIR):
            shutil.rmtree(GOLDENDIR)
        shutil.copytree(WORKDIR, GOLDENDIR)
    else:
        print ("\nCOMPARE RESULTS files to the testcase golden directory")
        goldenfiles =  os.listdir(GOLDENDIR)
        resultsfiles = os.listdir(WORKDIR)
        sys.stdout.flush()

        print ("----------------------------------------------------------")
        if len(goldenfiles) != len(resultsfiles):
            print ("MISCOMPARE - Number of Golden and Results files do notmatch:")
            print ("  Golden  count {}: {}".format(len(goldenfiles),  goldenfiles))
            print ("  Results count {}: {}".format(len(resultsfiles), resultsfiles))
        else:
            print ("Number of results files ({}) match".format(len(goldenfiles)))
        for xx in goldenfiles:
            if xx not in resultsfiles:
                errcnt += 1
                print ("File found in Golden but not in Results:  <{}>".format(xx))
        for xx in resultsfiles:
            if xx not in goldenfiles:
                errcnt += 1
                print ("File found in Results but not in Golden:  <{}>".format(xx))

        for xx in goldenfiles:
            if xx in resultsfiles:
                print ("\n----------------------------------------------------------")
                if filecmp.cmp (GOLDENDIR + xx, WORKDIR + xx):
                    print ("Match:  <{}>".format(xx))
                else:
                    if xx in resultsfiles:
                        errcnt += 1
                        print ("MISCOMPARE  < Golden  to  > Results  for:  <{}>".format(xx))
                        sys.stdout.flush()
                        subprocess.call(["diff", GOLDENDIR + xx, WORKDIR + xx ])
                sys.stdout.flush()

        print ("\n----------------------------------------------------------")


    if args.no_cleanup:
        print ("SKIPPING CLEANUP of testdirs and workdir")
    else:
        print ("CLEANING UP testdirs and workdir")
        subprocess.call([rclone, "purge", path1])
        subprocess.call([rclone, "purge", path2])
        shutil.rmtree(WORKDIR)


    if errcnt > 0:
        print ("TEST <{}> FAILED WITH {} ERRORS.\n\n".format(testcase, errcnt))
    else:
        print ("TEST <{}> PASSED\n\n".format(testcase))
    sys.stdout.flush()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="rclonesync test engine")
    parser.add_argument('Path1',
                        help="'local' or name of cloud service with ':'")
    parser.add_argument('Path2',
                        help="'local' or name of cloud service with ':'")
    parser.add_argument('TestCase',
                        help="Test case subdir name (beneath ./tests).  'ALL' to run all tests in the tests subdir")
    parser.add_argument('-g', '--golden',
                        help="Capture output and place in testcase golden subdir",
                        action='store_true')
    parser.add_argument('--no-cleanup',
                        help="Disable cleanup of Path1 and Path2 testdirs.  Useful for debug.",
                        action='store_true')
    parser.add_argument('--rclonesync',
                        help="Full or relative path to rclonesync Python file (default <{}>).".format(RCSEXEC),
                        default=RCSEXEC)
    parser.add_argument('-r','--rclone',
                        help="Full path to rclone executable (default is rclone in path)",
                        default="rclone")
    parser.add_argument('-V', '--version',
                        help="Return version number and exit.",
                        action='version',
                        version='%(prog)s ' + version)
    
    args = parser.parse_args()
    testcase = args.TestCase
    rcsexec  = args.rclonesync
    rclone   =  args.rclone
    
    try:
        clouds = subprocess.check_output([rclone, 'listremotes'])
    except subprocess.CalledProcessError as e:
        print ("ERROR  Can't get list of known remotes.  Have you run rclone config?"); exit()
    except:
        print ("ERROR  rclone not installed, or invalid --rclone path?\nError message: {}\n".format(sys.exc_info()[1])); exit()
    clouds = str(clouds.decode("utf8")).split()

    remoteFormat = re.compile('([\w-]+):(.*)')
    if args.Path1 == "local":
        path1base = LOCALTESTBASE
    else:
        out = remoteFormat.match(args.Path1)
        if out:
            path1base = out.group(1) + ':'
            if path1base not in clouds:
                print ("ERROR  Path1 parameter <{}> not in list of configured remotes: {}".format(path1base, clouds)); exit()
        else:
            print ("ERROR  Path1 parameter <{}> cannot be parsed. ':' missing?  Configured remotes: {}".format(args.Path1, clouds)); exit()

    if args.Path2 == "local":
        path2base = LOCALTESTBASE
    else:
        out = remoteFormat.match(args.Path2)
        if out:
            path2base = out.group(1) + ':'
            if path2base not in clouds:
                print ("ERROR  Path2 parameter <{}> not in list of configured remotes: {}".format(path2base, clouds)); exit()
        else:
            print ("ERROR  Path2 parameter <{}> cannot be parsed. ':' missing?  Configured remotes: {}".format(args.Path2, clouds)); exit()


    if testcase != "ALL":
        if os.path.exists("./tests/" + testcase):
            rcstest()
        else:
            print ("ERROR  TestCase directory <{}> not found".format(testcase)); exit()
    else:
        for directory in os.listdir("./tests"):
            print ("===================================================================")
            testcase = directory
            rcstest()

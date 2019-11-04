#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals  # This sets py2.7 default string literal to unicode from str.  No 'u' required on strings.
from __future__ import print_function    # This redefined print as a function, as in py3.  Forces writing compatible code.
"""Test engine for rclonesync test cases
Test cases are organized in subdirs beneath ./tests.
Results are compared against golden LSL files and the rclonesync log file.

Example for running all tests with output directed to a log file:
    ./testrcsync.py local GDrive: ALL > runlog.txt 2>&1
"""



version = "V1.6 191103"

# Revision history
# V1.6 191103  Unicode enhancements, including on the rclonesync command line
# V1.5 191003  Force sorted order of ALL testcases.  Force sorted order of 
#   results compare.  Deleted --config switch for Windows testing.  Fixed cleanup bug.
# V1.4 190408  Added --config switch and support for --rclone-args switches in ChangeCmds and SyncCmds rclonesync calls.
# V1.3 190330  Added hook for running tests with Windows.  See README.md.
# V1.2 181001  Add support for path to rclone
# V1.1 180729  Rework for rclonesync Path1/Path2 changes.  Added optional path to rclonesync.py.
# V1.0 180701  New

# Todos
#   sym links are not supported.


import argparse
import sys
import io
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
    # MODFILESDIR  = TESTCASEROOT + "modfiles/"
    GOLDENDIR    = TESTCASEROOT + "golden/"
    CHANGECMDS   = TESTCASEROOT + "/ChangeCmds.txt"         # File of commands for changes from initial setup state for a test
    SYNCCMD      = TESTCASEROOT + "/SyncCmds.txt"           # File of rclonesync (and other) commands

    print ("CLEAN UP any remnant test content and SET UP the INITIAL STATE on both Path1 and Path2")
    # subprocess.call([rclone, "purge", path1, "--config", rcconfig])
    # subprocess.call([rclone, "purge", path2, "--config", rcconfig])
    if os.path.exists(WORKDIR):
        shutil.rmtree(WORKDIR)
    os.mkdir(WORKDIR)

    # testdirpath1 = TESTDIR + "path1/"
    # try:
    #     subprocess.Popen([rclone, "purge", path1, "--config", rcconfig ], stdout=devnull, stderr=devnull)
    # except:
    #     pass
    FNULL = open(os.devnull, 'w')
    # subprocess.call(['echo', 'foo'], stdout=FNULL, stderr=subprocess.STDOUT)
    subprocess.call([rclone, "purge", path1, "--config", rcconfig ], stdout=FNULL, stderr=FNULL)
    subprocess.call([rclone, "purge", path2, "--config", rcconfig ], stdout=FNULL, stderr=FNULL)

    # raw_input ("Hello")


    # git tends to change file mod dates.  For test stability, jam initial dates to a fix past date.
    # test cases that changes files (test_changes, for example) will touch specific files to fixed new dates.
    subprocess.call("find " + INITIALDIR + r' -type f -exec touch --date="2000-01-01" {} +', shell=True)

    subprocess.call([rclone, "copy", INITIALDIR, path1, "--config", rcconfig])
    subprocess.call([rclone, "sync", path1, path2, "--config", rcconfig])
    sys.stdout.flush()                                      # Force alignment of stdout and stderr in redirected output file.
    # raw_input ("hello")
    print ("\nDO <rclonesync --first-sync> to set LSL files baseline")
    subprocess.call([rcsexec, path1, path2, "--first-sync", "--workdir", WORKDIR,
                     "--no-datetime-log", "--rclone", rclone, "--config", rcconfig])
    sys.stdout.flush()
    # raw_input ("hello")
    
    

    print ("RUN CHANGECMDS to apply changes from test case initial state")
        # with io.open(file, mode='rt', encoding='utf8',errors="replace") as inf:   # use io.open for unicode support (??)

    with io.open(CHANGECMDS, mode='rt', encoding='utf8', errors="replace") as ifile:
        for line in ifile:
            line = line[0:line.find('#')].lstrip().rstrip() # Throw away comment and any leading & trailing whitespace.
            if len(line) > 0:
                if ":MSG:" in line:
                    print ("    {}".format(line))
                else:
                    if ":RCSEXEC:" in line:
                        _line = line.split()    # Move any --rclone-args after additional switches
                        beginning = _line
                        rcargs = []
                        if "--rclone-args" in line:
                            rclone_args_index = _line.index("--rclone-args")
                            beginning = _line[0:rclone_args_index]
                            rcargs = _line[rclone_args_index:]
                        line = " ".join (beginning + [" --verbose --workdir :WORKDIR: --no-datetime-log --rclone :RCLONE: --config", rcconfig] + rcargs)
                    # if ":RCSEXEC:" in line:
                    #     line += " --verbose --workdir :WORKDIR: --no-datetime-log --rclone :RCLONE: --config " + rcconfig
                    #     # if args.config is not None:
                    #     #     line += "--config" + args.config
                    xx = line \
                         .replace(":/", ":") \
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
    with io.open(CONSOLELOGFILE, mode="wt", encoding="utf8") as logfile:
        with io.open(SYNCCMD, mode="rt", encoding='utf8', errors="replace") as ifile:
            for line in ifile:
                line = line[0:line.find('#')].lstrip().rstrip()
                sys.stdout.flush()
                sys.stderr.flush()
                if len(line) > 0:
                    if ":MSG:" in line:
                        print ("    {}".format(line))
                        subprocess.call(["echo", line], stdout=logfile, stderr=logfile)
                    else:
                        if ":RCSEXEC:" in line:
                            _line = line.split()    # Move any --rclone-args after additional switches
                            beginning = _line
                            rcargs = []
                            if "--rclone-args" in line:
                                rclone_args_index = _line.index("--rclone-args")
                                beginning = _line[0:rclone_args_index]
                                rcargs = _line[rclone_args_index:]
                            line = " ".join (beginning + [" --verbose --workdir :WORKDIR: --no-datetime-log --rclone :RCLONE: --config", rcconfig] + rcargs)
                        xx = line \
                            .replace(":/", ":") \
                            .replace(":TESTCASEROOT:", TESTCASEROOT) \
                            .replace(":PATH1:", path1) \
                            .replace(":PATH2:", path2) \
                            .replace(":RCSEXEC:", rcsexec) \
                            .replace(":RCLONE:", rclone) \
                            .replace(":WORKDIR:", WORKDIR)
                        subprocess.call("echo " + xx, stdout=logfile, stderr=logfile, shell=True)
                        sys.stdout.flush()
                        sys.stderr.flush()
                        if args.Windows_testing and ":RCSEXEC:" in line:
                            xx = xx.replace("--config","").replace(rcconfig,"").replace('/','\\')     # Must use Windows-side user default config file
                            print ("    {}".format(xx))
                            # os.remove("wincmd.bat")
                            with io.open("wincmd.bat", mode='wt', encoding='utf-8') as wincmd_bat:
                                # print ("    {} >> {} 2>&1".format(xx.replace('/','\\'), CONSOLELOGFILE.replace('/','\\')))
                                # wincmd_bat.write("    {} >> {} 2>&1".format(xx, CONSOLELOGFILE.replace('/','\\')))
                                wincmd_bat.write("    {} >> {} 2>&1 & del wincmd.bat".format(xx, CONSOLELOGFILE.replace('/','\\')))
                                wincmd_bat.flush()
                                os.fsync(wincmd_bat.fileno())
                            # subprocess.call("cat wincmd.bat", shell=True)
                            if sys.version_info[0] < 3:
                                # raw_input("Hit return after entering above on Windows side. >>")
                                raw_input("Hit return after running <wincmd.bat> on Windows side. >>")
                            else:
                                # input("Hit return after entering above on Windows side. >>")
                                input("Hit return after running <wincmd.bat> on Windows side. >>")
                        else:
                            print ("    {}".format(xx))
                            subprocess.call(xx, stdout=logfile, stderr=logfile, shell=True)
                    sys.stdout.flush()

    if os.path.exists(WORKDIR + "deleteme.txt"):    # Remnant from Windows and Python2.7
        os.remove (WORKDIR + "deleteme.txt")        # Delete it so that it doesn't mess up the file compare.

    errcnt = 0
    if args.golden:
        print ("\nCopying run results to the testcase golden directory")
        if os.path.exists(GOLDENDIR):
            shutil.rmtree(GOLDENDIR)
        shutil.copytree(WORKDIR, GOLDENDIR)
    else:
        print ("\nCOMPARE RESULTS files to the testcase golden directory")

        def files_list(dirlist):
            xxx = ""
            for file in dirlist:
                xxx += file + ', '
                # xxx += file.decode('utf-8') + ', '
            return xxx[:-2]

        goldenfiles =  sorted(os.listdir(GOLDENDIR))
        resultsfiles = sorted(os.listdir(WORKDIR))
        sys.stdout.flush()

        print ("----------------------------------------------------------")
        if len(goldenfiles) != len(resultsfiles):
            print ("MISCOMPARE - Number of Golden and Results files do notmatch:")
            print ("  Golden  count {}: {}".format(len(goldenfiles),  files_list(goldenfiles)))
            print ("  Results count {}: {}".format(len(resultsfiles), files_list(resultsfiles)))
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

        if args.Windows_testing:
            # hack the test result consolelog.txt, swapping to Linux-style slashes
            with io.open(CONSOLELOGFILE, encoding='utf-8') as f:
                s = f.read()
            s = s.replace("\\\\", "/")
            s = s.replace("\\", "/")
            with io.open(CONSOLELOGFILE, "w", encoding='utf-8') as f:
                f.write(s)

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
        subprocess.call([rclone, "purge", path1, "--config", rcconfig])
        subprocess.call([rclone, "purge", path2, "--config", rcconfig])
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
    parser.add_argument('--Windows-testing',
                        help="Disable running rclonesyncs during the SyncCmds phase.  Used for Windows testing.",
                        action='store_true')
    parser.add_argument('--rclonesync',
                        help="Full or relative path to rclonesync Python file (default <{}>).".format(RCSEXEC),
                        default=RCSEXEC)
    parser.add_argument('-r','--rclone',
                        help="Path to rclone executable (default is rclone in path environment var).",
                        default="rclone")
    parser.add_argument('--config',
                        help="Path to rclone config file (default is typically ~/.config/rclone/rclone.conf).",
                        default=None)
    parser.add_argument('-V', '--version',
                        help="Return version number and exit.",
                        action='version',
                        version='%(prog)s ' + version)
    
    args = parser.parse_args()
    testcase = args.TestCase
    rcsexec  = args.rclonesync
    rclone   = args.rclone

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
        print ("ERROR  Can't get list of known remotes.  Have you run rclone config?"); exit()
    except:
        print ("ERROR  rclone not installed, or invalid --rclone path?\nError message: {}\n".format(sys.exc_info()[1])); exit()

    remoteFormat = re.compile(r'([\w-]+):(.*)')
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
        for directory in sorted(os.listdir("./tests")):
            print ("===================================================================")
            testcase = directory
            rcstest()

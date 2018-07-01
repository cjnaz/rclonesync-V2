#!/usr/bin/env python
"""Test engine for rclonesync test cases
Test cases are organized in subdirs beneath ./tests.
Results are compared against golden LSL files and the rclonesync log file.

Example, for running all tests with output directed to a log file:
    ./testrcsync.py GDrive: ALL > runlog.txt 2>&1
"""

version = "V1.0 180701"

# Revision history
# 180701  New

# Todo
#   None



import argparse
import sys
import re
import os.path
import os
import subprocess
import shutil
import filecmp

def rcstest():
    print ("***** Test case <{}> on cloud <{}>".format(testcase, cloud))

    TESTDIR = "testdir"

    LOCALTESTDIR = "./" + TESTDIR
    CLOUDTESTDIR = cloud + '/' + TESTDIR
    WORKDIR = "./testwd" + "/"
    RCSEXEC = "../rclonesync.py"
    CONSOLELOGFILE = WORKDIR + "consolelog.txt"

    TESTCASEROOT = "./tests/" + testcase + "/"

    INITIALDIR   = TESTCASEROOT + "initial/"
    MODFILESDIR  = TESTCASEROOT + "modfiles/"
    GOLDENDIR    = TESTCASEROOT + "golden/"

    CHANGECMDS = TESTCASEROOT + "/ChangeCmds.txt"   # File of commands for changes from initial setup state for a test
    SYNCCMD = TESTCASEROOT + "/SyncCmds.txt"        # File of rclonesync command


    print ("CLEAN UP any remnant test content and SET UP the INITIAL STATE on both Local and Remote")
    if os.path.exists(WORKDIR):
        shutil.rmtree(WORKDIR)
    os.mkdir(WORKDIR)

    if os.path.exists(LOCALTESTDIR):
        shutil.rmtree(LOCALTESTDIR)
    sys.stdout.flush()                              # Flush to align stdout and stderr to a redirected output file.
    
    #shutil.copytree(INITIALDIR, LOCALTESTDIR)      # Changed to cp since Python 2.7 copytree changed timestamp (truncated to 1us resolution)
    subprocess.call(["cp", INITIALDIR, LOCALTESTDIR, "-rp"])
    subprocess.call(["rclone", "sync", LOCALTESTDIR, CLOUDTESTDIR])     # Sync completely replaces the Cloud with the Local content
    sys.stdout.flush()
    

    print ("\nDO RCLONESYNC --FIRST-SYNC to set LSL files baseline")
    subprocess.call([RCSEXEC, CLOUDTESTDIR, LOCALTESTDIR, "--first-sync", "--workdir", WORKDIR, "--no-datetime-log" ])
    sys.stdout.flush()
    

    print ("RUN CHANGECMDS to appy changes from test case initial state")
    with open(CHANGECMDS) as ifile:
        for line in ifile:
            line = line[0:line.find('#')].lstrip().rstrip() # throw away comment and any leading & trailing whitespace
            if len(line) > 0:
                if ":MSG:" in line:
                    print ("    {}".format(line))
                else:
                    xx = line \
                         .replace(":TESTCASEROOT:", TESTCASEROOT) \
                         .replace(":LOCALTESTDIR:", LOCALTESTDIR) \
                         .replace(":CLOUDTESTDIR:", CLOUDTESTDIR) \
                         .replace(":RCSEXEC:", RCSEXEC) \
                         .replace(":WORKDIR:", WORKDIR) \
                         .replace(":CLOUD:", cloud) \
                         .split()
                    print ("    {}".format(xx))
                    subprocess.call(xx) #, stdout=logfile, stderr=logfile)
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
                        xx = line \
                             .replace(":TESTCASEROOT:", TESTCASEROOT) \
                             .replace(":LOCALTESTDIR:", LOCALTESTDIR) \
                             .replace(":CLOUDTESTDIR:", CLOUDTESTDIR) \
                             .replace(":RCSEXEC:", RCSEXEC) \
                             .replace(":WORKDIR:", WORKDIR) \
                             .replace(":CLOUD:", cloud) \
                             .split()
                        print ("    {}".format(xx))
                        subprocess.call(xx, stdout=logfile, stderr=logfile)
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
                        print ("MISCOMPARE  < Golden  to  Results > for:  <{}>".format(xx))
                        sys.stdout.flush()
                        subprocess.call(["diff", GOLDENDIR + xx, WORKDIR + xx ])
                sys.stdout.flush()

        print ("\n----------------------------------------------------------")


    if args.no_cleanup:
        print ("SKIPPING CLEANING UP of Local and Remote testdirs")
    else:
        print ("CLEANING UP Local and Remote testdirs")
        if os.path.exists(LOCALTESTDIR):
            shutil.rmtree(LOCALTESTDIR)
        subprocess.call(["rclone", "purge", CLOUDTESTDIR])

    if errcnt > 0:
        print ("TEST <{}> FAILED WITH {} ERRORS.\n\n".format(testcase, errcnt))
    else:
        print ("TEST <{}> PASSED\n\n".format(testcase))
    sys.stdout.flush()

    


if __name__ == '__main__':

    try:                        # Get known Clouds
        clouds = subprocess.check_output(['rclone', 'listremotes'])
    except subprocess.CalledProcessError as e:
        logging.error ("ERROR  Can't get list of known remotes.  Have you run rclone config?"); exit()
    except:
        logging.error ("ERROR  rclone not installed?\nError message: {}\n".format(sys.exc_info()[1])); exit()

    clouds = str(clouds.decode("utf8")).split()

    parser = argparse.ArgumentParser(description="rclonesync test engine")
    parser.add_argument('Cloud',
                        help="Name of remote cloud service ({}) plus optional path".format(clouds))
    parser.add_argument('TestCase',
                        help="Test case subdir name (beneath ./tests).  ALL to run all tests in the tests subdir")
    parser.add_argument('-g', '--golden',
                        help="Capture output and place in testcase golden subdir",
                        action='store_true')
    parser.add_argument('--no-cleanup',
                        help="Disable cleanup of Local and Remote testdirs.  Useful for debug.",
                        action='store_true')
    parser.add_argument('-V', '--version',
                        help="Return version number and exit.",
                        action='version',
                        version='%(prog)s ' + version)
    
    args = parser.parse_args()
    testcase = args.TestCase
    
    remoteFormat = re.compile('([\w-]+):(.*)')      # Handle variations in the Cloud argument -- Remote: or Remote:some/path or Remote:/some/path
    out = remoteFormat.match(args.Cloud)
    cloud = remoteName = remotePathPart = remotePathBase = ''
    if out:
        cloud = out.group(1) + ':'
        if cloud not in clouds:
            print ("ERROR  Cloud argument <{}> not in list of configured remotes: {}".format(cloud, clouds)); exit()
    else:
        print ("ERROR  Cloud parameter <{}> cannot be parsed. ':' missing?  Configured remotes: {}".format(args.Cloud, clouds)); exit()


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


# testrcsync for testing rclonesync

rclonesync is difficult to test manually due to the volume of verbose output log data, the number of scenarios, and the 
relatively long runtime.  testrcsync.py provides a testing framework for rlconesync.  A series of tests are stored in
directories below the `tests` directory beneath this script.  Individual tests are invoked by their
directory name, such as `./testrcsync.py GDrive: test_basic`

Note that the focus of the tests is on rclonesync.py, not rclone itself.  If during the execution of a test there are
intermittent errors and rclone retries, then these errors will be captured and flagged as an invalid MISCOMPARE.  Rerunning the 
test should allow it to pass.  Consider such failures as noise.

## Usage
`./testrcsync.py GDrive: test_basic` runs the test_basic test case.  Test script output is to the console, while commands within
SyncCmds.txt have their output sent to the `.testwd/consolelog.txt` file, which is finally compared to the golden copy.
`.testrcsync.py GDrive: ALL` runs all tests.  Test run stdout and stderr console output may be directed to a file, eg 
`.testrcsync.py GDrive: ALL > runlog.txt 2>&1`.  The `--golden` switch will store the console and ...LSL files from each test 
into the respective testcase golden directories.  Check carefully that you are not saving bad test results as golden!
```
$ ./testrcsync.py -h
usage: testrcsync.py [-h] [-g] [--no-cleanup] [-V] Cloud TestCase

rclonesync test engine

positional arguments:
  Cloud          Name of remote cloud service (['Dropbox:', 'GDrive:']) plus
                 optional path
  TestCase       Test case subdir name (beneath ./tests). ALL to run all tests
                 in the tests subdir

optional arguments:
  -h, --help     show this help message and exit
  -g, --golden   Capture output and place in testcase golden subdir
  --no-cleanup   Disable cleanup of Local and Remote testdirs. Useful for
                 debug.
  -V, --version  Return version number and exit.
```
Note that the testcase `test_dry_run` will produce a mismatch for the consolelog.txt file because this test captures rclone --dry-run
info messages that have timestamps that will mismatch to the golden consolelog.txt.  This is the only expected failure.

## Test execution flow:
1. The base setup in the `initial` directory of the test case is applied on the Local and Remote file systems, and a rclonesync 
--first-sync is run to establish the baseline __remoteLSL and __llocalLSL files in the test working directory 
(./testwd/ relative to the testrcsync.py directory).
2. The commands in the ChangeCmds.txt file are applied.  This establishes deltas from the initial sync in step 1.
3. The commands in the SyncCmds.txt file are applied, with output directed to the consolelog.txt file in the test working directory.
4. The contents of the test working directory are compared to the contents of the test case golden directory.


## Setup notes
- rclonesync.py is invoked in the directory above testrcsync.py (testrcsync.py must be in a directory below rclonesync.py).
- Test cases are in individual directories beneath ./tests (relative to the testrcsync.py directory).  A command line reference to a test 
is understood to reference a directory beneath ./tests.  Eg, `./testrcsync.py GDrive: test_basic` refers to the test case in 
`./tests/test_basic`.
- The temporary test working directory is located at `./testwd` (relative to the testrcsync.py directory).
- The temporary Local sync tree is located at `./testdir` (relative to the testrcsync.py directory).
- The temporary Remote sync tree is located at `<Cloud:>/testdir`.  An optional cloud path is supported.
- By default, the Local and Remote testdir will be deleted after each test run.  The `--no-cleanup` switch disables purging the
testdirs when validating and debugging a given test.  These directories will be flushed when running another test, independent of 
`--no-cleanup` usage.
- You will likely want to add `- /testdir/**` to the rclonesync `--filters-file` so that normal syncs do not attempt to sync the test 
run temporary 
directories, which may have RCLONE_TEST miscompares in some test cases and would otherwise trip the `--check-access` system. 
rclonesync's check-access
mechanism is hard-coded to ignore RCLONE_TEST files beneath rclonesync/Test, so the test cases may reside on the sync'd tree even if
there are transient RCLONE_TEST mismatches beneath /Test.


## Each test is organized as follows:
- `<testname>/initial/` contains a tree of files that will be set as the initial condition on both Local and Remote testdirs.
- `<testname>/modfiles/` contains files that will be pushed into the Local and/or Remote filesystems by the ChangeCmds.txt file
as the purpose of the test.
- `<testname>/golden/` contains the expected content of the test working directory (./testwd) at the completion of the test case.
- `<testname>/ChangeCmds.txt` contains the commands to apply change to the Local and/or Remote filesystems as the purpose of the test
- `<testname>/SyncCmds.txt` contains the command(s) to run rclonesync.py to resync the Local and Remote test trees.  Output from
these commands is captured to `./testwd/consolelog.txt` for comparison to the golden files.  Note that commands in this
file are not restricted to rclonesync.py commands.

## ChangeCmds.txt and SyncCmds.txt support several substitution terms:

Keyword| Points to | Example
---|---|---
`:TESTCASEROOT:` | The root dir of the testcase | example follows... 
`:LOCALTESTDIR:` | The root of the test on the Local filesystem | `rclone copy :TESTCASEROOT:/modfiles/file11.txt :LOCALTESTDIR:`
`:CLOUDTESTDIR:` | The root of the test on the Remote filesystem | `rclone copy :TESTCASEROOT:/modfiles/file1.txt :CLOUDTESTDIR:`
`:RCSEXEC:` | References `../rclonesync.py` | example follows...
`:WORKDIR:` | The temporary test working directory | `:RCSEXEC: :CLOUDTESTDIR: :LOCALTESTDIR: --verbose --workdir :WORKDIR: --no-datetime-log`
`:CLOUD:` | The name of the cloud system in use. This shouldn't be needed since `:CLOUD:/testdir` == `:CLOUDTESTDIR:`.  Generally, use :CLOUDTESTDIR:.  | none
`:MSG:` | Print the line to the console and to the consolelog.txt file when processing SyncCmds.txt. | `:MSG: Hello, my name is Fred`

## Parting shots
Developed on CentOS 7 and tested on Python 2.7.x and Python 3.6.5.  Issues echo and diff subprocess commands that surely 
will not work on Windows (sorry).

## Revision history

- V1 180701 New

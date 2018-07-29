
# testrcsync for testing rclonesync

rclonesync is difficult to test manually due to the volume of verbose output log data, the number of scenarios, and the 
relatively long runtime if syncing with a cloud service.
testrcsync.py provides a testing framework for rlconesync.
A series of tests are stored in directories below the `tests` directory beneath this script.
Individual tests are invoked by their directory name, such as `./testrcsync.py local GDrive: test_basic`

Note that the focus of the tests is on rclonesync.py, not rclone itself.  If during the execution of a test there are
intermittent errors and rclone retries, then these errors will be captured and flagged as an invalid MISCOMPARE.  Rerunning the test should allow it to pass.  Consider such failures as noise.

## Usage
- `./testrcsync.py local local test_basic` runs the test_basic test case using only the local filesystem - synching
one local directory with another local directory.
Test script output is to the console, while commands within SyncCmds.txt have their output sent to the `./testwd/consolelog.txt` file, which is finally compared to the golden copy.
- `./testrcsync.py local local ALL` runs all tests.
- Path1 and Path2 may either be the keyword `local` or may be names of configured cloud services.  `./testrcsync.py GDrive: Dropbox: test_basic` will run the test between these two services, without transferring any files to the local filesystem.
- Test run stdout and stderr console output may be directed to a file, eg 
`./testrcsync.py GDrive: local ALL > runlog.txt 2>&1`.
- The `--golden` switch will store the consolelog.txt and <...>__Path*LSL files from each test into the respective testcase golden directories.  Check carefully that you are not saving bad test results as golden!
- NOTE that the golden results contain the local and cloud paths, which means that if the golden results are produced from 
`./testrcsync.py local local ALL --golden`, they will not match when run with a cloud service as with `./testrcsync.py local Dropbox: ALL`. Expected differences:  1) the consolelog.txt will mismatch for Path1/Path2, and 2) rclonesync's produced <...>__Path*LSL filenames incorporate the Path1 and Path2 names.  Manually check the differences, and consider running with `--golden` if a given cloud service is 
your preference.  Running the tests with a cloud service is WAY slower than local local.

```
$ ./testrcsync.py -h
usage: testrcsync.py [-h] [-g] [--no-cleanup] [--rclonesync RCLONESYNC] [-V]
                     Path1 Path2 TestCase

rclonesync test engine

positional arguments:
  Path1                 'local' or name of cloud service (['Dropbox:',
                        'GDrive:', 'gdrive2:'])
  Path2                 'local' or name of cloud service (['Dropbox:',
                        'GDrive:', 'gdrive2:'])
  TestCase              Test case subdir name (beneath ./tests). 'ALL' to run
                        all tests in the tests subdir

optional arguments:
  -h, --help            show this help message and exit
  -g, --golden          Capture output and place in testcase golden subdir
  --no-cleanup          Disable cleanup of Path1 and Path2 testdirs. Useful
                        for debug.
  --rclonesync RCLONESYNC
                        Full or relative path to rclonesync Python file
                        (default <../rclonesync.py>).
  -V, --version         Return version number and exit.

```

## Test execution flow:
1. The base setup in the `initial` directory of the testcase is applied on the Path1 and Path2 filesystems, and a rclonesync 
--first-sync is run to establish the baseline <...>__Path1LSL and <...>__Path2LSL files in the test working directory 
(./testwd/ relative to the testrcsync.py directory).
2. The commands in the ChangeCmds.txt file are applied.  This establishes deltas from the initial sync in step 1.
3. The commands in the SyncCmds.txt file are applied, with output directed to the consolelog.txt file in the test working directory.
4. The contents of the test working directory are compared to the contents of the testcase golden directory.
Note that testcase `test_dry_run` will produce a mismatch for the consolelog.txt file because this test captures rclone --dry-run
info messages that have timestamps that will mismatch to the golden consolelog.txt.  This is the only expected failure.


## Setup notes
- rclonesync.py is by default invoked in the directory above testrcsync.py.  An alternate path to rclonesync.py may be specified with the 
`--rclonesync` switch.
- Test cases are in individual directories beneath ./tests (relative to the testrcsync.py directory).  A command line reference to a test 
is understood to reference a directory beneath ./tests.  Eg, `./testrcsync.py GDrive: local test_basic` refers to the test case in 
`./tests/test_basic`.
- The temporary test working directory is located at `./testwd` (relative to the testrcsync.py directory).
- The temporary local sync tree is located at `./testdir` (relative to the testrcsync.py directory).  
- The temporary cloud sync tree is located at `<cloud:>/testdir`.
- `path1` and/or `path2` subdirectories are created beneath the respective local or cloud testdir.
- By default, the Path1 and Path2 testdirs will be deleted after each test run.  The `--no-cleanup` switch disables purging the
testdirs when validating and debugging a given test.  These directories will be flushed when running another test, independent of 
`--no-cleanup` usage.
- You will likely want to add `- /testdir/**` to the rclonesync `--filters-file` so that normal syncs do not attempt to sync the test 
temporary 
directories, which may have RCLONE_TEST miscompares in some testcases which would otherwise trip the `--check-access` system. 
rclonesync's --check-access
mechanism is hard-coded to ignore RCLONE_TEST files beneath rclonesync/Test, so the testcases may reside on the sync'd tree even if
there are RCLONE_TEST mismatches beneath /Test.


## Each test is organized as follows:
- `<testname>/initial/` contains a tree of files that will be set as the initial condition on both Path1 and Path2 testdirs.
- `<testname>/modfiles/` contains files that will be pushed into the Path1 and/or Path2 filesystems by the ChangeCmds.txt file
as the purpose of the test.
- `<testname>/golden/` contains the expected content of the test working directory (./testwd) at the completion of the testcase.
- `<testname>/ChangeCmds.txt` contains the commands to apply change to the Path1 and/or Path2 filesystems as the purpose of the test.
- `<testname>/SyncCmds.txt` contains the command(s) to run rclonesync.py to resync the Path1 and Path2 test trees.  Output from
these commands is captured to `./testwd/consolelog.txt` for comparison to the golden files.  Note that commands in this
file are not restricted to rclonesync.py commands.

## ChangeCmds.txt and SyncCmds.txt support several substitution terms:

Keyword| Points to | Example
---|---|---
`:TESTCASEROOT:` | The root dir of the testcase | example follows... 
`:PATH1:` | The root of the Path1 test directory tree | `rclone delete :PATH1:subdir/file1.txt`
`:PATH2:` | The root of the Path2 test directory tree | `rclone copy :TESTCASEROOT:modfiles/file11.txt :PATH2:`
`:RCSEXEC:` | References `../rclonesync.py` by default | example follows...
`:WORKDIR:` | The temporary test working directory | `:RCSEXEC: :PATH1: :PATH2: --verbose --workdir :WORKDIR: --no-datetime-log`
`:MSG:` | Print the line to the console and to the consolelog.txt file when processing SyncCmds.txt. | `:MSG: Hello, my name is Fred`

Note that the substituted `:TESTCASEROOT:`, `:PATH1:`, `:PATH2:`, and `:WORKDIR:` terms end with `/`, so it is not necessary to include a slash in the usage. `rclone delete :PATH1:subdir/file1.txt` and `rclone delete :PATH1:/subdir/file1.txt` are functionally equivalent.

## Parting shots
Developed on CentOS 7 and tested on Python 2.7.x and Python 3.6.5.  Issues echo, touch and diff subprocess commands that surely 
will not work on Windows (sorry).

## Revision history
- V1.1 180728 - Rework for rclonesync Path1/Path2 changes.  Added optional path to rclonesync.py.
- V1 180701 New

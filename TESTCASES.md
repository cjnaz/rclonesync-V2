# testrcsync for testing rclonesync

rclonesync is difficult to test manually due to the volume of verbose output log data, the number of scenarios, and the 
relatively long runtime if syncing with a cloud service.
testrcsync.py provides a testing framework for rlconesync.
A series of tests are stored in directories below the `tests` directory beneath this script.
Individual tests are invoked by their directory name, such as `./testrcsync.py local GDrive: test_basic`

Note that the focus of the tests is on rclonesync.py, not rclone itself.  If during the execution of a test there are
intermittent errors and rclone retries, then these errors will be captured and flagged as invalid MISCOMPAREs. 
Rerunning the test should allow it to pass.  Consider such failures as noise.

Note also that testrcsync _only_ works on Linux, and does not fully support Windows (see below).

## Usage
- `./testrcsync.py local local test_basic` runs the test_basic test case using only the local filesystem - synching
one local directory with another local directory.
Test script output is to the console, while commands within SyncCmds.txt have their output sent to the `./testwd/consolelog.txt` 
file, which is finally compared to the golden copy.
- `./testrcsync.py local local ALL` runs all tests.
- Path1 and Path2 may either be the keyword `local` or may be names of configured cloud services. 
`./testrcsync.py GDrive: Dropbox: test_basic` will run the test between these two services, without transferring any 
files to the local filesystem.
- Test run stdout and stderr console output may be directed to a file, eg 
`./testrcsync.py GDrive: local ALL > runlog.txt 2>&1`.
- The `--golden` switch will store the consolelog.txt and LSL* files from each test into the respective testcase golden 
directories.  Check carefully that you are not saving bad test results as golden!
- NOTE that the golden results contain the local and cloud paths, which means that if the golden results are produced from 
`./testrcsync.py local local ALL --golden`, they will not match when run with a cloud service as with 
`./testrcsync.py local Dropbox: ALL`. Expected differences:  1) the consolelog.txt will mismatch for Path1/Path2, and 2) 
rclonesync's produced LSL* filenames incorporate the Path1 and Path2 names.  Manually check the differences, 
and consider running with `--golden` if a given cloud service is 
your preference.  Running the tests with a cloud service is WAY slower than `local local`.

## Windows usage (limited)
- Testing with Windows is supported by running testrcsync.py from Linux and using the `--Windows-testing` switch.  When set, the script pauses for each rclonesync command in the test's SyncCmds.txt file, and provides a `wincmd.bat` Windows batch file to be run in a Windows Cmd terminal window.  After all sync commands have been applied, testrcsync proceeds with the diff checks.
- The assumption/requirement is that both the Linux and Windows systems are sharing the same test directories and working directory.
- There will be differences in Windows vs. Linux path styles which will mismatch with the golden consolelog.txt file.  Other Expected differences in the consolelog.txt include 1) Difference in the command line config setting (`config=None` on Windows), and 2) Difference in the lockfile path.  The LSL* files should match, however.  Beyond Compare may be useful for comparing test versus golden consolelog.txt files.
- With both Linux and Windows writing to the consolelog.txt file, the output gets out of sync and sometimes gets partially clobbered.  This is a known bug in testresync.py.  Various sys.stdout.flush() attempts did not fix the problem - left as a corner case bug.
- The Windows user's default rclone config file (typically at C:\Users\<username>\.conifg\rclone\rclone.conf) will be used.  testrcsync's --config switch value is not printed to the wincmd.bat output.

Testcase test_rclone_args will fail on Windows since the --syslog switch is not supported on rclone Windows.


```
$ ./testrcsync.py -h
usage: testrcsync.py [-h] [-g] [--no-cleanup] [--Windows-testing]
                     [--rclonesync RCLONESYNC] [-r RCLONE] [--config CONFIG]
                     [-V]
                     Path1 Path2 TestCase

rclonesync test engine

positional arguments:
  Path1                 'local' or name of cloud service with ':'
  Path2                 'local' or name of cloud service with ':'
  TestCase              Test case subdir name (beneath ./tests). 'ALL' to run
                        all tests in the tests subdir

optional arguments:
  -h, --help            show this help message and exit
  -g, --golden          Capture output and place in testcase golden subdir
  --no-cleanup          Disable cleanup of Path1 and Path2 testdirs. Useful
                        for debug.
  --Windows-testing     Disable running rclonesyncs during the SyncCmds phase.
                        Used for Windows testing.
  --rclonesync RCLONESYNC
                        Full or relative path to rclonesync Python file
                        (default <../rclonesync.py>).
  -r RCLONE, --rclone RCLONE
                        Path to rclone executable (default is rclone in path
                        environment var).
  --config CONFIG       Path to rclone config file (default is typically
                        ~/.config/rclone/rclone.conf).
  -V, --version         Return version number and exit.
```

## Test execution flow:
1. The base setup in the `initial` directory of the testcase is applied on the Path1 and Path2 filesystems, and a rclonesync 
--first-sync is run to establish the baseline LSL<...>__Path1 and LSL<...>__Path2 files in the test working directory 
(./testwd/ relative to the testrcsync.py directory).
2. The commands in the ChangeCmds.txt file are applied.  This establishes deltas from the initial sync in step 1.
3. The commands in the SyncCmds.txt file are applied, with output directed to the consolelog.txt file in the test working directory.
4. The contents of the test working directory are compared to the contents of the testcase golden directory.
Note that testcase `test_dry_run` may produce mismatches in the consolelog.txt file because this test captures rclone --dry-run info messages and rclone sync is not deterministic in the order that it processes changes. This is the only expected failure.


## Setup notes
- rclonesync.py is by default invoked in the directory above testrcsync.py.  An alternate path to rclonesync.py may be specified with the 
`--rclonesync` switch.
- The rclone executable is by default determined by the path.  An alternate rclone version may be selected with the `--rclone` switch.
- The path to the rclone config file may be specified with the `--config` switch.  This setting will also be passed to rclonesync calls.  (See Windows usage (limited), above.)
- Test cases are in individual directories beneath ./tests (relative to the testrcsync.py directory).  A command line reference to a test 
is understood to reference a directory beneath ./tests.  Eg, `./testrcsync.py GDrive: local test_basic` refers to the test case in 
`./tests/test_basic`.
- The temporary test working directory is located at `./testwd` (relative to the testrcsync.py directory).
- The temporary local sync tree is located at `./testdir` (relative to the testrcsync.py directory).  
- The temporary cloud sync tree is located at `<cloud:>/testdir`.
- `path1` and/or `path2` subdirectories are created beneath the respective local or cloud testdir.
- By default, the Path1 and Path2 testdirs, and the testwd will be deleted after each test run.  The `--no-cleanup` switch disables 
purging these directories when validating and debugging a given test.  These directories will be flushed when running another 
test, independent of `--no-cleanup` usage.
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
`:TESTCASEROOT:` | The root dir of the testcase | examples follows... 
`:PATH1:` | The root of the Path1 test directory tree | `:RCLONE: delete :PATH1:subdir/file1.txt`
`:PATH2:` | The root of the Path2 test directory tree | `:RCLONE: copy :TESTCASEROOT:modfiles/file11.txt :PATH2:`
`:RCSEXEC:` | References `../rclonesync.py` by default.  Sets `--verbose --workdir :WORKDIR: --no-datetime-log` and passes along --rclone | `:RCSEXEC: :PATH1: :PATH2:`
`:RCLONE:` | References the rclone executable from the path environment var be default | examples above and below
`:WORKDIR:` | The temporary test working directory | `:RCLONE: copy :TESTCASEROOT:filtersfile.txt :WORKDIR:`
`:MSG:` | Print the line to the console and to the consolelog.txt file when processing SyncCmds.txt. | `:MSG: Hello, my name is Fred`

Note that the substituted `:TESTCASEROOT:`, `:PATH1:`, `:PATH2:`, and `:WORKDIR:` terms end with `/`, so it is not necessary 
to include a slash in the usage. `rclone delete :PATH1:subdir/file1.txt` and `rclone delete :PATH1:/subdir/file1.txt` 
are functionally equivalent.

**New in V1.4:  `:RCEXEC:` lines may include the `--rclone-args` switch to pass arbitrary switches to rclonesync.** See documentation for rclonesync.

## Parting shots
Developed on CentOS 7 and tested on Python 2.7.x and Python 3.8.0.  Issues echo, touch and diff subprocess commands that surely 
will not work on Windows (see Windows usage, above).

## Revision history
- V1.6 191103 - Unicode enhancements, including on the rclonesync command line
- V1.5 191003 - Force sorted order of ALL testcases.  Force sorted order of results compare.  Deleted --config switch for Windows testing.  Fixed cleanup bug.
- V1.4 190408 - Added --config switch and support for --rclone-args switches in ChangeCmds and SyncCmds rclonesync calls.
- V1.3 190330 - Added limited/partial testing with Windows via `--Windows-testing` switch.
- V1.2 181001 - Added --rclone switch.  Cleaned up SyncCmds syntax with hard-coded `--verbose --workdir :WORKDIR: --no-datetime-log` 
for rclonesync calls.
- V1.1 180728 - Rework for rclonesync Path1/Path2 changes.  Added optional path to rclonesync.py.
- V1 180701 New

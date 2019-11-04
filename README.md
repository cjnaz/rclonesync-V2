# rclonesync - A Bidirectional Cloud Sync Utility using rclone


[Rclone](https://rclone.org/) provides a programmatic building block interface for transferring files between a cloud service 
provider and your local filesystem (actually a lot of functionality), but _rclone does not provide a turnkey bidirectional 
sync capability_.  rclonesync.py provides a bidirectional sync solution using rclone.

I use rclonesync on a Centos 7 box to sync both Dropbox and Google Drive to a local disk which is Samba-shared on my LAN. 
I run rclonesync as a Cron job every 30 minutes, or on-demand from the command line.

rclonesync support:
- Validated on Google Drive, Dropbox, OwnCloud, OneDrive (thanks @AlexEshoo), Box (thanks @darlac).
- Linux support, and V2.3 adds Windows support.
- Runs on both Python 2.7 and 3.x.

rclonesync has not been 
tested on other services.  If it works, or sorta works, please raise an issue and I'll update these notes.  Run the test suite
to check for proper operation.

## Installation, setup, getting started
- Install [rclone](https://rclone.org/) and setup your remotes.  Ensure the location is included in your executables search path (PATH environment variable), else see rclonesync's `--rclone` switch.
- Place the rclonesync.py script on your system.  Place it in a directory within your PATH environment variable, or run it with a full path reference.  On Linux, make sure the file mode is set to executable (`chmod +x rclonesync.py`).  On Windows and if using Python 2.7, read about the `win_subprocess.py` and `win32_unicode_argv.py` modules below in the Windows support section.  Place these two modules in the same directory as the rclonesync.py script. 
- Create the rclonesync working directory at `~/.rclonesyncwd` (Linux) or `C:\Users\<your loginname>\.rclonesyncwd` (Windows),  Set up a filters file in this directory, if needed.
- Run rclonesync with the `--first-sync` switch, specifying the paths to the local and remote sync directory roots.
- For successive sync runs, leave off the `--first-sync` switch.
- Consider setting up the --check-access feature for safety, and the `--filters-file` feature for excluding unnecessary files and directories from the sync.
- On Linux, consider setting up a crontab entry.  The following runs a sync every 5 minutes between a local directory and an OwnCloud server, with output logged to a runlog file:
```
# Minute (0-59)
#      Hour (0-23)
#           Day of Month (1-31)
#                Month (1-12 or Jan-Dec)
#                     Day of Week (0-6 or Sun-Sat)
#                         Command
  */5  *    *    *    *   ~/scripts/rclonesync.py /mnt/share/myoc owncloud: --check-access --filters-file ~/.rclonesyncwd/Filters  >> ~/scripts/owncloud_runlog 2>&1

```

## Notable changes in the latest release
V2.9 191103:
- Added extended character support for all fields on the command line - issue #35.  For example:  `rclonesync.py /home/<me>/測試_Русский_ě_áñ GDrive:測試_Русский_ě_áñ`.
- NOTE:   As of V2.9, it is required that the Windows CMD shell be properly configured for Unicode support, even if you only use ASCII.  Execute both `chcp 65001` and `set PYTHONIOENCODING=UTF-8` in the command shell before attempting to run rclonesync.  If these are not set properly rclonesync will post an error and exit.
- Tested in Windows 10 with Python 3.8.


## High level behaviors / operations
-  Keeps `rclone lsl` file lists of the Path1 and Path2 filesystems, and on each run checks for deltas on Path1 and Path2
-  Applies Path2 deltas to the Path1 filesystem, then `rclone syncs` the Path1 filesystem to the Path2 filesystem
-  Handles change conflicts nondestructively by creating _Path1 and _Path2 file versions
-  Reasonably fail safe:
	- Lock file prevents multiple simultaneous runs when taking a while.
	- File access health check using `RCLONE_TEST` files (see `--check-access` switch).
	- Excessive deletes abort - Protects against a failing `rclone lsl` being interpreted as all the files were deleted.  See 
	the `--max-deletes` and `--force` switches.
	- If something evil happens, rclonesync goes into a safe state to block damage by later runs.  (See **Runtime Error Handling**, below)


```
$ ./rclonesync.py -h
usage: rclonesync.py [-h] [-1] [-c] [--check-filename CHECK_FILENAME]
                     [-D MAX_DELETES] [-F] [-e] [-f FILTERS_FILE] [-r RCLONE]
                     [--config CONFIG] [--rclone-args ...] [-v] [--rc-verbose]
                     [-d] [-w WORKDIR] [--no-datetime-log] [-V]
                     Path1 Path2

***** BiDirectional Sync for Cloud Services using rclone *****

positional arguments:
  Path1                 Local path, or cloud service with ':' plus optional
                        path. Type 'rclone listremotes' for list of configured
                        remotes.
  Path2                 Local path, or cloud service with ':' plus optional
                        path. Type 'rclone listremotes' for list of configured
                        remotes.

optional arguments:
  -h, --help            show this help message and exit
  -1, --first-sync      First run setup. WARNING: Path2 files may overwrite
                        path1 versions. Consider using with --dry-run first.
                        Also asserts --verbose.
  -c, --check-access    Ensure expected RCLONE_TEST files are found on both
                        path1 and path2 filesystems, else abort.
  --check-filename CHECK_FILENAME
                        Filename for --check-access (default is
                        <RCLONE_TEST>).
  -D MAX_DELETES, --max-deletes MAX_DELETES
                        Safety check for percent maximum deletes allowed
                        (default 50%). If exceeded the rclonesync run will
                        abort. See --force.
  -F, --force           Bypass --max-deletes safety check and run the sync.
                        Also asserts --verbose.
  -e, --remove-empty-directories
                        Execute rclone rmdirs as a final cleanup step.
  -f FILTERS_FILE, --filters-file FILTERS_FILE
                        File containing rclone file/path filters (needed for
                        Dropbox).
  -r RCLONE, --rclone RCLONE
                        Path to rclone executable (default is rclone in path
                        environment var).
  --config CONFIG       Path to rclone config file (default is typically
                        ~/.config/rclone/rclone.conf).
  --rclone-args ...     Optional argument(s) to be passed to rclone. Specify
                        this switch and rclone ags at the end of rclonesync
                        command line.
  -v, --verbose         Enable event logging with per-file details.
  --rc-verbose          Enable rclone's verbosity levels (May be specified
                        more than once for more details. Also asserts
                        --verbose.)
  -d, --dry-run         Go thru the motions - No files are copied/deleted.
                        Also asserts --verbose.
  -w WORKDIR, --workdir WORKDIR
                        Specified working dir - used for testing. Default is
                        ~user/.rclonesyncwd.
  --no-datetime-log     Disable date-time from log output - useful for
                        testing.
  -V, --version         Return rclonesync's version number and exit.
```	

Typical run log:
```
$ ./rclonesync.py ./testdir/path1/ GDrive:testdir/path2/ --verbose
2018-07-28 17:13:25,912:  ***** BiDirectional Sync for Cloud Services using rclone *****
2018-07-28 17:13:25,913:  Synching Path1  <./testdir/path1/>  with Path2  <GDrive:/testdir/path2/>
2018-07-28 17:13:25,913:  Command line:  <Namespace(Path1='./testdir/path1/', Path2='GDrive:testdir/path2/', check_access=False, dry_run=False, filters_file=None, first_sync=False, force=False, max_deletes=50, no_datetime_log=False, rc_verbose=None, verbose=True, workdir='./testwd/')>
2018-07-28 17:13:27,244:  >>>>> Path1 Checking for Diffs
2018-07-28 17:13:27,244:    Path1      File is newer                     - file2.txt
2018-07-28 17:13:27,244:    Path1      File size is different            - file2.txt
2018-07-28 17:13:27,244:    Path1      File was deleted                  - file4.txt
2018-07-28 17:13:27,244:    Path1      File is newer                     - file5.txt
2018-07-28 17:13:27,244:    Path1      File size is different            - file5.txt
2018-07-28 17:13:27,244:    Path1      File was deleted                  - file6.txt
2018-07-28 17:13:27,244:    Path1      File is newer                     - file7.txt
2018-07-28 17:13:27,245:    Path1      File size is different            - file7.txt
2018-07-28 17:13:27,245:    Path1      File is new                       - file11.txt
2018-07-28 17:13:27,245:       6 file change(s) on Path1:    1 new,    3 newer,    0 older,    2 deleted
2018-07-28 17:13:27,245:  >>>>> Path2 Checking for Diffs
2018-07-28 17:13:27,245:    Path2      File is newer                     - file1.txt
2018-07-28 17:13:27,245:    Path2      File size is different            - file1.txt
2018-07-28 17:13:27,245:    Path2      File is newer                     - file5.txt
2018-07-28 17:13:27,245:    Path2      File size is different            - file5.txt
2018-07-28 17:13:27,245:    Path2      File is newer                     - file6.txt
2018-07-28 17:13:27,245:    Path2      File size is different            - file6.txt
2018-07-28 17:13:27,245:    Path2      File is new                       - file10.txt
2018-07-28 17:13:27,245:       4 file change(s) on Path2:    1 new,    3 newer,    0 older,    0 deleted
2018-07-28 17:13:27,245:  >>>>> Applying changes on Path2 to Path1
2018-07-28 17:13:27,245:    Path2      Copying to Path1                  - ./testdir/path1/file1.txt
2018-07-28 17:13:30,133:    Path2      Copying to Path1                  - ./testdir/path1/file10.txt
2018-07-28 17:13:33,148:    WARNING    Changed in both Path1 and Path2   - file5.txt
2018-07-28 17:13:33,148:    Path2      Copying to Path1                  - ./testdir/path1/file5.txt_Path2
2018-07-28 17:13:43,739:    Path1      Renaming Path1 copy               - ./testdir/path1/file5.txt_Path1
2018-07-28 17:13:43,747:    WARNING    Deleted on Path1 and also changed on Path2 - file6.txt
2018-07-28 17:13:43,747:    Path2      Copying to Path1                  - ./testdir/path1/file6.txt
2018-07-28 17:13:46,642:  >>>>> Synching Path1 to Path2
2018-07-28 17:13:51,932:  >>>>> Refreshing Path1 and Path2 lsl files
2018-07-28 17:13:53,263:  >>>>> Successful run.  All done.
```

## rclonesync Operations

rclonesync keeps copies of the prior sync file lists of both Path1 and Path2 filesystems, and on a new run checks for any changes.
Note that on some (all?) cloud storage systems it is not possible to have file timestamps 
that match between the local and other cloud filesystems.  rclonesync works around this problem by tracking Path1-to-Path1 
and Path2-to-Path2 deltas, and then applying the changes on the other side. 

### Notable features / functions / behaviors

- **Path1** and **Path2** arguments may be references to any mix of local directory paths (absolute or relative), UNC paths 
(//server/share/path), or configured 
remotes/clouds with optional subdirectory paths.  Cloud references are distinguished by having a ':' in the argument 
(see Windows support, below).  Path1 may 
be considered the master, in that any changed files on Path2 are applied to Path1, and then a native `rclone sync` is used to 
make Path2 match Path1.  The LSL files in rclonesync's working directory (default `~/.rclonesyncwd`) 
are named based on the Path1 and Path2 arguments so that separate syncs to individual directories within the tree may be set up. 
In the tables below, understand that the last operation is to do an `rclone sync <Path1> <Path2>` _if_ rclonesync had made any 
changes on the Path1 filesystem.

- Any empty directories after the sync on both the Path1 and Path2 filesystems are **NOT** deleted, by default 
(changed in V2.4).  If the `--remove-empty-directories` switch is specified, then both paths will have any empty directories
purged as the last step in the process.

- **--first-sync** - This will effectively make both Path1 and Path2 filesystems contain a matching superset of all files.  Path2 
files that do not exist in Path1 will be copied to Path1, and the process will then sync the Path1 tree to Path2. 
**Note that the base directories on both the Path1 and Path2 filesystems 
must exist, and must contain at least one file, or rclonesync will fail.**  This is required for safety - that rclonesync can
verify that both paths are valid.  Attempting to rclonesync to an empty directory results in `ERROR    Zero length in prior Path list file`.
The fix is simply to create the missing directory and place a single file in it and rerun the --first-sync.
**NOTE that when using --first-sync a newer version of a file on the Path2 filesystem will be overwritten by the Path1 filesystem 
version.** Carefully evaluate deltas using --dry-run.

- **--check-access** - Access check files are an additional safety measure against data loss.  rclonesync will ensure it can 
find matching `RCLONE_TEST` files in the same places in the Path1 and Path2 filesystems.  Time stamps and file contents 
are not important, just the names and locations.  Place one or more RCLONE_TEST files in the Path1 or Path2 filesystem and then 
do either a run without `--check-access` or a `--first-sync` to set matching files on both filesystems. _Also see the 
`--check-filename` switch._

- **--max-deletes** - As a safety check, if greater than the --max-deletes percent of files were deleted on either the Path1 or
Path2 filesystem, then rclonesync will abort with a warning message, without making any changes.  The default --max-deletes is 50%. 
One way to trigger this limit is to rename a directory that contains more than half of your files.  This will appear to rclonesync as a
bunch of deleted files and a bunch of new files.
This safety check is intended to block rclonesync from deleting all of the files on both filesystems
due to a temporary network access issue, or if the user had inadvertently deleted the files on one side or the other.  To force the sync 
either set a different delete percentage limit, eg `--max-deletes 75` (allows up to 75% deletion), or use `--force` to bypass the check.

- **--filters-file** - Using rclone's filter features you can exclude file types or directory sub-trees from the sync. 
See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).) A
starter `Filters` file is included with rclonesync that contains filters for not-allowed files for syncing with Dropbox, and a filter
for the rclonesync test engine temporary test tree, `/testdir/`.  **NOTE:** if you make changes to your filters file then 
rclonesync requires a run with --first-sync.  This is a safety feature, which avoids 
existing files on the Path1 and/or Path2 side from seeming to disappear from view (since they are newly excluded in the LSL runs), 
which would fool
rclonesync into seeing them as deleted (as compared to the prior run LSL files), and then rclonesync would proceed to delete them 
for real.  To block this from happening rclonesync calculates an MD5 hash of your filters file and stores the hash in a ...MD5 file
in the same
place as your filters file.  On each rclonesync run with --filters-file set, rclonesync first calculates the MD5 hash of the current
filters file and compares it to the hash stored in the ...MD5 file.  If they don't match the run aborts with a CRITICAL error and
thus forces you to do a --first-sync, likely avoiding a disaster.

- **--rclone-args** - Arbitrary rclone switches may be specified on the rclonesync.py command line by placing `--rclone-args` as the last argument in the rclonesync.py call, followed by one or more switches to be passed in the rclone calls.  For example:  `../rclonesync.py ./testdir/path1/ GDrive:testdir/path2/ --rclone-args --drive-skip-gdocs -v -v --timeout 0m10s`.  (rclonesync.py is coded to skip Google doc files without the example switch.)  Note that the interaction of the various rclone switches with the rclonesync.py process flow has not be tested.  The specified switches are passed on all rclone calls (lsl, copy, copyto, move, moveto, delete, sync, rmdirs), although some switches may not be appropriate for some rclone commands. Initial testing shows problems with the `--copy-links` and `--links` switches.

- **Google Doc files** - Google docs exist as virtual files on Google Drive, and cannot be transferred to other filesystems natively.
rclonesync's handling of Google Doc files is to 1) Flag them in the run log output as an FYI, and 2) ignore them for any file transfers,
deletes, or syncs.  See TROUBLESHOOTING.md for more info.

- **Verbosity controls** - `--verbose` enables rclonesync's logging of each check and action (as shown in the typical run log, above). 
rclone's verbosity levels may also be enabled using the `--rc-verbose` switch.  rclone supports additional verbosity levels which may be 
enabled by providing the `--rc-verbose` switch more than once.  Turning on rclone's verbosity using `--rc-verbose` will also turn on
rclonesync's `--verbose` switch.  **Note** that rclonesync's log messages have '-'s in the date stamp (2018-06-11), while rclone's 
log messages have '/'s in the date stamp (2018/06/11) - this is important for tracking down the source of problems.

- **Runtime Error Handling** - Certain rclonesync critical errors, such as `rclone copyto` failing, 
will result in an rclonesync lockout of successive runs.  The lockout is asserted because the sync status of the Path1 and Path2 filesystems
cannot be trusted, so it is safer to block any further changes until someone with a brain (you) check things out.
The recovery is to do a --first-sync again.  It is recommended to use --first-sync 
--dry-run --rc-verbose initially and carefully review what changes will be made before running the --first-sync without --dry-run. 
Most of these events come up due to rclone returning a non-zero status from a command.  On such a critical error 
the <...>__Path1LSL and <...>__Path1LSL files are renamed adding _ERROR, which blocks any future rclonesync runs (since the 
original files are not found).  Some errors are considered temporary, and re-running the rclonesync is not blocked. 
Within the code, see usages of `return RTN_CRITICAL` and `return RTN_ABORT`.  `return RTN_CRITICAL` blocks further rclonesync runs.

- **--dry-run oddity** - The --dry-run messages may indicate that it would try to delete files on the Path2 server in the last 
rclonesync step of rclone syncing Path1 to the Path2.  If the file did not exist on Path1 then it would normally be copied to 
the Path1 filesystem, but with --dry-run enabled those copies didn't happen, and thus on the final `rclone sync` step they don't exist on Path1, 
which leads to the attempted delete on the Path2, blocked again by --dry-run: `... Not deleting as --dry-run`.  This whole confusing situation is an 
artifact of the `--dry-run` switch.  Scrutinize the proposed deletes carefully, and if the files would have been copied to Path1 then 
the threatened deletes on Path2 may be disregarded.

- **Lock file** - When rclonesync is running, a lock file is created (typically on Linux at /tmp/rclonesync_LOCK_path1_path2).  If rclonesync should crash or 
hang the lock file will remain in place and block any further runs of rclonesync _for the same paths_.  Delete the lock file as part of 
debugging the situation.  The lock file effectively blocks follow-on (i.e., CRON scheduled) runs when the prior invocation 
is taking a long time.  The lock file contains the job command line and time, which may help in debug.  If rclonesync crashes with a Python
traceback please open an issue.  **NOTE** that while concurrent rclonesync runs are allowed, **be very cautious** that there is no overlap in the trees being synched between concurrent runs, lest there be replicated files, deleted files, and general mayhem - _you have been warned_.

- **Return codes** - rclonesync returns `0` to the calling script on a successful run, `1` for a non-critical failing run (a rerun may be successful), and `2` for a critically aborted run (requires a --first-sync to recover).

- **Test features** - V2.0 adds a companion testrcsync.py script.  The --workdir and --no-datetime-log switches were added to rclonesync
to support testing.  See the TESTCASES.md file.  You 
will likely want to add `- /testdir/**` to your filters-file so that normal syncs do not attempt to sync the test run temporary 
directories, which may have RCLONE_TEST miscompares in some test cases and thus trip the --check-access system.  The --check-access
mechanism is hard-coded to ignore RCLONE_TEST files beneath RCloneSync/Test.

### Windows support
Support for rclonesync on Windows was added in V2.3.  
- Tested on Windows 10 Pro version 1903 (May'19) and with rclone v1.46 release, and both Python 2.7.17 and 3.8.0.
- **NOTE:   As of V2.9, it is required that the Windows CMD shell be properly configured for Unicode support, even if you only use ASCII.  Execute both `chcp 65001` and `set PYTHONIOENCODING=UTF-8` in the command shell before attempting to run rclonesync.  If these are not set properly rclonesync will post an error and exit.**
- Drive letters are allowed, including drive letters mapped to network drives (`rclonesync.py J:\localsync GDrive:`). 
If a drive letter is omitted the shell current drive is the default.  Drive letters are a single character follows by ':', so cloud names
must be more than one character long.
- Absolute paths (with or without a drive letter), and relative paths (with or without a drive letter) are supported.
- rclonesync's working directory is created at the user's top level (`C:\Users\<user>\.rclonesyncwd`).
- rclone must be in the path, or use rclonesync's `--rclone` switch.
- Note that rclonesync output will show a mix of forward `/` and back '\' slashes.  They are equivalent in Python - not to worry.
- Be careful of case independent directory and file naming on Windows vs. case dependent Linux!
- As of version 2.9, extended characters (Unicode code points, UTF-8) are now supported in all path fields in the rclonesync command line.  However,Python 2.7 on Windows does not natively support extended characters on the command line.  The `win32_unicode_argv.py` module has been added to this project to address this Win-Ph2.7-specific gap.  See [this post](https://stackoverflow.com/questions/846850/read-unicode-characters-from-command-line-arguments-in-python-2-x-on-windows/846931#846931).  Additionally, the subprocess calls within rclonesync.py must support extended characters, and the Python 2.7 on Windows subprocess module does not natively support extended characters.  Valentin Lab posted a fix for the Python 2.7 Windows subprocess.py module as `win_subprocess.py` (https://gist.github.com/vaab/2ad7051fc193167f15f85ef573e54eb9), which has also been added to the rclonesync project, with no edits other than noting the source.  When rclonesync.py is run from Windows on Python 2.7, a dummy file `deleteme.txt` is created in the rclonesync working directory (due to a constraint/bug in win_subprocess.py).  This file may be ignored or deleted (it will come back).  These modules are only needed for Python 2.7 on Windows.    Note that it appears that rclone itself only allows ASCII characters in the names of remotes.
 

### Usual sync checks

 Type | Description | Result| Implementation ** 
--------|-----------------|---------|------------------------
Path2 new| File is new on Path2, does not exist on Path1 | Path2 version survives | `rclone copyto` Path2 to Path1
Path2 newer| File is newer on Path2, unchanged on Path1 | Path2 version survives | `rclone copyto` Path2 to Path1
Path2 deleted | File is deleted on Path2, unchanged on Path1 | File is deleted | `rclone delete` Path1
Path1 new | File is new on Path1, does not exist on Path2 | Path1 version survives | `rclone sync` Path1 to Path2
Path1 newer| File is newer on Path1, unchanged on Path2 | Path1 version survives | `rclone sync` Path1 to Path2
Path1 older| File is older on Path1, unchanged on Path2 | Path1 version survives | `rclone sync` Path1 to Path2
Path1 deleted| File no longer exists on Path1| File is deleted | `rclone sync` Path1 to Path2


### *UNusual* sync checks

 Type | Description | Result| Implementation **
--------|-----------------|---------|------------------------
Path1 new AND Path2 new | File is new on Path1 AND new on Path2 | Files renamed to _Path1 and _Path2 | `rclone copyto` Path2 to Path1 as _Path2, `rclone moveto` Path1 as _Path1
Path2 newer AND Path1 changed | File is newer on Path2 AND also changed (newer/older/size) on Path1 | Files renamed to _Path1 and _Path2 | `rclone copyto` Path2 to Path1 as _Path2, `rclone moveto` Path1 as _Path1
Path2 newer AND Path1 deleted | File is newer on Path2 AND also deleted on Path1 | Path2 version survives  | `rclone copyto` Path2 to Path1
Path2 deleted AND Path1 changed | File is deleted on Path2 AND changed (newer/older/size) on Path1 | Path1 version survives |`rclone sync` Path1 to Path2
Path1 deleted AND Path2 changed | File is deleted on Path1 AND changed (newer/older/size) on Path2 | Path2 version survives  | `rclone copyto` Path2 to Path1

** If any changes are made on the Path1 filesystem then the final operation is an `rclone sync` to update the Path2 filesystem to match.

### Unhandled - WARNING

 Type | Description | Comment 
--------|-----------------|---------
Path2 older|  File is older on Path2, unchanged on Path1 | `rclone sync` will push the newer Path1 version to Path2.
Path1 size | File size is different (same timestamp) | Not sure if `rclone sync` will pick up on just a size difference and push the Path1 to Path2.


## Revision history

- V2.9 191103 Support Unicode in command line args.  Support Python 3 on Windows.
- V2.8 191003 Fixed Windows platform detect bug (#27), utilized Python's tempfile directory feature (#28), and made non-verbose logging completely quiet (#31).
- V2.7 190429 Added paths-specific lock filename and exit codes.  Corrected listremotes subprocess call (thanks @JasperJuergensen).
- V2.6 190408 Added --config and --rclone-args switches.
- V2.5 190330 Fixed Windows with Python 2.7 extended characters (UTF-8) support.  
- V2.4 181004 Added --remove-empty-directories and --check-filename switches.  **NOTE** that the rmdirs default behavior changed as of 
this release:  empty directories are NOT deleted by default, whereas they were deleted in prior releases.

- V2.3 181001 Added Windows support.  UNC paths (//server/share/path) now supported.  
Minimum Python V2.7 is now enforced.  Added --rclone switch.

- V2.2 180921 Changed MD5 hash of the filtersfile for support of extended character sets, such as Cyrillic.  Thanks for the fix @erakli!

- V2.1 180729 Reworked to Path1/Path2, allowing unrestricted sync between local and remote filesystems. Added blocking of syncs of Google
doc files (size -1).  Google doc file are logged as not syncable, but do not cause the overall rclonesync run to fail.

- V2.0 180701 Added rclonesync test capabilities. 
		Fixed corner case bug that copied a file from Remote to Local twice. 
		Changed from --ExcludeListFile to --filters-file, which requires minor adjustments to your excludes file (add a '- ' in front of your
		excludes). See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).)
		Added change detection on the filters file (MD5 hash), forcing a --first-sync in order to avoid doing damage. 
		Added --max-deletes switch for command line control of the excessive deletes feature.
		Changed rclonesync's interface to align to Linux command line standards (lower case, hyphens between words).  Internally adjusted
		the code to reasonably closely align with Python coding standards in PEP 8.
		
- 180611  Bug fix:  A deleted a file on the Remote filesystem results in an rclone delete on the Local filesystem.  If switches to rclone are enabled 
		(--rc-verbose or --dry-run) then the issued delete command was incorrect -- the switches became the p2 param to rcloneCmd.
		Added `options=' to all calls to rcloneCmd to force switches the options keyword arg.

- 180314  Incorporated rework by croadfeldt, changing handling of subprocess commands and many src/dest, etc. from strings 
		to lists.  No functional or interface changes.  Added --dry-run oddity note to the README.

- 171119  Added 3x retry on rclone commands to improve robustness.  Beautified the `--verbose` mode output.  Broke out control of 
		rclone's verbosity with the`--rc-verbose` switch.
		
- 171115  Remote supports path entry.  Reworked LSL file naming to support for Remote paths.
       --verbose switch applies to all rclone copyto, moveto, delete, and sync calls (was only on sync)

- 171112  Revamped error handling to be effective.  See Readme.md.
       Added --check-access switch to make filesystems access test optional.  Default is False (no check).

- 171015  Moved tooManyLocalDeletes error message down below the Remote check to provide both Local and Remote change lists to the stdout

- 170917  Added --Force switch - required when the % changes on Local or Remote system are greater than maxDelta.  Safeguard for
       Local or Remote not online.
       Added --ignore-times to the copy of changed file on Remote to Local.  Was not copying files with matching sizes.

- 170805  Added --verbose command line switch 

- 170730  Horrible bug - Remote lsl failing results in deleting all Local files, and then iteratively replicating _Local and _Remote files.
       Added connection test/checking files to abort if the basic connection is down.  RCLONE_TEST files on the Local system
       must match the Remote system (and be unchanged), else abort.
       Added lockfile so that a second run aborts if a first run is still in process, or failed and left the lockfile in place.
       Added python logging, sorted processing

- 170716  New


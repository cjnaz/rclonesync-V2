# rclonesync - A Bidirectional Cloud Sync Utility using rclone


[Rclone](https://rclone.org/) provides a programmatic building block interface for transferring files between a cloud service 
provider and your local filesystem (actually a lot of functionality), but _rclone does not provide a turnkey bidirectional 
sync capability_.  _rclonesync_ provides a bidirectional sync solution using rclone.

### rclonesync high level behaviors / operations
- Retains the `rclone lsl` file lists of the Path1 and Path2 filesystems from the prior run
- On each successive run: 
	- rclonesync gets the current LSL's of Path1 and Path2, and checks for changes on each.  Changes include New, Newer, Older, and Deleted files.
	- Changes on Path1 are propagated to Path2, and vice-versa. 
-  Reasonably fail safe:
	- Lock file prevents multiple simultaneous runs when taking a while.
	- Handles change conflicts nondestructively by creating _Path1 and _Path2 file versions
	- File system access health check using `RCLONE_TEST` files (see `--check-access` switch).
	- Excessive deletes abort - Protects against a failing `rclone lsl` being interpreted as all the files were deleted.  See 
	the `--max-deletes` and `--force` switches.
	- If something evil happens, rclonesync goes into a safe state to block damage by later runs.  (See **Runtime Error Handling**, below)


### rclonesync supported usage:
- Runs on Linux and Windows.
- Requires Python 3.6 or later (tested on 3.6.8 minimum).
- Requires rclone V1.53 or later. 
- Validated on Google Drive, Dropbox, OwnCloud, OneDrive (thanks @AlexEshoo), Box (thanks @darlac).
- rclonesync has not been fully 
tested on other services.  If it works, or sorta works, please raise an issue and I'll update these notes.  Run the test suite
to check for proper operation.


` `  
## Installation, setup, getting started
- Install [rclone](https://rclone.org/) and setup your remotes.  Ensure the location is included in your executables search path (PATH environment variable), else see rclonesync's `--rclone` switch.
- Place the rclonesync script on your system.  Place it in a directory within your PATH environment variable, or run it with a full path reference.  On Linux, make sure the file mode is set to executable (`chmod +x rclonesync`).   
- Create the rclonesync working directory at `~/.rclonesyncwd` (Linux) or `C:\Users\<your loginname>\.rclonesyncwd` (Windows),  Set up a filters file in this directory, if needed.
- Run rclonesync with the `--first-sync` switch, specifying the paths to the local and remote sync directory roots.
- For successive sync runs, leave off the `--first-sync` switch.
- Consider setting up the `--check-access` feature for safety, and the `--filters-file` feature for excluding unnecessary files and directories from the sync.  See [FILTERING.md](FILTERING.md).
- On Linux, consider setting up a crontab entry.  The following runs a sync every 5 minutes between a local directory and an OwnCloud server, with output logged to a runlog file:

        # Minute (0-59)
        #      Hour (0-23)
        #           Day of Month (1-31)
        #                Month (1-12 or Jan-Dec)
        #                     Day of Week (0-6 or Sun-Sat)
        #                         Command
          */5  *    *    *    *   ~/scripts/rclonesync /mnt/share/mylocal Mycloud: --check-access --filters-file ~/.rclonesyncwd/Filters  >> ~/scripts/runlog 2>&1
- rclonesync has no built-in capability to monitor the file system for changes, and must be blindly run periodically.  User @bshensky put together a set of scripts that receive Linux OS inotifies and change notifications from Dropbox.  See [rclonesync + inotifywait + Dropbox Webhook = handcrafted local Linux Dropbox volume #68](https://github.com/cjnaz/rclonesync-V2/issues/68) and [vault_rclonesync.zip](vault_rclonesync.zip) for this setup.  Note that this 
setup is NOT supported within the rclonesync project - please work with the author.

` `  
## Notable changes in the latest release

### V3.2
- Added Check Sync integrity checks on the final LSL files, enabled by default.  New switches `--no-check-sync` disables the normal integrity check at the end of a run, and `--check-sync-only` only runs the integrity check and terminates.  Note that the default-enabled integrity check locally executes a load of both the final path1 and path2 LSL files, and thus adds to the run time of a sync.  Using `--no-check-sync` may significantly reduce sync run times for large numbers of files.
- Support for spaces in remote names, as supported by rclone.
- Minimum required version of rclone is v1.53.  (A bug in v1.52 affected moveto, blocking renames on remotes.)
- Included user submission of inotify wrapper scripts for use with Dropbox. See ([issue #68](https://github.com/cjnaz/rclonesync-V2/issues/68)) and [vault_rclonesync.zip](vault_rclonesync.zip)
- Minor bug fixes.


` `  
## rclonesync command line interface

```
$ ../rclonesync -h
usage: rclonesync [-h] [-1] [-c] [--check-filename CHECK_FILENAME]
                  [-D MAX_DELETES] [-F] [--no-check-sync] [--check-sync-only]
                  [-e] [-f FILTERS_FILE] [-r RCLONE] [--config CONFIG]
                  [--rclone-args ...] [-v] [--rc-verbose] [-d] [-w WORKDIR]
                  [--no-datetime-log] [--no-cleanup] [-V]
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
  -1, --first-sync      First run setup. WARNING: Path1 files may overwrite
                        path2 versions. Consider using with --dry-run first.
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
  --no-check-sync       Disable comparison of final LSL files (default is
                        check-sync enabled).
  --check-sync-only     Only execute the comparison of LSL files from the last
                        rclonesync run.
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
  -v, --verbose         Enable event logging with per-file details. Specify
                        once for info and twice for debug detail.
  --rc-verbose          Enable rclone's verbosity levels (May be specified
                        more than once for more details. Also asserts
                        --verbose.)
  -d, --dry-run         Go thru the motions - No files are copied/deleted.
                        Also asserts --verbose.
  -w WORKDIR, --workdir WORKDIR
                        Specified working dir - useful for testing. Default is
                        ~user/.rclonesyncwd.
  --no-datetime-log     Disable date-time from log output - useful for
                        testing.
  --no-cleanup          Retain working files - useful for debug and testing.
  -V, --version         Return rclonesync's version number and exit.
```	

Typical run log (test case `test_changes` output - normally timestamps are included):
```
../rclonesync ./testdir/path1/ ./testdir/path2/ --verbose --workdir ./testwd/ --no-datetime-log --no-cleanup --rclone rclone --config /home/<me>/.config/rclone/rclone.conf
***** BiDirectional Sync for Cloud Services using rclone (V3.2 201201) *****
Lock file created: </tmp/rclonesync_LOCK_._testdir_path1_._testdir_path2_>
Synching Path1  <./testdir/path1/>  with Path2  <./testdir/path2/>
Command args: <Path1=./testdir/path1/, Path2=./testdir/path2/, check_access=False, check_filename=RCLONE_TEST, check_sync_only=False, config=/home/<me>/.config/rclone/rclone.conf, dry_run=False, filters_file=None, first_sync=False, force=False, max_deletes=50, no_check_sync=False, no_cleanup=True, no_datetime_log=True, rc_verbose=None, rclone=rclone, rclone_args=None, remove_empty_directories=False, verbose=1, workdir=./testwd/>
>>>>> Path1 Checking for Diffs
  Path1      File is newer                     - file2.txt
  Path1      File was deleted                  - file4.txt
  Path1      File is newer                     - file5.txt
  Path1      File was deleted                  - file6.txt
  Path1      File is newer                     - file7.txt
  Path1      File was deleted                  - file8.txt
  Path1      File is new                       - file11.txt
     7 file change(s) on Path1:    1 new,    3 newer,    0 older,    3 deleted
>>>>> Path2 Checking for Diffs
  Path2      File is newer                     - file1.txt
  Path2      File was deleted                  - file3.txt
  Path2      File is newer                     - file5.txt
  Path2      File is newer                     - file6.txt
  Path2      File was deleted                  - file7.txt
  Path2      File was deleted                  - file8.txt
  Path2      File is new                       - file10.txt
     7 file change(s) on Path2:    1 new,    3 newer,    0 older,    3 deleted
>>>>> Determining and applying changes
  Path1      Queue copy to Path2               - ./testdir/path2/file11.txt
  Path1      Queue copy to Path2               - ./testdir/path2/file2.txt
  Path2      Queue delete                      - ./testdir/path2/file4.txt
  WARNING    New or changed in both paths      - file5.txt
  Path1      Renaming Path1 copy               - ./testdir/path1/file5.txt_Path1
  Path1      Queue copy to Path2               - ./testdir/path2/file5.txt_Path1
  Path2      Renaming Path2 copy               - ./testdir/path2/file5.txt_Path2
  Path2      Queue copy to Path1               - ./testdir/path1/file5.txt_Path2
  Path2      Queue copy to Path1               - ./testdir/path1/file6.txt
  Path1      Queue copy to Path2               - ./testdir/path2/file7.txt
  Path2      Queue copy to Path1               - ./testdir/path1/file1.txt
  Path2      Queue copy to Path1               - ./testdir/path1/file10.txt
  Path1      Queue delete                      - ./testdir/path1/file3.txt
  Path2      Do queued copies to               - Path1
  Path1      Do queued copies to               - Path2
             Do queued deletes on              - Path1
             Do queued deletes on              - Path2
>>>>> Refreshing Path1 and Path2 lsl files
>>>>> Checking integrity of LSL history files for Path1  <./testdir/path1/>  versus Path2  <./testdir/path2/>
Lock file removed: </tmp/rclonesync_LOCK_._testdir_path1_._testdir_path2_>
>>>>> Successful run.  All done.
```

` `  
## rclonesync Operations

rclonesync keeps copies of the prior sync file lists of both Path1 and Path2 filesystems, and on a new run checks for any changes.
Note that on some (all?) cloud storage systems it is not possible to have file timestamps 
that match between the local and other cloud filesystems.  rclonesync works around this problem by tracking Path1-to-Path1 
and Path2-to-Path2 deltas, and then applying the changes on the other side. 

### Notable features / functions / behaviors

- **Path1** and **Path2** arguments may be references to any mix of local directory paths (absolute or relative), UNC paths 
(//server/share/path), Windows drive paths (with a drive letter and `:`) or configured 
remotes/clouds with optional subdirectory paths.  Cloud references are distinguished by having a ':' in the argument 
(see Windows support, below).  Path1 and Path2 are treated equally, in that neither has priority for file changes, and access efficiency does not change whether a remote is on Path1 or Path2.  The LSL files in rclonesync's working directory (default `~/.rclonesyncwd`) 
are named based on the Path1 and Path2 arguments so that separate syncs to individual directories within the tree may be set up. 


- Any empty directories after the sync on both the Path1 and Path2 filesystems are not deleted, by default 
(changed in V2.4).  If the `--remove-empty-directories` switch is specified, then both paths will have any empty directories
purged as the last step in the process.

- **--first-sync** - This will effectively make both Path1 and Path2 filesystems contain a matching superset of all files.  Path2 
files that do not exist in Path1 will be copied to Path1, and the process will then sync the Path1 tree to Path2. Note:
  - The base directories on both the Path1 and Path2 filesystems 
must exist or rclonesync will fail.  This is required for safety - that rclonesync can
verify that both paths are valid.  
  - **When using --first-sync a newer version of a file on the Path2 filesystem will be overwritten by the Path1 filesystem version.** Carefully evaluate deltas using --dry-run.
  - For a first-sync run, one of the paths may be empty (no files in the path tree).  The first-sync run should result in files on both paths, else a non-first-sync run will fail.
  - For a non-first-sync run, either path being empty (no files in the path tree) results in 
`ERROR    Zero length in current Path<X> list file <./testwd/LSL_._testdir_path1_._testdir_path2__Path1_NEW>.  Cannot sync to an empty directory tree.`  This is a safety check - that an unexpected empty path does not result in deleting everything in the other path.

- **--check-access** - Access check files are an additional safety measure against data loss.  rclonesync will ensure it can 
find matching `RCLONE_TEST` files in the same places in the Path1 and Path2 filesystems.  Time stamps and file contents 
are not important, just the names and locations.  Place one or more RCLONE_TEST files in the Path1 or Path2 filesystem and then 
do either a run without `--check-access` or a `--first-sync` to set matching files on both filesystems. _If you have symbolic links in your sync tree it is recommended to place RCLONE_TEST files in the linked-to directory tree to protect against rclonesync assuming a bunch of deleted files if the linked-to tree should not be accessible._  Also see the 
`--check-filename` switch.

- **--max-deletes** - As a safety check, if greater than the --max-deletes percent of files were deleted on either the Path1 or
Path2 filesystem, then rclonesync will abort with a warning message, without making any changes.  The default --max-deletes is 50%. 
One way to trigger this limit is to rename a directory that contains more than half of your files.  This will appear to rclonesync as a
bunch of deleted files and a bunch of new files.
This safety check is intended to block rclonesync from deleting all of the files on both filesystems
due to a temporary network access issue, or if the user had inadvertently deleted the files on one side or the other.  To force the sync 
either set a different delete percentage limit, eg `--max-deletes 75` (allows up to 75% deletion), or use `--force` to bypass the check.

- **All files changed check** - Added in V2.10, if _all_ prior existing files on either of the filesystems have changed (e.g. timestamps have changed due to changing the system's timezone) then rclonesync will abort without making any changes.  Any new files are not considered for this check.  A `--force` may be used for forcing the sync (which ever side has the changed timestamp files wins).  Alternately, a `--first-sync` may be issued (Path1 versions will be pushed to Path2).  Consider the situation carefully, and perhaps use `--dry-run` before you commit to the changes.

- **--filters-file** - Using rclone's filter features you can exclude file types or directory sub-trees from the sync. 
See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).) A
starter `Filters` file is included with rclonesync that contains filters for not-allowed files for syncing with Dropbox, and a filter
for the rclonesync test engine `/testdir/` temporary test tree.  **NOTE:** if you make changes to your filters file then 
rclonesync requires a run with --first-sync.  This is a safety feature, which avoids 
existing files on the Path1 and/or Path2 side from seeming to disappear from view (since they are newly excluded in the LSL runs), 
which would fool
rclonesync into seeing them as deleted (as compared to the prior run LSL files), and then rclonesync would proceed to delete them 
for real.  To block this from happening rclonesync calculates an MD5 hash of your filters file and stores the hash in a ...MD5 file
in the same
place as your filters file.  On each rclonesync run with --filters-file set, rclonesync first calculates the MD5 hash of the current
filters file and compares it to the hash stored in the ...MD5 file.  If they don't match the run aborts with a CRITICAL error and
thus forces you to do a --first-sync, likely avoiding a disaster.

- **--no-check-sync** and **--check-sync-only** - New in V3.2 and enabled by default, the check-sync function checks that all of the same files exist
in both the Path1 and Path2 LSL history files.  In prior versions, any untrapped failing file copy/deletes between the two paths could result in differences
between the two LSL files, resulting in untracked file content differences between the two paths.  A first-sync run would correct the error.
As of V3.2, this check-sync integrity check is performed at the end
of the sync run, by default.  It may be disabled by the `--no-check-sync` switch, and may be run manually with the `--check-sync-only` switch.
`--no-check-sync` may be desireable when dealing with a very large number of files in order to save overall sync run time.

- **--rclone-args** - Arbitrary rclone switches may be specified on the rclonesync command line by placing `--rclone-args` as the last argument in the rclonesync call, followed by one or more switches to be passed in the rclone calls.  For example:  `../rclonesync ./testdir/path1/ GDrive:testdir/path2/ --rclone-args --drive-skip-gdocs -v -v --timeout 0m10s`.  (rclonesync is coded to skip Google doc files without the example switch.)  Note that the interaction of the various rclone switches with the rclonesync process flow has not be tested.  The specified switches are passed on all rclone calls (lsl, copy, copyto, move, moveto, delete, sync, rmdirs), although some switches may not be appropriate for some rclone commands. Initial testing shows problems with the `--copy-links`, `--links`, and `--create-empty-src-dirs` switches.

- **Verbosity controls** - `--verbose` enables rclonesync's logging of each check and action (as shown in the typical run log, above). Specifying `--verbose --verbose` turns on debug level logging and notably logging of the issued rclone commands. 
rclone's verbosity levels may also be enabled using the `--rc-verbose` switch.  rclone supports additional verbosity levels which may be 
enabled by providing the `--rc-verbose` switch more than once.  Turning on rclone's verbosity using `--rc-verbose` will also turn on
rclonesync's `--verbose` switch.  **Note** that rclonesync's log messages have '-'s in the date stamp (2018-06-11), while rclone's 
log messages have '/'s in the date stamp (2018/06/11) - this is important for tracking down the source of problems.

- **Runtime Error Handling** - Certain rclonesync critical errors, such as `rclone moveto` failing, 
will result in an rclonesync lockout of following runs.  The lockout is asserted because the sync status and history of the Path1 and Path2 filesystems
cannot be trusted, so it is safer to block any further changes until someone with a brain (you) checks things out.
The recovery is to do a --first-sync again.  It is recommended to use `--first-sync 
--dry-run --rc-verbose` initially and carefully review what changes will be made before running the --first-sync without --dry-run. 
Most of these events come up due to rclone returning a non-zero status from a command.  On such a critical error 
the <...>__Path1LSL and <...>__Path1LSL files are renamed adding `_ERROR`, which blocks any future rclonesync runs (since the 
original files are not found).  Some errors are considered temporary, and re-running the rclonesync is not blocked. 
Within the code, see usages of `return RTN_CRITICAL` and `return RTN_ABORT`.  `return RTN_CRITICAL` blocks further rclonesync runs.

- **--dry-run oddity** - The --dry-run messages may indicate that it would try to delete some files.  For example, if a file is new on Path2 and does not exist on Path1 then it would normally be copied to Path1, but with --dry-run enabled those copies don't happen,
which leads to the attempted delete on the Path2, blocked again by --dry-run: `... Not deleting as --dry-run`.  This whole confusing situation is an 
artifact of the `--dry-run` switch.  Scrutinize the proposed deletes carefully, and if the files would have been copied to Path1 then 
the threatened deletes on Path2 may be disregarded.

- **Lock file** - When rclonesync is running, a lock file is created (typically on Linux at /tmp/rclonesync_LOCK_path1_path2).  If rclonesync should crash or 
hang the lock file will remain in place and block any further runs of rclonesync _for the same paths_.  Delete the lock file as part of 
debugging the situation.  The lock file effectively blocks follow-on (i.e., CRON scheduled) runs when the prior invocation 
is taking a long time.  The lock file contains the job command line and time, which may help in debug.  If rclonesync crashes with a Python
traceback please open an issue.  **NOTE** that while concurrent rclonesync runs are allowed, **be very cautious** that there is no overlap in the trees being synched between concurrent runs, lest there be replicated files, deleted files, and general mayhem - _you have been warned_.

- **Return codes** - rclonesync returns `0` to the calling script on a successful run, `1` for a non-critical failing run (a rerun may be successful), and `2` for a critically aborted run (requires a --first-sync to recover).

- **Test features** - rclonesync has a companion testrcsync script.  See the [TESTCASES.md](TESTCASES.md) file.  _If you are doing rclonesync development_ you will likely want to add `- /testdir/` to your filters-file so that normal syncs do not attempt to sync the test run temporary 
directories, which may have RCLONE_TEST miscompares in some test cases and thus trip the --check-access system.  If the rclonesync development directory is within your sync paths, the testing sub-tree is automatically not scanned for RCLONE_TEST files during the check access phase - RCLONE_TEST files beneath `rclonesync/Test/` are excluded from the check.

` `  
## LIMITATIONS (most notable) - _WARNING_
See the Github [Issues](https://github.com/cjnaz/rclonesync-V2/issues) tab for further details.

1. rclonesync relies on file date/time stamps to identify changed files.  If an application (or yourself) should change the content of a file without changing the modification time then rclonesync will not notice the change, and thus will not copy it to the other side.
2. New empty directories on one path are _not_ propagated to the other side ([issue #63](https://github.com/cjnaz/rclonesync-V2/issues/63)).  This is because rclone, and thus rclonesync, natively works on files not directories.  This sequence is a workaround but will not propagate the delete of an empty to the other side:

        1) rclonesync <path1> <path2>
        2) rclone copy <path1> <path2> --filter "+ */" --filter "- **" --create-empty-src-dirs
        3) rclone copy <path2> <path1> --filter "+ */" --filter "- **" --create-empty-src-dirs
3. When using local, ftp, or sftp remotes rclone does not create temporary files at the destination when copying, and thus if the connection is lost the created file may be corrupt, which will likely propagate back to the original path on the next sync, resulting in data loss ([rclonesync issue #56](https://github.com/cjnaz/rclonesync-V2/issues/56) and [rclone issue #1316](https://github.com/rclone/rclone/issues/1316)).  This is a problem for rclone to solve, as there is no way for rclonesync to gracefully and reliably deal with it.
4. Files that change during an rclonesync run may result in data loss ([issue #24](https://github.com/cjnaz/rclonesync-V2/issues/24)).  This has been seen in a highly dynamic environment, where the file system is getting hammered by running processes during the sync.  The best solutions are to 1) sync at quiet times, and/or 2) to [filter out](FILTERING.md) unnecessary directories and files.
5. Exception / failure if there are bogus (non-UTF8) filenames ([issue #62](https://github.com/cjnaz/rclonesync-V2/issues/62)).  rclonesync is hard coded to work with UTF8-encoded filenames.  Solutions: Fix invalid filenames, filter out directories containing such files, or put such files into a .zip file with a proper name.
6. Syncing with non-case-sensitive filesystems, such as Windows and Box, can result in filename conflicts ([issue #54](https://github.com/cjnaz/rclonesync-V2/issues/54)).  This may have some handling in rclonesync in a future release.  The near term fix is to make sure that files on both sides don't have spelling case differences (`Smile.jpg` vs. `smile.jpg`).
7. Google docs exist as virtual files on Google Drive, and cannot be transferred to other filesystems natively.
rclonesync's handling of Google Doc files is to 1) Flag them in the run log output as an FYI, and 2) ignore them for any file transfers,
deletes, or syncs.  See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more info.


` `  
## Windows support
Support for rclonesync on Windows was added in V2.3.  
- Tested on Windows 10 Pro 64-bit version 1909 and with rclone v1.52.2 release on Python 3.8.0.
- **NOTE:  It is required that the Windows CMD shell be properly configured for Unicode support, even if you only use ASCII.  Execute both `chcp 65001` and `set PYTHONIOENCODING=UTF-8` in the command shell before attempting to run rclonesync.  If these are not set properly rclonesync will post an error and exit.**
- Drive letters are allowed, including drive letters mapped to network drives (`rclonesync J:\localsync GDrive:`). 
If a drive letter is omitted the shell current drive is the default.  Drive letters are a single character follows by `:`, so cloud names
must be more than one character long.
- Absolute paths (with or without a drive letter), and relative paths (with or without a drive letter) are supported.
- rclonesync's working directory is created at the user's top level (`C:\Users\<user>\.rclonesyncwd`).
- rclone must be in the path, or use rclonesync's `--rclone` switch.
- Note that rclonesync output will show a mix of forward `/` and back `\` slashes.  They are equivalent in Python - not to worry.
- Be careful of case independent directory and file naming on Windows vs. case dependent Linux!
 

` `  
## Usual sync checks

 Type | Description | Result| Implementation 
--------|-----------------|---------|------------------------
Path2 new| File is new on Path2, does not exist on Path1 | Path2 version survives | `rclone copy` Path2 to Path1
Path2 newer| File is newer on Path2, unchanged on Path1 | Path2 version survives | `rclone copy` Path2 to Path1
Path2 deleted | File is deleted on Path2, unchanged on Path1 | File is deleted | `rclone delete` Path1
Path1 new | File is new on Path1, does not exist on Path2 | Path1 version survives | `rclone copy` Path1 to Path2
Path1 newer| File is newer on Path1, unchanged on Path2 | Path1 version survives | `rclone copy` Path1 to Path2
Path1 older| File is older on Path1, unchanged on Path2 | _Path1 version survives_ | `rclone copy` Path1 to Path2
Path2 older| File is older on Path2, unchanged on Path1 | _Path2 version survives_ | `rclone copy` Path2 to Path1
Path1 deleted| File no longer exists on Path1| File is deleted | `rclone delete` Path2


` `  
## *UNusual* sync checks

 Type | Description | Result| Implementation 
--------|-----------------|---------|------------------------
Path1 new AND Path2 new | File is new on Path1 AND new on Path2 | Files renamed to _Path1 and _Path2 | `rclone copy` _Path2 file to Path1, `rclone copy` _Path1 file to Path2
Path2 newer AND Path1 changed | File is newer on Path2 AND also changed (newer/older/size) on Path1 | Files renamed to _Path1 and _Path2 | `rclone copy` _Path2 file to Path1, `rclone copy` _Path1 file to Path2
Path2 newer AND Path1 deleted | File is newer on Path2 AND also deleted on Path1 | Path2 version survives  | `rclone copy` Path2 to Path1
Path2 deleted AND Path1 changed | File is deleted on Path2 AND changed (newer/older/size) on Path1 | Path1 version survives |`rclone copy` Path1 to Path2
Path1 deleted AND Path2 changed | File is deleted on Path1 AND changed (newer/older/size) on Path2 | Path2 version survives  | `rclone copy` Path2 to Path1


` `  
## Benchmarks

Here are a few data points for scale, execution times, and memory usage.

This first set of data was between my local disk to Dropbox.  My [Speedtest.net](https://www.Speedtest.net) download speed is ~170 Mbps, and upload speed is ~10 Mbps.  500 files (~9.5 MB each) are already sync'd.  50 files were added in a new directory, each ~9.5 MB, ~475 MB total.

Change | Operations and times | Overall run time
----|----|----
500 files sync'd (nothing to move) | 1x LSL Path1 & Path2 | 1.5 sec 
500 files sync'd with --check-access  | 1x LSL Path1 & Path2 | 1.5 sec
50 new files on remote | Queued 50 copies down: 27 sec | 29 sec 
Moved local dir | Queued 50 copies up: 410 sec, Queued 50 deletes up: 9 sec | 421 sec 
Moved remote dir | Queued 50 copies down: 31 sec, Queued 50 deletes down: <1 sec | 33 sec 
Delete local dir | Queued 50 deletes up: 9 sec | 13 sec

This next data is from a user's application.  They have ~400GB of data over 1.96 million files being sync'ed between a Windows local disk and a remote/cloud (type??).  The file full path length is average 35 characters (which factors into load time and RAM required).  (Data points to be added are noted once the user replies.  If you have similar large-scale data please share.)
- Loading the prior LSL into memory (1.96 million files, LSL file size 140 MB) takes ~30 sec and occupies about 1 GB of RAM.
- Executing a fresh `rclone lsl` of the local file system (producing the 140 MB output file) takes about xxx sec.
- Executing a fresh `rclone lsl` of the remote file system (producing the 140 MB output file) takes about xxx sec.  The network download speed was measured at yyy Mb/s.
- Once the prior and current Path1 and Path2 lsl's are loaded (a total of four to be loaded, two at a time), determining the deltas is pretty quick (a few seconds for this test case), and the transfer times for any files to be copied is dominated by the network bandwidth.


` `  
## Revision history
- V3.2 - Added Check-Sync.  Support for spaces in remote names.  Minimum rclone version enforced v1.53, due to bug in v1.52 affecting moveto on remotes.  Added inotify wrapper scripts .zip file to the repo.  Minor bug fixes.
- V3.1.1 201015 - In startup check, allow rclone version without 'v'.
- V3.1 200909 - 50% memory size reduction optimization by loading only two LSLs simultaneously.  Fixed lsl file naming bug related to --dry-run and --first-sync introduced in V3.0.  Added WARNING log for duplicate entries in the LSL files, as seen in one test case.
- V3.0  200824 - Major algorithm revamp.
- V2.11 200813 - Bug fix for proper searching during the check access phase.  
- V2.10 200411 - Added verbose level 2 (debug) with rclone command log (issue #46); Removed '/' after remote: name in support of SFTP remotes (issue #46); Added error trap for all files changed (such as for system timezone change, issue #32); Added trap of keyboard interrupt / SIGINT and lock file removal; Added log of rclonesync version number.
- V2.9.1 191208 - Fixed workdir bug issue #39.
- V2.9 191103 - Support Unicode in command line args.  Support Python 3 on Windows.
- V2.8 191003 - Fixed Windows platform detect bug (#27), utilized Python's tempfile directory feature (#28), and made non-verbose logging completely quiet (#31).
- V2.7 190429 - Added paths-specific lock filename and exit codes.  Corrected listremotes subprocess call (thanks @JasperJuergensen).
- V2.6 190408 - Added --config and --rclone-args switches.
- V2.5 190330 - Fixed Windows with Python 2.7 extended characters (UTF-8) support.  
- V2.4 181004 - Added --remove-empty-directories and --check-filename switches.  **NOTE** that the rmdirs default behavior changed as of 
this release:  empty directories are NOT deleted by default, whereas they were deleted in prior releases.

- V2.3 181001 - Added Windows support.  UNC paths (//server/share/path) now supported.  
Minimum Python V2.7 is now enforced.  Added --rclone switch.

- V2.2 180921 - Changed MD5 hash of the filtersfile for support of extended character sets, such as Cyrillic.  Thanks for the fix @erakli!

- V2.1 180729 - Reworked to Path1/Path2, allowing unrestricted sync between local and remote filesystems. Added blocking of syncs of Google
doc files (size -1).  Google doc file are logged as not syncable, but do not cause the overall rclonesync run to fail.

- V2.0 180701 - Added rclonesync test capabilities. 
		Fixed corner case bug that copied a file from Remote to Local twice. 
		Changed from --ExcludeListFile to --filters-file, which requires minor adjustments to your excludes file (add a '- ' in front of your
		excludes). See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).)
		Added change detection on the filters file (MD5 hash), forcing a --first-sync in order to avoid doing damage. 
		Added --max-deletes switch for command line control of the excessive deletes feature.
		Changed rclonesync's interface to align to Linux command line standards (lower case, hyphens between words).  Internally adjusted
		the code to reasonably closely align with Python coding standards in PEP 8.
		
- 180611 -  Bug fix:  A deleted a file on the Remote filesystem results in an rclone delete on the Local filesystem.  If switches to rclone are enabled 
		(--rc-verbose or --dry-run) then the issued delete command was incorrect -- the switches became the p2 param to rcloneCmd.
		Added `options=' to all calls to rcloneCmd to force switches the options keyword arg.

- 180314 -  Incorporated rework by croadfeldt, changing handling of subprocess commands and many src/dest, etc. from strings 
		to lists.  No functional or interface changes.  Added --dry-run oddity note to the README.

- 171119 -  Added 3x retry on rclone commands to improve robustness.  Beautified the `--verbose` mode output.  Broke out control of 
		rclone's verbosity with the`--rc-verbose` switch.
		
- 171115 -  Remote supports path entry.  Reworked LSL file naming to support for Remote paths.
       --verbose switch applies to all rclone copyto, moveto, delete, and sync calls (was only on sync)

- 171112 -  Revamped error handling to be effective.  See Readme.md.
       Added --check-access switch to make filesystems access test optional.  Default is False (no check).

- 171015 -  Moved tooManyLocalDeletes error message down below the Remote check to provide both Local and Remote change lists to the stdout

- 170917 -  Added --Force switch - required when the % changes on Local or Remote system are greater than maxDelta.  Safeguard for
       Local or Remote not online.
       Added --ignore-times to the copy of changed file on Remote to Local.  Was not copying files with matching sizes.

- 170805 -  Added --verbose command line switch 

- 170730 -  Horrible bug - Remote lsl failing results in deleting all Local files, and then iteratively replicating _Local and _Remote files.
       Added connection test/checking files to abort if the basic connection is down.  RCLONE_TEST files on the Local system
       must match the Remote system (and be unchanged), else abort.
       Added lockfile so that a second run aborts if a first run is still in process, or failed and left the lockfile in place.
       Added python logging, sorted processing

- 170716 -  New


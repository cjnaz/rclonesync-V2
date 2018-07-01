# rclonesync - A Bidirectional Cloud Sync Utility using rclone


[Rclone](https://rclone.org/) provides a programmatic building block interface for transferring files between a cloud service 
provider and your Local filesystem (actually a lot of functionality), but _rclone does not provide a turnkey bidirectional 
sync capability_.  rclonesync.py provides a bidirectional sync solution using rclone.

I use rclonesync on a Centos 7 box to sync both Dropbox and Google Drive to a Local disk which is Samba shared on my LAN. 
I run rclonesync as a Cron job every 30 minutes, or on-demand from the command line.

rclonesync runs on both Python 2.7 and 3.x, and has been validated for Google Drive and Dropbox.  rclonesync has not been 
tested on other services.  If it works, or sorta works, please raise an issue and I'll update these notes.  Run the test suite
to check for proper operation.


### High level behaviors / operations
-  Keeps `rclone lsl` file lists of the Local and Remote systems, and on each run checks for deltas on Local and Remote
-  Applies Remote deltas to the Local filesystem, then `rclone syncs` the Local to the Remote filesystem
-  Handles change conflicts nondestructively by creating _Local and _Remote file versions
-  Reasonably fail safe:
	- Lock file prevents multiple simultaneous runs when taking a while
	- File access health check using `RCLONE_TEST` files (see --check-access switch)
	- Excessive deletes abort - Protects against a failing `rclone lsl` being interpreted as all the files were deleted.  See 
	the --max-deletes and --force switches.
	- If something evil happens, rclonesync goes into a safe state to block damage by later runs.  (See **Runtime Error Handling**, below)


```
$ ./rclonesync.py -h
usage: rclonesync.py [-h] [-1] [-c] [-D MAX_DELETES] [-F] [-f FILTERS_FILE]
                     [-v] [--rc-verbose] [-d] [-w WORKDIR] [--no-datetime-log]
                     [-V]
                     Cloud LocalPath

***** BiDirectional Sync for Cloud Services using rclone *****

positional arguments:
  Cloud                 Name of Remote cloud service (['Dropbox:', 'GDrive:'])
                        plus optional path.
  LocalPath             Path to Local tree base.

optional arguments:
  -h, --help            show this help message and exit
  -1, --first-sync      First run setup. WARNING: Local files may overwrite
                        Remote versions. Consider using --dry-run. Also
                        asserts --verbose.
  -c, --check-access    Ensure expected RCLONE_TEST files are found on both
                        Local and Remote filesystems, else abort.
  -D MAX_DELETES, --max-deletes MAX_DELETES
                        Safety check for percent maximum deletes allowed
                        (default 50%). If exceeded the rclonesync run will
                        abort. See --force.
  -F, --force           Bypass --max-deletes safety check and run the sync.
                        Also asserts --verbose.
  -f FILTERS_FILE, --filters-file FILTERS_FILE
                        File containing rclone file/path filters (needed for
                        Dropbox).
  -v, --verbose         Enable event logging with per-file details.
  --rc-verbose          Enable rclone's verbosity levels (May be specified
                        more than once for more details. Also asserts
                        --verbose.)
  -d, --dry-run         Go thru the motions - No files are copied/deleted.
                        Also asserts --verbose.
  -w WORKDIR, --workdir WORKDIR
                        Specified working dir - used for testing. Default is
                        ~user/.rclonesyncwd.
  --no-datetime-log     Disable date-time from log output - used for testing.
  -V, --version         Return rclonesync's version number and exit.

```	

Typical run log:
```
2018-07-01 11:41:50,925:  ***** BiDirectional Sync for Cloud Services using rclone *****
2018-07-01 11:41:50,925:  Synching Remote path  <GDrive:/testdir/>  with Local path  <./testdir/>
2018-07-01 11:41:50,925:  Command line:  <Namespace(Cloud='GDrive:/testdir', LocalPath='./testdir', check_access=False, dry_run=False, filters_file=None, first_sync=False, force=False, max_deletes=50, no_datetime_log=False, rc_verbose=None, verbose=True, workdir='./testwd/')>
2018-07-01 11:41:50,925:  >>>>> Generating Local and Remote lists
2018-07-01 11:41:51,513:    Local    Checking for Diffs                  - ./testdir/
2018-07-01 11:41:51,513:    Local      File is newer                     - file2.txt
2018-07-01 11:41:51,513:    Local      File size is different            - file2.txt
2018-07-01 11:41:51,513:    Local      File was deleted                  - file4.txt
2018-07-01 11:41:51,513:    Local      File is newer                     - file5.txt
2018-07-01 11:41:51,513:    Local      File size is different            - file5.txt
2018-07-01 11:41:51,513:    Local      File was deleted                  - file6.txt
2018-07-01 11:41:51,513:    Local      File is newer                     - file7.txt
2018-07-01 11:41:51,513:    Local      File size is different            - file7.txt
2018-07-01 11:41:51,513:    Local      File is new                       - file11.txt
2018-07-01 11:41:51,513:       6 file change(s) on Local:     1 new,    3 newer,    0 older,    2 deleted
2018-07-01 11:41:51,514:    Remote   Checking for Diffs                  - GDrive:/testdir/
2018-07-01 11:41:51,514:    Remote     File is newer                     - file1.txt
2018-07-01 11:41:51,514:    Remote     File size is different            - file1.txt
2018-07-01 11:41:51,514:    Remote     File was deleted                  - file3.txt
2018-07-01 11:41:51,514:    Remote     File is newer                     - file5.txt
2018-07-01 11:41:51,514:    Remote     File size is different            - file5.txt
2018-07-01 11:41:51,514:    Remote     File is newer                     - file6.txt
2018-07-01 11:41:51,514:    Remote     File size is different            - file6.txt
2018-07-01 11:41:51,514:    Remote     File was deleted                  - file7.txt
2018-07-01 11:41:51,514:    Remote     File is new                       - file10.txt
2018-07-01 11:41:51,514:       6 file change(s) on Remote:    1 new,    3 newer,    0 older,    2 deleted
2018-07-01 11:41:51,514:  >>>>> Applying changes on Remote to Local
2018-07-01 11:41:51,514:    Remote     Copying to Local                  - ./testdir/file1.txt
2018-07-01 11:41:53,530:    Remote     Copying to Local                  - ./testdir/file10.txt
2018-07-01 11:41:55,197:    Local      Deleting file                     - ./testdir/file3.txt
2018-07-01 11:41:55,207:    WARNING    Changed in both Local and Remote  - file5.txt
2018-07-01 11:41:55,207:    Remote     Copying to Local                  - ./testdir/file5.txt_Remote
2018-07-01 11:42:00,967:    Local      Renaming Local copy               - ./testdir/file5.txt_Local
2018-07-01 11:42:00,974:    WARNING    Deleted Locally and also changed Remotely - file6.txt
2018-07-01 11:42:00,974:    Remote     Copying to Local                  - ./testdir/file6.txt
2018-07-01 11:42:02,605:  >>>>> Synching Local to Remote
2018-07-01 11:42:06,234:  >>>>> rmdirs Remote
2018-07-01 11:42:06,834:  >>>>> rmdirs Local
2018-07-01 11:42:06,841:  >>>>> Refreshing Local and Remote lsl files
2018-07-01 11:42:07,653:  >>>>> Successful run.  All done.

```

## rclonesync Operations

rclonesync keeps copies of the prior sync file lists of both Local and Remote filesystems, and on a new run checks for any changes 
locally and then remotely.  Note that on some (all?) cloud storage systems it is not possible to have file timestamps 
that match between the local and cloud copies of a file.  rclonesync works around this problem by tracking Local-to-Local 
and Remote-to-Remote deltas, and then applying the changes on the other side. 

### Notable features / functions / behaviors

- The **Cloud** argument may be just the configured Remote name (i.e., `GDrive:`), or it may include a path to a sub-directory within the 
tree of the Remote (i.e., `GDrive:/Exchange`).  Leading and trailing '/'s are not required but will be added by rclonesync.  The 
path reference is identical with or without the '/'s.  The LSL files in rclonesync's working directory (default `~/.rclonesyncwd`) 
are named based on the Cloud argument, thus separate syncs to individual directories within the tree may be set up. 
Test with `--dry-run` first to make sure the Remote 
and Local path bases are as expected.  As usual, double quote `"Exchange/Paths with spaces"`.

- For the **LocalPath** argument, absolute paths or paths relative to the current working directory may be used. `rclonesync GDrive:Exchange
 /mnt/mydisk/GoogleDrive/Exchange` is equivalent to `rclonesync GDrive:Exchange Exchange` if the cwd is /mnt/mydisk/GoogleDrive.
As usual, double quote `"Exchange/Paths with spaces"`.

- rclonesync applies any changes found on the Remote filesystem to the Local filesystem first, then uses `rclone sync` to make the Remote 
filesystem match the Local.
In the tables below, understand that the last operation is to do an `rclone sync` if rclonesync had made any changes on the Local filesystem.

- Any empty directories after the sync are deleted on both the Local and Remote filesystems.

- **--first-sync** - This will effectively make both Local and Remote filesystems contain a matching superset of all files.  Remote 
files that do not exist locally will be copied locally, and the process will then sync the Local tree to the Remote. 
**NOTE that when using --first-sync a newer version of a file on the Remote filesystem will be overwritten by the Local filesystem 
version.** Carefully evaluate deltas using --dry-run.  **Note** that the base directories on both the Remote and Local filesystems 
must exist, even if empty, or rclonesync will fail.  The fix is simply to create the missing directory on both sides and rerun the
rclonesync --first-sync.

- **--check-access** - Access check files are an additional safety measure against data loss.  rclonesync will ensure it can 
find matching `RCLONE_TEST` files in the same places in the Local and Remote file systems.  Time stamps and file contents 
are not important, just the names and locations.  Place one or more RCLONE_TEST files in the Local or Remote filesystem and then 
do either a run without `--check-access` or a `--first-sync` to set matching files on both filesystems.

- **--max-deletes** - As a safety check, if greater than the --max-deletes percent of files were deleted on either the Local or
Remote filesystem, then rclonesync will abort with a warning message, without making any changes.  The default --max-deletes is 50%. 
One way to trigger this limit is to rename a directory that contains more than half of your files.  This will appear to rclonesync as a
bunch of deleted files and a bunch of new files.
This safety check is intended to block rclonesync from deleting all of the files on both the Local and Remote filesystems
due to a temporary network access issue, or if the user had inadvertently deleted the files on one side or the other.  To force the sync 
either set a different delete percentage limit, eg `--max-deletes 75` (allows up to 75% deletion), or use `--force` to bypass the check.

- **--filters-file** - Using rclone's filter features you can exclude file types or directory sub-trees from the sync. 
See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).) A
starer `Filters` file is included with rclonesync that contains filters for not-allowed files for syncing with Dropbox, and a filter
for the rclonesync test engine temporary test tree, `/testdir/`.  **NOTE:** if you make changes to your filters file then 
existing files on the Remote or Local side may magically disappear from view (since they are newly excluded in the LSL runs), which would fool
rclonesync into seeing them as deleted (as compared to the prior run LSL files), and then rclonesynce would proceed to delete them 
for real.  To block this from happening rclonesync calculates an MD5 hash of your filters file and stores the hash in a ...MD5 file
in the same
place as your filters file.  On each rclonesync run with --filters-file set, rclonesync first calculates the MD5 hash of the current
filters file and compares it to the hash stored in the ...MD5 file.  If they don't match the run aborts with a CRITICAL error and
thus forces you to do a --first-sync, likely avoiding a disaster.

- **Verbosity controls** - `--verbose` enables rclonesync's logging of each check and action (as shown in the typical run log, above). 
rclone's verbosity levels may also be enabled using the `--rc-verbose` switch.  rclone supports additional verbosity levels which may be 
enabled by providing the `--rc-verbose` switch more than once.  Turning on rclone's verbosity using `--rc-verbose` will also turn on
rclonesync's `--verbose` switch.  **Note** that rclonesync's log messages have '-'s in the date stamp (2018-06-11), while rclone's 
log messages have '/'s in the date stamp (2018/06/11).

- **Runtime Error Handling** - Certain rclonesync critical errors, such as `rclone copyto` failing, 
will result in an rclonesync lockout of successive runs.  The lockout is asserted because the sync status of the Local and Remote filesystems
can't be trusted, so it is safer to block any further changes until someone with a brain (you) check things out.
The recovery is to do a --first-sync again.  It is recommended to use --first-sync 
--dry-run --rc-verbose initially and carefully review what changes will be made before running the --first-sync without --dry-run. 
Most of these events come up due to rclone returning a non-zero status from a command.  On such a critical error 
the *_llocalLSL and *_remoteLSL files are renamed adding _ERROR, which blocks any future rclonesync runs (since the 
original files are not found).  These files may possibly be valid and may be renamed back to the non-_ERROR versions 
to unblock further rclonesync runs.  Some errors are considered temporary, and re-running the rclonesync is not blocked. 
Within the code, see usages of `return RTN_CRITICAL` and `return RTN_ABORT`.  `return RTN_CRITICAL` blocks further rclonesync runs.

- **--dry-run oddity** - The --dry-run messages may indicate that it would try to delete files on the Remote server in the last 
rclonesync step of rclone syncing the Local to the Remote.  If the file did not exist Locally then it would normally be copied to 
the Local filesystem, but with --dry-run enabled those copies didn't happen, and thus on the final rclone sync step they don't exist locally, 
which leads to the attempted delete on the Remote, blocked again by --dry-run `... Not deleting as --dry-run`.  This whole situation is an 
artifact of the --dry-run switch.  Scrutinize the proposed deletes carefully, and if they would have been copied to Local then they 
may be disregarded.

- **Lock file** - When rclonesync is running, a lock file is created (/tmp/rclonesync_LOCK).  If rclonesync should crash or 
hang the lock file will remain in place and block any further runs of rclonesync.  Delete the lock file as part of 
debugging the situation.  The lock file effectively blocks follow on CRON scheduled runs when the prior invocation 
is taking a long time.  The lock file contains the job command line and time, which may help in debug.  If rclonesync crashes with a Python
traceback please open an issue.

- **Test features** - V2.0 adds a companion testrcsync.py script.  The --workdir and --no-datetime-log switches were added to rclonesync
to support testing.  See the TESTCASES.md file.  You 
will likely want to add `- /testdir/**` to your filters-file so that normal syncs do not attempt to sync the test run temporary 
directories, which may have RCLONE_TEST miscompares in some test cases and thus trip the --check-access system.  The --check-access
mechanism is hard-coded to ignore RCLONE_TEST files beneath RCloneSync/Test.

### Usual sync checks

 Type | Description | Result| Implementation ** 
--------|-----------------|---------|------------------------
Remote new| File is new on Remote, does not exist on Local | Remote version survives | `rclone copyto` Remote to Local
Remote newer| File is newer on Remote, unchanged on Local | Remote version survives | `rclone copyto` Remote to Local
Remote deleted | File is deleted on Remote, unchanged Locally | File is deleted | `rclone delete` Local
Local new | File is new on Local, does not exist on Remote | Local version survives | `rclone sync` Local to Remote
Local newer| File is newer on Local, unchanged on Remote | Local version survives | `rclone sync` Local to Remote
Local older| File is older on Local, unchanged on Remote | Local version survives | `rclone sync` Local to Remote
Local deleted| File no longer exists on Local| File is deleted | `rclone sync` Local to Remote


### *UNusual* sync checks

 Type | Description | Result| Implementation **
--------|-----------------|---------|------------------------
Remote new AND Local new | File is new on Remote AND new on Local | Files renamed to _Local and _Remote | `rclone copyto` Remote to Local as _Remote, `rclone moveto` Local as _Local
Remote newer AND Local changed | File is newer on Remote AND also changed (newer/older/size) on Local | Files renamed to _Local and _Remote | `rclone copyto` Remote to Local as _Remote, `rclone moveto` Local as _Local
Remote newer AND Local deleted | File is newer on Remote AND also deleted Locally | Remote version survives  | `rclone copyto` Remote to Local
Remote deleted AND Local changed | File is deleted on Remote AND changed (newer/older/size) on Local | Local version survives |`rclone sync` Local to Remote
Local deleted AND Remote changed | File is deleted on Local AND changed (newer/older/size) on Remote | Remote version survives  | `rclone copyto` Remote to Local

** If any changes are made on the Local filesystem then the final operation is an `rclone sync` to update the Remote filesystem to match.

### Unhandled

 Type | Description | Comment 
--------|-----------------|---------
Remote older|  File is older on Remote, unchanged on Local | `rclone sync` will push the newer Local version to the Remote.
Local size | File size is different (same timestamp) | Not sure if `rclone sync` will pick up on just a size difference and push the Local to the Remote.


## Revision history

- V2.0 180701 Added rclonesync test capabilities. 
		Fixed corner case bug that copied a file from Remote to Local twice. 
		Changed from --ExcludeListFile to --filters-file, which requires minor adjustments to your excludes file (add a '- ' in front of your
		excludes). See [rclone Filtering documentation](https://rclone.org/filtering/#filter-from-read-filtering-patterns-from-a-file).)
		Added change detection on the filters file (MD5 hash), forcing a --first-sync in order to avoid doing damage. 
		Added --max-deletes switch for command line control of the excessive deletes feature.
		Changed rclonesync's interface to align to Linux command line standards (lower case, hypens between words).  Internally adjusted
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

- 170917  Added --Force switch - required when the % changes on Local or Remote system are grater than maxDelta.  Safeguard for
       Local or Remote not online.
       Added --ignore-times to the copy of changed file on Remote to Local.  Was not copying files with matching sizes.

- 170805  Added --verbose command line switch 

- 170730  Horrible bug - Remote lsl failing results in deleting all Local files, and then iteratively replicating _Local and _Remote files.
       Added connection test/checking files to abort if the basic connection is down.  RCLONE_TEST files on the Local system
       must match the Remote system (and be unchanged), else abort.
       Added lockfile so that a second run aborts if a first run is still in process, or failed and left the lockfile in place.
       Added python logging, sorted processing

- 170716  New


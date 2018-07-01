# Full change list for rclonesync V2

- **Linux-ification** - Changed the name of the script from RCloneSync to rclonesync, and changed to Linux standard 
command line arguments format.  Prior RCloneSync CapWords style not supported in V2.
- **Excludes --> Filters** - --ExcludesFile command line argument has been removed and replaced with --filters-file.  This change was needed in order to
support test features. User's exclude files will have to be modified to rclone's filters format.  (Simple...  add a `- ` to 
each exclude)
- **Testing** - Added a test system and a handful of tests for most of rclonesync's modes/switches.  See TESTCASES.md.
This added two switches to rclonesync:  --workdir allows the working dir (place where the LSL files are stored) to be changed 
from the default of <users_home>/.rclonesync to wherever.  --no-datetime-log suppreses the datestamp on rclonesync's log messages 
which simplifies diff testing of test run result files to the golden versions.  --workdir and --no-datetime-log are primarily
intended for testing purposes.
- **Safety from filters file edits** - Added enforcement for requiring --first-sync if the filters-file is touched. 
Initially, an MD5 of the filters file is calculated and stored in the --workdir, 
and recalculated for the current filters file and compared on each run.  If the filter file calculated MD5 differs from the stored 
MD5 it's a critical error.  Changing the filters can result is a bunch of files no longer visible, and if allowed rclonesync would
assume they were deleted, and will then proceed to really delete them.  Forcing --first-sync cleanly solves the risk.
- **Max Deletes** - The name of the varialbe changed from maxDelta to max_deletes, and a command line switch --max-deletes allows
setting the limit, default 50 (50%).  --force still works and probably best used for manual intervention.
- **Python-ification** - The code is now much closer to the PEP 8 standards.  Thanks @hildogjr for helping me find the standard.
- **Minor redundant copy bug** - The code is commented out just in case it covered some other corner case I've not thought of.  The bug
was found while developing tests.
- **Python 3 support** - I made the adjustments for Py3 support.  I've set up MiniConda and have been ping poinging between 2.7.15 and 3.6.5.
All looks good.

## Not incorporated in V2 (needs discussion)
- **Cron** support is not here.  My position is that setting up a crontab entry can have several personal variations, so trying to 
provide high flexibity from the rclonesync command line is a lot of clutter, but only providing limited settings is not sufficient.
I included a cron example in TROUBLESHOOTING.md.  Or perhaps a side tool.
- **Package-ification** - Setting up rclonesync for PiPy install support sounds great.  @deeuu, please proceed.
- **No Delete Local** - @hildogjr's `--no_local_delete` switch really only blocks the empty directory cleanup.  Even with this switch
if files are no longer on the Remote, the code will delete them from Local.  It would be difficult to not delete files on Local without 
the final rclone sync putting them back on the Remote.  Maybe a command line switch to move files to be deleted locally into 
some other directory, out of
the sync tree space.  Or did you really only want to not have local empty directories deleted?
- **Code formatting** - I've worked hard on trying to create a clean log format, with indented lines and ***** eye flags, and such.
Similarly, the code takes some liberties from PEP 8, such as longer lines, nearby line comments indented, compound statements 
on one line.  I'm following the PEP 8 comment about *foolish consistency*.
If there are important code and output formatting change needed, let's discuss.

cjn
# Troubleshooting notes 

## Reading rclone and rclonesync logs
rclonesync's log messages have dashes in the dates, such as `2018-05-26`, and rclone's log messages have slashes in the dates, 
such as `2018/05/26`. This will give you a clue on which layer is complaining.  

Here are two normal runs.  The first has one newer file on the remote.  The second has no deltas between local and remote. 
Note that all the log lines are from rclonesync.

```
2018-07-29 02:30:02,003:  ***** BiDirectional Sync for Cloud Services using rclone *****
2018-07-29 02:30:02,005:  Synching Path1  </path to local tree base/>  with Path2  <Dropbox:>
2018-07-29 02:30:16,983:     113 file change(s) on Path2:   22 new,    0 newer,    0 older,   91 deleted
2018-07-29 02:31:05,392:  >>>>> Successful run.  All done.

2018-07-29 02:00:01,705:  ***** BiDirectional Sync for Cloud Services using rclone *****
2018-07-29 02:00:01,706:  Synching Path1  </path to local tree base/>  with Path2  <Dropbox:>
2018-07-29 02:00:24,493:  >>>>> Successful run.  All done.
```

This run shows an intermittent fail.  Lines 4 and 5 are rclone messages.  Line 6 is a bubbled-up _warning_ message from rclonesync, conveying
the rclone error.  rclonesync retries each rclone command up to three times, and rclone itself retries failing commands up to three times, so there may be numerous messages in the log.  
_Since there are no final error/warning messages, the rclone failure recovered on the second try, and the overall sync was successful._

```
1: 2018-07-29 02:30:02,003:  ***** BiDirectional Sync for Cloud Services using rclone *****
2: 2018-07-29 02:30:02,005:  Synching Path1  </path to local tree base/>  with Path2  <Dropbox:>
3: 2018-07-29 02:30:16,983:     113 file change(s) on Path2:   22 new,    0 newer,    0 older,   91 deleted
4: 2018/07/29 02:30:18 ERROR : /path to local tree base/objects/af: error listing: unexpected end of JSON input
5: 2018/07/29 02:30:20 Failed to lsl: unexpected end of JSON input
6: 2018-07-29 02:30:22,723/:    WARNING  rclone lsl try 1 failed.            - Dropbox:
7: 2018-07-29 02:31:05,392:  >>>>> Successful run.  All done.
```

Rclone also has built in 3x retries.  If you run with `--rc-verbose` you'll see error and retry messages from rclone, such as shown below.
This is normal, not a bug. **If at the end of the run you see `>>>>> Successful run.  All done.` and not `Critical Error Abort` 
(as shown below) or `Error Abort` then the run was successful, and you can ignore the error messages.**
This log shows a Critical failure which requires a --first-sync to recover from - see the README.md Runtime Error Handling bullet.
```
...
2018/05/26 20:49:40 Google drive root '': Waiting for checks to finish
2018/05/26 20:49:40 Google drive root '': Waiting for transfers to finish
2018/05/26 20:49:40 Google drive root '': not deleting files as there were IO errors
2018/05/26 20:49:40 Attempt 3/3 failed with 3 errors and: not deleting files as there were IO errors
2018/05/26 20:49:40 Failed to sync: not deleting files as there were IO errors
2018-05-26 20:49:40,853/:    WARNING  rclone sync try 3 failed.           - /path to local tree base/
2018-05-26 20:49:40,853/:    ERROR    rclone sync failed.  (Line 384)     - /path to local tree base/
2018-05-26 20:49:40,879/:  ***** Critical Error Abort - Must run --first-sync to recover.  See README.md *****
```

## Run rclone commands manually 
rclonesync uses rclone lsl, copyto, moveto, delete, sync, and rmdir commands.  To solve a problem, try the operation 
manually from the console, with the rclone's --verbose switch.  Any error messages come right back to you without the big wrapper 
of rclonesync dealing with the entire sync process.  Learning what rclone is actually doing will aid you greatly in problem solving.

## Rclone bugs?
Rclone gets updated frequently.  Most revs are Beta.  Check the rclone forum (https://github.com/ncw/rclone/issues) for discussion, 
and open issues in the rclone github issues, as appropriate.  Try installing a later or older rclone rev.  A few issues have been
rclone bugs, so it does happen, and I can't do anything about it.


## Illegal filenames
Some cloud services allow characters in filenames that are not legal on the local filesystem, such as '/', ':'.  rclonesync will fail 
when attempting to copy these files to the local filesystem.  Consider renaming the offending file, or adding it to the --filters-file. 

## Running from cron
If you run rclonesync as a cron job, redirect stdout and stderr to a file.  This setup runs a sync to Dropbox
every half hour, and logs all stdout (via the `>>`) and stderr (via `2>&1`) to a log file.  

```
0,30  *  *  *  *   /<path to script>/rclonesync.py  /<path to local>/Dropbox Dropbox:  --check-access --filters-file /<path to user home>/.rclonesyncwd/Filters >> /<path to logdir>/Dropbox_runlog 2>&1
```

## Denied downloads of "infected" or "abusive" files 
Google Drive (only?) has a filter for certain file types (.exe, .apk, and ??) that by default cannot be copied from Google Drive to the local filesystem. 
Mother is trying to protect you from evil and dirty things (The Wall reference).
See (https://github.com/ncw/rclone/issues/2317).  If you are having problems, run with --verbose or with --rc-verbose to see
specifically which files are generating complaints.  If the error is `This file has been identified as malware or spam and 
cannot be downloaded.` then you **_may_** wish to add the environment variable `RCLONE_DRIVE_ACKNOWLEDGE_ABUSE=true` for GDrive rclone runs.
Eventually, rclone may support setting such switches directly in the rclone.config file for specific remotes (https://github.com/ncw/rclone/issues/661).
**_Note_** that _rclonesync_ does not (currently) support random rclone 
switches on the rclonesync command line.  Also **_Note_** that maybe there's a real problem with one of your files.  User beware.

## Google Doc files
Google docs exist as virtual files on Google Drive.  While it is possible to export a Google doc to a normal file (with .xlsx extension, for example), _it is not possible to import a normal file back into a Google document_.  See https://github.com/cjnaz/rclonesync-V2/issues/1 for
the full discussion.  Also see https://github.com/ncw/rclone/issues/1349 and https://github.com/ncw/rclone/issues/2399.  Your inputs for the best solution for handling Google docs is 
welcome.

Note that rclonesync currently ignores any Google docs.  They will show up with a length of `-1` when rclonesync issues an `rclone lsl`, and then rclonesync proceeds to flag them and ignore them.  This rclonesync run is otherwise successful:

```
2018-07-29 08:49:44,828:  ***** BiDirectional Sync for Cloud Services using rclone *****
2018-07-29 08:49:44,829:  Synching Path1  </path to local tree base/>  with Path2  <GDrive:>
2018-07-29 08:49:48,740:  Something wrong with this line (ignored) in ...__Path2LSL_new:
   <       -1 2018-07-29 08:49:30.136000000 Exchange/Test Google Doc file.docx
>
2018-07-29 08:49:50,123:  >>>>> Successful run.  All done.
```


## Running Python version 2.6?

If rclonesync crashes as follows, you are probably running an unsupported version of Python (seen on a CentOS 6 running Python 2.6.6). 
Do a secondary Python install of Python 2.7.x or 3.x.  See... Google `Python altinstall` on Linux machines (https://docs.python.org/2/using/unix.html) 
and (https://danieleriksson.net/2017/02/08/how-to-install-latest-python-on-centos/). In the bin list 
is version enforcement for graceful failure, rather than this crap:

```
2018-06-12 17:39:44,137/:  ***** BiDirectional Sync for Cloud Services using rclone *****
Traceback (most recent call last):
  File "./rclonesync.py", line 472, in <module>
    logging.error ("ERROR  rclone not installed?\nError message: {}\n".format(sys.exc_info()[1])); exit()
ValueError: zero length field name in format
```


# Writing Filters Files

See rclone's [Filtering documentation](https://rclone.org/filtering/) for how filter rules are written and interpreted!

rclonesync only uses rclone's `--filter-from` mechanism for setting up filtering.  rclone's `--include*`, `--exclude*`, and `--filter` mechanisms are not supported by rclonesync.

For a given rclonesync run you may provide _one_ `--filters-file`.


## Filtering directories

Filtering portions of the directory tree is a critical feature for synching.  

Examples of directory trees (always beneath the Path1/Path2 root level) you may want to exclude from your sync:
- Directory trees containing only software build intermediate files.
- Directory trees containing application temporary files and data such as the Windows `C:\Users\<me>\AppData\` tree.
- Directory trees containing files that are large, less important, or are getting thrashed continuously by ongoing processes.  

On the other hand, there may be only select directories that you actually want to sync, and exclude all others.  See the _Example Include-style filters files for Windows User directories_, below.


### Filters file writing guidelines

1. Begin with excluding directory trees 
	- EG: `- /AppData/`
	- `**` on the end is not necessary.  Once a given directory level is excluded then everything beneath it won't be looked at.
	- Exclude such directories that are unneeded, are big, dynamically thrashed, or where there may be access permission issues.
	- Excluding such dirs first will make rclone operations (much) faster.
    - Specific files may also be excluded, as with the Dropbox exclusions example, below.
2. Decide if its easier and/or cleaner to:
	- Include select directories and _therefore exclude everything else_ -- or -- 
	- Exclude select directories and _therefore include everything else_
3. Include Select Directories
	- Add lines like: `+ /Documents/PersonalFiles/**` to select which directories to include in the sync.
	- `**` on the end specifies to include the full depth of the specified tree.
    - With Include-style filters, files at the Path1/Path2 root are not included.  They may be included with `+ /*`.
	- Place RCLONE_TEST files within these included directory trees.  They will only be looked for in these directory trees.
    - Finish by excluding everything else by adding `- **` at the end of the filters file.
	- Disregard step 4.
4. Exclude Select Directories
	- Add more lines like in step 1.  EG: `-/Desktop/tempfiles/`, or `- /testdir/`.  Again, a `**` on the end is not necessary.
	- Do _not_ add a `- **` in the file.  Without this line, everything will be included that has not be explicitly excluded.
	- Disregard step 3.

A few rules for the syntax of a filter file (expanding on rclone's documentation):
- Any line may start with spaces and tabs (whitespace).  rclone does a lstrip() for leading whitespace.
- If the first non-whitespace character is a # then the line is a comment, and ignored.
- Blank lines are ignored.
- The first non-whitespace character on a filter line must be a `+` or `-`.
- Exactly 1 space is allowed between the `+/-` and the path term.
- Only forward slashes (`/`) are used in path terms, even on Windows.
- The rest of the line is taken as the path term.  Trailing whitespace is taken literally, and probably is an error.


## Example _Include-style_ filters files for Windows User directories

This Windows _Include-style_ example is based on the sync root (Path1) set to `C:\Users\<me>`.  The strategy is to select specific directories to be synced with a network dive (Path2).  Notable:
- `- /AppData/` excludes an entire tree of Windows stored stuff that need not be synced.  In my case, AppData has >11 GB of stuff I don't care about, and there are some subdirectories beneath AppData that are not accessible to my user login, resulting in rclonesync critical aborts.
- Windows creates cache files starting with both upper and lowercase `NTUSER` at `C:\Users\<me>`.  These files may be dynamic, locked, and are generally don't care.
- There are just a few directories with _my_ data that I do want synced, in the form of `+ /<path>`.  By selecting only the directory trees I want I avoid the dozen plus directories that various apps make at `C:\Users\<me>\Documents`.
- Include files in the root of the sync point, `C:\Users\<me>`, by adding the `+ /*` line.
- This is a Include-style filters file, therefore it ends with `- **` which excludes everything not explicitly included.
```
- /AppData/
- NTUSER*
- ntuser*
+ /Documents/Family/**
+ /Documents/Sketchup/**
+ /Documents/Microcapture_Photo/**
+ /Documents/Microcapture_Video/**
+ /Desktop/**
+ /Pictures/**
+ /*
- **
```

Note also that Windows implements several "library" links such as `C:\Users\<me>\My Documents\My Music`, which points to `C:\Users\<me>\Music`.  rclone sees these as links, so you must add `--rclone-args --links` to the rclonesync command line if you which to follow these links.  I find that I get permission errors in trying to follow the links, so I don't include the rclone --links switch, but then I get lots of `Can't follow symlink…` noise from rclone about not following the links.  This noise can be quashed by adding `--rclone-args --quiet` to the rclonesync command line.

## Example _Exclude-style_ filters files for use with Dropbox

This file is [included](https://github.com/cjnaz/rclonesync-V2/blob/master/Filters) in the rclonesync repo directory.  Notable:
- Dropbox disallows syncing the listed temporary and configuration/data files.  The `- ...` filters exclude these files where ever they may occur in the sync tree.  Consider adding similar exclusions for file types you don't need to sync, such as core dump and software build files.
- rclonesync testing creates /testdir/ at the top level of the sync tree, and usually deletes the tree after the test.  If a normal sync should run while the /testdir/ tree exists the --check-access phase may fail due to unbalanced RCLONE_TEST files.  The `- /testdir/` filter blocks this tree from being synced.  You don't need this exclusion if you are not doing rclonesync development testing.
- Everything else beneath the Path1/Path2 root will be synced.
- RCLONE_TEST files may be placed anywhere within the tree, including the root.

```
# Filter file for use with rclonesync
# See https://rclone.org/filtering/ for filtering rules
# NOTICE:  If you make changes to this file you MUST do a --FirstSetup run OR FILES WILL BE DELETED.  Run with --DryRun to see what changes will be made.

# Dropbox wont sync some files, so filtered here.  See https://www.dropbox.com/en/help/syncing-uploads/files-not-syncing
- .dropbox.attr
- ~*.tmp
- ~$*
- .~*
- desktop.ini
- .dropbox

# Used for rclonesync testing, so excluded from normal runs
- /testdir/**

# Other example filters
# /TiBU/*
# /Photos/**
```

## rclonesync's --check-access handling of the filters file (detailed reading)
For debug purposes, here are the details of how filtering is done during the `--check-access` phase. To view the `--check-access` phase constructed filters, run rclonesync with `--verbose --verbose` (yes, two of them). `--check-filename` may be used to override the default RCLONE_TEST file name.  `--keep-chkfiles` may be set to keep the LSL*CHK files in your rclonesync workdir.

Normally if there is a supplied `--filters-file` the file is directly passed along to rclone's  `--filter-from`; however, during the `--check-access` phase if there is a supplied `--filters-file` the file is _not_ passed directly to rclone, but rather it is parsed and `--filter` terms are passed to rclone as follows:
- A directory exclude line, such as `- /AppData/`, is directly passed as `--filter "- /AppData/"`
    - The filter may be alternately written as `- /AppData/*` or `- /AppData/**`.  All three syntaxes are equivalent - everything in and beneath /AppData/ is excluded by rclone.
- A directory include line, such as `+ /Documents/ABC/**`, becomes `--filter "+ /Documents/ABC/**RCLONE_TEST"`
- rclonesync test-related directories are excluded by adding `--filter "- rclonesync/Test/" --filter "- /testdir/"`.  The former is incase you have the rclonesync git tree within the sync tree, which can cause sync failures as new test cases with check files are added.  This git tree can be synced, but check files within this tree are not checked.  The latter excludes directories related to actively running test cases. 
	- If you are doing development on rclonesync you may wish to put `- /testdir/` in your filters file to avoid syncing this tree, as these are temporary/transient files (otherwise not needed).
- If your filters file does _not_ contain a `- **` line then `--filter "RCLONE_TEST"` is added to pick up check files throughout the tree, not including excluded directories.
- Lastly, `--filter "- **"` is added to eliminate all other files.

Effectively, RCLONE_TEST files are found _only_ in included directory trees, _or_ in the entire non-excluded tree if there no `- **` line in your filters file.


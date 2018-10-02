# USAGE examples

## Sharing an encrypted folder tree between hosts

rclonesync can keep a local folder in sync with a cloud service, but what if you have some highly sensitive files to be sync'd?

My usage of a cloud service is for exchanging both routine and sensitive personal files between my home network, my personal notebook when 
on the road, and with
my work computer.  The routine data is not sensitive.  I have configured an rclone Crypt (https://rclone.org/crypt/) "remote" to point 
to a subdirectory within the local disk tree that I rclonesync to Dropbox:.  I then set up an rclonesync for this local crypt directory to 
a directory outside of main sync tree.

### The setup looks like this on my local Linux server:
- `/mnt/somepath/DBoxroot` is the root of my local sync tree.  There are numerous subdirectories.
- `/mnt/somepath/DBoxroot/crypt` is the root subdirectory for files that are encrypted.  This local directory target is setup as
an rclone crypt "remote" named Dropcrypt:.  See rclone.conf snip below.
- `/mnt/somepath/myUnencryptedFiles` is the root of my sensitive files - not encrypted, not within the tree synced to Dropbox, and SAMBA
shared on my LAN.
- To sync my local unencrypted files with the encrypted Dropbox versions I manually run 
`rclonesync.py /mnt/somepath/myUnencryptedFiles Dropcrypt:`.  (Note **)
- `rclonesync.py /mnt/somepath/DBoxroot Dropbox:` runs periodically via cron, keeping my full local sync tree in sync with Dropbox.

Note **:  This step could be bundled into a script to run before and after the full Dropbox tree sync in the last step, thus actively 
keeping the sensitive files in sync.

### The setup looks like this on my Windows notebook (which is not always at home on my LAN):
- The Dropbox client runs, keeping the full local tree `C:\Users\<me>\Dropbox` always in sync with Dropbox.  I could have used 
rclone/rclonesync instead.
- A separate directory tree at `C:\Users\<me>\Documents\DropLocal` hosts the tree of unencrypted files/folders.
- To sync my local unencrypted files with the encrypted Dropbox versions I manually run 
`rclonesync.py C:\Users\<me>\Documents\DropLocal Dropcrypt:`.
- The Dropbox client then syncs the changes with Dropbox.

### rclone.conf snip:
```
[Dropbox]
type = dropbox
...

[Dropcrypt]
type = crypt
remote = /mnt/somepath/DBoxroot/crypt  << Looks like this on the Linux server
remote = C:\Users\<me>\Dropbox\crypt   << Looks like this on my Windows notebook
filename_encryption = standard
directory_name_encryption = true
password = ...
...
```

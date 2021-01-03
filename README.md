# Paper Storage

Create paper backups for arbitrary data that are recoverable by simple means, even without this software.
Can be used as a standalone tool or integrated as a module.

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e2215b5bf74e45d4a7bfb5eff5c41ba3)](https://app.codacy.com/gh/schroeding/paperstorage?utm_source=github.com&utm_medium=referral&utm_content=schroeding/paperstorage&utm_campaign=Badge_Grade) [![Codacy Badge](https://app.codacy.com/project/badge/Coverage/bd3aeab0a9d74e1183e7e5788ff13335)](https://www.codacy.com/gh/schroeding/paperstorage/dashboard?utm_source=github.com&utm_medium=referral&utm_content=schroeding/paperstorage&utm_campaign=Badge_Coverage) [![PyPI version](https://badge.fury.io/py/paperstorage.svg)](https://badge.fury.io/py/paperstorage)

You can find a sample PDF as [sample.pdf](https://github.com/schroeding/paperstorage/blob/master/sample.pdf) in this repository.

## Installation

```bash
python -m pip install paperstorage
```

If you want to try the webcam restore feature, you also need to install pyGame:
```bash
python -m pip install paperstorage[full]
```

## Usage

### As a standalone tool

Create a backup from a file on disk:
```bash
python -m paperstorage -f <inputfile> -o <outputfile>
```

Create a backup from any output of other applications:
```bash
otherapplication | python -m paperstorage -id <identifier> -o <outputfile>
```

Restore backups:
```bash
python -m paperstorage --interactiverestore
```

Example: Create a GPG private key backup in the US Letter format:
```
gpg --export-secret-key 789C2CE9916081FEA9E134E9C310E13C02D32624 | python -m paperstorage -id 'GPG Key' -format Letter -o gpgbackup.pdf
```

### As a module

```python
from paperstorage import PaperStorage

# Create a backup from file
ps = PaperStorage.fromFile('inputfile')
ps.savePDF('outputfile')

# Create a backup from bytes
ps = PaperStorage(someBytesObject)
ps.savePDF('outputfile')

# Restore a backup with your own QR-Code reading code
ps = PaperStorage()
while (not ps.isDataReady()):
	qrString = # ... your QR-Code reading code goes here
	ps.restoreFromQRString(qrString)
restoredData = ps.getData()

# Restore a backup from scans / images inside a folder
ps = PaperStorage()
if (ps.restoreFromFolder('folderpath')):
	# ... backup restored!
else:
	# ... some blocks missing, you can fetch a list of them using getMissingBlocks()
```
## Paper Storage Format

### Structure of the first page (metadata)

In addition to the three available recovery methods, the first page contains all the information necessary for recovery in the upper third of the page. The QR-Code contains the following metadata:

```
hcpb01,[document id in Base64],[identifier in Base64],[size of restored data as string],[size of datablocks as string],[SHA256 hash of restored data as string].
```

"hcpb01" serves as the Magic Number of the metadata block. The document id is a random unsigned 16-bit integer to prevent any backup mix-up. The SHA256 hash can be used to verify the integrity of the restored backup.

In addition to the QR code, other meta information that is not required for the restore process, such as the date of the backup, the host name and a CRC32 value, is printed in human-readable form only.

With the help of the information printed onto this first page, it should be possible to restore any backup even in the very distant future.

### Structure of the other pages (data block)

By default a data block is 1.5 KiB in size and fills exactly one A4 / Letter page. It consists of a QR-Code (version 31) and up to 30 lines of data encoded with Base32. The latter serves as a human-readable alternative should machine reading fail; both contain basically the same data block.

The QR code encodes the following information:

```
[block id in Base64][document id in Base64][block data in Base64].
```

The block and document id are unsigned 16-bit integers (big endian), i.e. 2 bytes in size.

The block id starts at 0 and is consecutive. It corresponds to the current page number minus 2.

The document id corresponds to the document ID of the first page and is the same in all blocks of a backup.

The human readable lines below the QR-Code encode the following information:

```
[line number][80 characters of Base32 encoded data][CRC32 of the decoded data in Base85].
```

The line number always has two characters. The 80 characters of Base32 encoded data are divided into ten blocks for easier . At the end of each line there is a CRC32 checksum of the decoded data of the line (50 bytes) encoded in Base85. It can be used for a more convenient, line-by-line integrity check - calculate the checksum of the line entered by the user, display the checksum so the user can compare the two.

### Design decisions

The format chosen is extremely inefficient with a maximum of 3 KiB per sheet of paper. [PaperBak](http://ollydbg.de/Paperbak/) by Oleh Yuschuk is a *way* better choice if efficiency is a major concern.
However, efficiency is not the goal of these backups - the goal is longevity and robustness for small files like e.g. SSH private keys.

In principle, these backups should be restorable with more or less little effort and simple technical means, even if this application, with which they were created, has long since ceased to run. In principle, even a manual restore is possible in an emergency. The short unix shell script on the first page allows for automatic recovery by scan (as long as zbar is available) and the python script below for a more convenient input of the Base32 strings, with Base85 checksums for each line.


## License

[Mozilla Public License 2.0](https://choosealicense.com/licenses/mpl-2.0/)
# Paper Storage

Create paper backups for arbitrary data that are recoverable by simple means, even without this software.
Can be used as a standalone tool or integrated as a module.

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e2215b5bf74e45d4a7bfb5eff5c41ba3)](https://app.codacy.com/gh/schroeding/paperstorage?utm_source=github.com&utm_medium=referral&utm_content=schroeding/paperstorage&utm_campaign=Badge_Grade) [![Codacy Badge](https://app.codacy.com/project/badge/Coverage/bd3aeab0a9d74e1183e7e5788ff13335)](https://www.codacy.com/gh/schroeding/paperstorage/dashboard?utm_source=github.com&utm_medium=referral&utm_content=schroeding/paperstorage&utm_campaign=Badge_Coverage)

## Installation

```bash
python -m pip install paperstorage
```

## Usage

### As a standalone tool

Create backup from a file on disk:
```bash
python -m paperstorage -f <inputfile> -o <outputfile>
```

Create backup from any output of other applications:
```bash
otherapplication | python -m paperstorage -id <identifier> -o <outputfile>
```

Restore backups:
```bash
python -m paperstorage --interactiverestore
```

### As a module

```python
from paperstorage import PaperStorage


```

## License

[Mozilla Public License 2.0](https://choosealicense.com/licenses/mpl-2.0/)
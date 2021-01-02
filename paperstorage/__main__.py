import argparse
import sys
from paperstorage import PaperStorage

def main(argv) -> None:
	"""Main method to start paperstorage in interactive mode / from the console (python -m paperstorage)
	Do not use if you want to use paperstorage as a module.

	Takes arguments, returns nothing
	"""
	parser = argparse.ArgumentParser('paperstorage')
	parser.add_argument('-o', dest='outputFilename', default='backup.pdf', help='filename to write output PDF file to', required=False)
	parser.add_argument('-f', dest='inputFilename', help='read the specified file, otherwise stdin', required=False)
	parser.add_argument('-id', dest='identifier', help='identifier that will be printed on the backup file', required=False)
	parser.add_argument('--format', dest='format', choices=['A4','Letter'], default='A4', type=str, help='uses the specified format for the output PDF file')
	parser.add_argument('--force-from-stdin', dest='forceStdin', action='store_true', default=False, help='forces a read from stdin, even with no piped data available', required=False)
	parser.add_argument('--interactive-restore', dest='interactiveRestore', action='store_true', default=False, help='starts an interactive restore of a backup', required=False)
	parser.add_argument('-b', dest='blocksize', choices=range(50, 1501, 50), metavar='[50-1500]' ,type=int, default=1500, help='use a custom block size between 50 bytes and (the default) 1500 bytes', required=False)
	arguments = parser.parse_args(argv)

	_ps = None
	if (arguments.format == 'Letter'):
		_format = PaperStorage.LETTER
	else:
		_format = PaperStorage.A4

	if (arguments.inputFilename != None):
		try:
			_ps = PaperStorage.fromFile(arguments.inputFilename,
			blockSize=arguments.blocksize,
			identifier=arguments.identifier,
			size=_format)
		except (ValueError):
			print('Cannot open the specified input file.')
			return
	elif ((not sys.stdin.isatty()) or (arguments.forceStdin)):
		_ps = PaperStorage(bytes(sys.stdin.buffer.read()),
			blockSize=arguments.blocksize,
			identifier=arguments.identifier,
			size=_format)
	else:
		parser.print_help()
		return
		
	_ps.savePDF(arguments.outputFilename)


main(sys.argv[1:])
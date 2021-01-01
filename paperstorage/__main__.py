import argparse
import sys
from paperstorage import PaperStorage

def main(argv) -> None:
	"""
	Main method to start paperstorage in interactive mode / from the console
	Do not use if you want to use paperstorage as a module.

	Takes arguments, returns nothing
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument('-o', dest='outputFilename', default='backup.pdf', help='filename to write output PDF file to', required=False)
	parser.add_argument('-f', dest='file', help='TODO TODO TODO read the specified file, otherwise stdin', required=False)
	parser.add_argument('-id', dest='id', help='identifier that will be printed on the backup file', required=False)
	parser.add_argument('--force-from-stdin', action='store_true', default=False, help='forces a read from stdin, even with no piped data available', required=False)
	parser.add_argument('--interactive-restore', dest='interactiverestore', action='store_true', default=False, help='starts an interactive restore of a backup', required=False)
	parser.add_argument('-b', dest='blocksize', choices=range(500, 1501, 50), type=int, default=1536, help='use a custom block size between 512 bytes and (the default) 2048 bytes', required=False)
	arguments = parser.parse_args(argv)

	_ps = None

	if (arguments.file != None):
		raise NotImplementedError('TODO')
	elif ((not sys.stdin.isatty()) or (arguments.force_from_stdin)):
		_ps = PaperStorage(bytes(sys.stdin.buffer.read()))
	else:
		parser.print_help()

	_ps.savePDF(arguments.outputFilename)


main(sys.argv[1:])
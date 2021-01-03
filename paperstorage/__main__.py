import argparse
import sys
import os
import hashlib
from paperstorage import PaperStorage
try:
	import PIL
	import PIL.ImageOps
except (ImportError):
	print('PIL / pillow is not installed, but required to restore backups. Please install it with \'python -m pip install pillow\'')
	quit()
try:
	import pyzbar.pyzbar as pyzbar
except (ImportError):
	print('pyzbar is not installed, but required to restore backups. Please install it with \'python -m pip install pyzbar\'')
	quit()


def __interactiveSave(_ps: PaperStorage) -> None:
	if (_ps._sha256 != hashlib.sha256(_ps.getData()).hexdigest()):
		print(f'\nYour backup of \'{_ps._identifier}\' was restored, but something went wrong. (hash mismatch)\nThis should never happen. Please try to rescan all files into a fresh folder.\nYour file will still be saved, but is probably corrupt.')
	else:
		print(f'\nThat worked, your backup of \'{_ps._identifier}\' was restored completly!')
	while (True):
		_filename = input('Please choose a filename to save the restored file to: ')
		try:
			_file = open(_filename, 'wb+')
		except (Exception):
			print('Could not save the data to the specified filename. Please try something else.')
		break
	_file.write(_ps.getData())
	_file.close()

def __interactiveFolder(_ps: PaperStorage) -> None:
	while (True):
		_folder = input('\nPlease enter the path of the folder you just saved the scans to: ')
		if (os.path.isdir(_folder)):
			break
		print('The path specified is not a folder or does not exist. Please try again.')
	_ps.restoreFromFolder(_folder)
	while (not _ps.isDataReady()):
		if (_ps.getMissingDataBlocks() == []):
			print(f'\nNo valid QR-Codes found. Try making sure the folder name (\'{_folder}\') is correct.\nOtherwise try rescanning the pages with a higher quality setting and try again.')
			quit()
		print(f'\nThe backup could not be restored completly. Page(s) {",".join([str(n+2) for n in _ps.getMissingDataBlocks()])} must be rescanned.')
		input('Please rescan the listed pages and save them to the same folder as before. Press [Enter] when you are done. ')
		_ps.restoreFromFolder(_folder)
	__interactiveSave(_ps)


def __interactiveWebcam(_ps: PaperStorage) -> None:
	try:
		print('')
		import pygame.camera
	except (ImportError):
		print('Webcam restore uses PyGame to fetch webcam images, but PyGame is not installed. Please install it using \'python -m pip install pygame\' and try again.')
		exit()
	input('\nPress [Enter] to enable your webcam and to start the restore process. ')

	pygame.camera.init()
	_cameras = pygame.camera.list_cameras()

	if (len(_cameras) < 1):
		print('\nNo webcam found. PyGame only supports certain cameras, so it\'s possible your webcam is not supported.')
		exit()

	_webcam = pygame.camera.Camera(_cameras[0], (1920, 1080), 'RGB')
	_webcam.start()
	_webcamWidth, _webcamHeight = _webcam.get_size()

	print(f'\nUsing webcam \'{_cameras[0]}\' with resolution of {_webcamWidth} x {_webcamHeight}')
	_ps = PaperStorage()

	print('Please hold the first page into your webcam...\n(Press [CTRL] + [C] to abort)')

	_lastCode = str()
	_pageRead = False

	while (not _pageRead):
		try:
			_image = PIL.Image.frombytes('RGB', (_webcamWidth, _webcamHeight), pygame.image.tostring(_webcam.get_image(), 'RGB', False))
			_bwImage = PIL.ImageOps.grayscale(PIL.ImageOps.posterize(PIL.ImageOps.autocontrast(_image), 2))
			for n in (pyzbar.decode(_image) + pyzbar.decode(_bwImage)):
				if (n.data.decode('ascii') == _lastCode): continue
				_lastCode = n.data.decode('ascii')
				if (n.data.decode('ascii')[:6] != 'hcpb01'):
					print('\nQR-Code detected, but this is not the first page.\nPlease hold the first page in front of your webcam...')
					continue
				_ps.restoreFromQRString(n.data.decode('ascii'))
				print(f'\nFirst page read! Restoring file \'{_ps._identifier}\' with {_ps._amountOfBlocks + 1} pages')
				_pageRead = True
		except (KeyboardInterrupt):
			quit()

	try:
		for i in _ps.getMissingDataBlocks():
			print(f'\nPlease hold page {i + 2} in front of the webcam...')
			_pageRead = False
			while (not _pageRead):
				_image = PIL.Image.frombytes('RGB', (_webcamWidth, _webcamHeight), pygame.image.tostring(_webcam.get_image(), 'RGB', False))
				_bwImage = PIL.ImageOps.grayscale(PIL.ImageOps.posterize(PIL.ImageOps.autocontrast(_image), 2))
				for n in (pyzbar.decode(_image) + pyzbar.decode(_bwImage)):
					if (n.data.decode('ascii') == _lastCode): continue
					_lastCode = n.data.decode('ascii')
					_ps.restoreFromQRString(n.data.decode('ascii'))
					if (i in _ps.getMissingDataBlocks()):
						print(f'\nQR-Code detected, but this is not page {i + 2}.\nPlease hold page {i + 2} in front of the webcam...')
						continue
					print(f'\nPage {i + 2} read!')
					_pageRead = True
	except (KeyboardInterrupt):
		quit()

	_webcam.stop()

	__interactiveSave(_ps)


def main() -> None:
	"""Main method to start paperstorage in interactive mode / from the console (python -m paperstorage)

	Do not use if you want to use paperstorage as a module.
	Takes arguments, returns nothing
	"""
	parser = argparse.ArgumentParser('paperstorage')
	parser.add_argument('-o', dest='outputFilename', metavar='filename', default='backup.pdf', help='filename to write to', required=False)
	parser.add_argument('-f', dest='inputFilename', metavar='filename', help='read the specified file, otherwise stdin', required=False)
	parser.add_argument('-id', dest='identifier', metavar='identifier', help='identifier that will be printed on the backup file', required=False)
	parser.add_argument('-format', dest='format', choices=['A4','Letter'], default='A4', type=str, help='uses the specified format for the output PDF file')
	parser.add_argument('--force-from-stdin', dest='forceStdin', action='store_true', default=False, help='forces a read from stdin, even with no piped data available', required=False)
	parser.add_argument('-restore', dest='restore', metavar='folder_path' ,default=None, type=str, help='restores a backup from scanned images inside a folder', required=False)
	parser.add_argument('--interactiverestore', dest='interactiveRestore', action='store_true', default=False, help='starts an interactive restore of a backup', required=False)
	parser.add_argument('-b', dest='blocksize', choices=range(50, 1501, 50), metavar='{50-1500}', type=int, default=1500, help='use a custom block size between 50 bytes and (the default) 1500 bytes', required=False)
	arguments = parser.parse_args(argv)

	argv = sys.argv[1:]
	_ps = None

	if (arguments.interactiveRestore):
		
		print('Please select one of the following options:\n\n'\
			'1) I\'ve already scanned all pages of a backup to images and want to restore the file\n'\
			'2) I want to try reading a backup using my webcam (experimental)\n'\
			'3) I\'m here because my backup said so, please guide me step-by-step\n'\
			'0) Quit\n')

		_ps = PaperStorage()

		_choice = None

		while (True):
			try:
				_choice = abs(int(input('Please enter the number of your choice (0-3): ')))
				if (_choice <= 3):
					break
			except (ValueError):
				print('Please enter a number from 0 to 3')
			except (KeyboardInterrupt, EOFError):
				break

		if (_choice == 1):
			__interactiveFolder(_ps)

		elif (_choice == 2):
			__interactiveWebcam(_ps)

		elif (_choice == 3):
			if (input('\nDo you have a (working) scanner nearby? (yes / no) ').startswith('y')):
				print('\nPlease make sure you have all pages of the backup ready.\nCreate a single scan of every page and save all scans in a single folder on this computer.\n')
				input('Press [Enter] when you are done. ')
				__interactiveFolder(_ps)
			else:
				if (input('Do you have a smartphone nearby? (yes / no) ').startswith('y')):
					print('\nPlease make sure you have all pages of the backup ready.\nCreate a single photo of the QR-Code of every page. Try to maximize the size of the QR-Code without cutting anything off.\nTransfer all images to a single folder on this computer.\n')
					input('Press [Enter] when you are done. ')
					__interactiveFolder(_ps)
				else:
					if (input('Does your computer have a webcam and are you willing to use it to scan the pages? (yes / no) ').startswith('y')):
						__interactiveWebcam(_ps)
					else:
						print('\nYou have to use some other measure to make pictures of every page of the backup.\nPlease do so and save the resulting images into a single folder on this computer.\n')
						input('Press [Enter] when you are done. ')
						__interactiveFolder(_ps)

	elif (arguments.restore != None):

		_ps = PaperStorage()

		if (not os.path.isdir(arguments.restore)):
			print('Invalid path specified')
			quit()

		_ps.restoreFromFolder(arguments.restore)
		if (not _ps.isDataReady()):
			if (_ps.getMissingDataBlocks() == []):
				print('No data blocks found, doublecheck the path and try rescanning the pages')
				quit()
			else:
				print(f'Some data blocks missing. Page(s) {",".join([str(n+2) for n in _ps.getMissingDataBlocks()])} are missing / unreadable\nRescan these pages and try again.')
				quit()
		if (arguments.outputFilename == 'backup.pdf'): arguments.outputFilename = (_ps._identifier if (_ps._identifier != None) else 'restored_file')
		try:
			_file = open(arguments.outputFilename, "wb")
		except (Exception):
			print(f'Could not write to \'{arguments.outputFilename}\'!')
			quit()
		_file.write(_ps.getData())
		_file.close()
		print(f'Saved restored file to \'{arguments.outputFilename}\'')

	else:

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

		if (arguments.outputFilename[-4:] != '.pdf'): arguments.outputFilename += '.pdf'

		if (_ps.savePDF(arguments.outputFilename)):
			print(f'Saved backup as \'{arguments.outputFilename}\'')
		else:
			print(f'Could not write to \'{arguments.outputFilename}\'!')


main()
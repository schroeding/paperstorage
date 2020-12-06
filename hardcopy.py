import sys
import argparse
import datetime
import base64
import binascii
import qrcode
from qrcode.image import svg
import reportlab
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

_fontsize = 8
_border = 24.5 * mm

def _readFromStdIn() -> list[bytes]:
	readData = sys.stdin.buffer.read()
	return bytes(readData)

def main(argv: list) -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument('-o', dest='output', default='backup.pdf', help='filename to write output PDF file to', required=False)
	parser.add_argument('-f', dest='file', help='TODO TODO TODO read the specified file, otherwise stdin', required=False)
	parser.add_argument('-id', dest='id', help='identifier that will be printed on the backup file', required=False)
	parser.add_argument('--force-from-stdin', action='store_true', default=False, help='forces a read from stdin, even with no piped data available', required=False)
	parser.add_argument('-b', dest='blocksize', choices=[512, 1024, 2048], type=int, default=2048, help='use a custom block size between 512 bytes and (the default) 2048 bytes', required=False)
	arguments = parser.parse_args(argv)

	data = None

	if (arguments.file != None):
		print('TODO')
		raise NotImplementedError
	elif ((not sys.stdin.isatty()) or (arguments.force_from_stdin)): # isatty() => Script runs in interactive terminal
		data = _readFromStdIn()
	else:
		parser.print_help()
		return

	assert(data != None)

	id = arguments.id

	if (id == None):
		if (arguments.file != None):
			print("TODO")
			raise NotImplementedError
		else:
			id = ("Backup of " + str(len(data)) + " byte file")
		
	assert(id != None)

	print("Read " + str(len(data)) + " bytes")
	
	blockSize = arguments.blocksize
	requiredBlocks = len(data) // blockSize
	if ((len(data) % blockSize) != 0): requiredBlocks += 1

	print("Using " + str(requiredBlocks) + " block(s) with " + str(blockSize) + " bytes")

	document = canvas.Canvas(arguments.output, pagesize=reportlab.lib.pagesizes.A4)
	document.setAuthor("hardcopy.py")
	document.setCreator("hardcopy.py")
	document.setProducer("hardcopy.py")
	document.setTitle("Hardcopy Paper Backup")

	documentpages = [];

	for i in range(requiredBlocks):
		print("Creating page " + str(i+1) + " of " + str(requiredBlocks) + " ...")
		document.setFont("Courier", _fontsize)
		document.setLineWidth(0.4)

		print("\t... Writing header and footer ...")
		# Header -> page number
		document.drawString(_border, A4[1] - (25 + _fontsize), "Hardcopy Paper Backup")
		document.drawRightString(A4[0] - _border, A4[1] - (25 + _fontsize), "Page " + str(i+1) + " of " + str(requiredBlocks))
		document.line(_border, A4[1] - (30 + _fontsize), A4[0] - _border, A4[1] - (30 + _fontsize))

		# Footer -> id (filename or something else)
		document.drawString(_border, 25, id)
		document.drawRightString(A4[0] - _border, 25, "Created on " + str(datetime.date.today()))
		document.line(_border, 30 + _fontsize, A4[0] - _border, 30 + _fontsize)

		print("\t... Creating QR-Code ...")
		dataBlock = data[(i * blockSize) : ((i+1) * blockSize)]
		b64EncodedDataBlock = base64.b64encode(dataBlock)

		qr = None

		try:
			qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_Q, border=0, box_size=32)
			qr.add_data(b64EncodedDataBlock)
			qr.make(True);
			print("\t\t... using Error Correction Level Q (25% recoverable)")
		except (qrcode.exceptions.DataOverflowError):
			qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L, border=0, box_size=32)
			qr.add_data(b64EncodedDataBlock)
			qr.make(True);
			print("\t\t... using Error Correction Level L (7% recoverable)")

		assert(qr != None)

		qrAsImage = ImageReader(qr.make_image().get_image())
		document.drawImage(
			qrAsImage, _border + 60,
			A4[1] - (36.5 + _fontsize + (A4[0] - (2 * _border + 120))),
			A4[0] - (2 * _border + 120),
			A4[0] - (2 * _border + 120))

		print("\t... Writing bytes to file ...")

		b32EncodedDataBlock = base64.b32encode(dataBlock)

		requiredLines = len(b32EncodedDataBlock) // 80 # 80 => number of chars per line (actually 84, but 4 chars are for crc16)
		if ((len(b32EncodedDataBlock) % 80) != 0): requiredLines += 1 # max blocksize 2048 -> base32 -> 3280 chars / 80 = 41 lines max

		for lineCount in range(requiredLines):
			lineData = b32EncodedDataBlock[(lineCount * 80) : ((lineCount+1) * 80)]
			line = ""
			for blockCount in range(10):
				block = lineData[(blockCount * 8) : ((blockCount+1) * 8)].decode('ascii')
				line += f"{block} "
			document.drawString(_border, A4[1] - (396 + ((_fontsize + 2) * lineCount)), line) # TODO: Replace magic number 396px with dynamic stuff

			# crc over the base data, NOT the encoded base32 one

			crc32 = base64.b85encode(binascii.crc32(base64.b32decode(lineData)).to_bytes(4, byteorder='big'))
			document.setFillAlpha(0.5)
			document.drawRightString(A4[0] - _border, A4[1] - (395 + ((_fontsize + 2) * lineCount)), crc32)
			document.setFillAlpha(1)

		document.showPage()

	print("Paper backup creation successful! Saving output to " + arguments.output)
	document.save()

	return


if (__name__ == "__main__"):
	main(sys.argv[1:])
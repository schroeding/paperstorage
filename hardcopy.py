import sys
import argparse
import datetime
import base64
import binascii
import socket # socket is only required to recieve the hostname of the system
import qrcode
from qrcode.image import svg
import pyzbar # pyzbar is only required for reading / restoring a backup
import reportlab
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

_fontsize = 8
_border = 22 * mm

def _readFromStdIn() -> list[bytes]:
	readData = sys.stdin.buffer.read()
	return bytes(readData)

def _printTextToDocument(document: canvas, xpos: int, ypos: int, text: str) -> canvas:
	lines = text.splitlines(False)
	for i in range(len(lines)):
		document.drawString(xpos,  A4[1] - (ypos + (_fontsize + 3) * i), lines[i])
	return document

def main(argv: list) -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument('-o', dest='output', default='backup.pdf', help='filename to write output PDF file to', required=False)
	parser.add_argument('-f', dest='file', help='TODO TODO TODO read the specified file, otherwise stdin', required=False)
	parser.add_argument('-id', dest='id', help='identifier that will be printed on the backup file', required=False)
	parser.add_argument('--force-from-stdin', action='store_true', default=False, help='forces a read from stdin, even with no piped data available', required=False)
	parser.add_argument('--interactive-restore', dest='interactiverestore', action='store_true', default=False, help='starts an interactive restore of a backup', required=False)
	parser.add_argument('-b', dest='blocksize', choices=range(512, 2049, 512), type=int, default=2048, help='use a custom block size between 512 bytes and (the default) 2048 bytes', required=False)
	arguments = parser.parse_args(argv)

	data = None

	if (arguments.file != None):
		print('TODO')
		raise NotImplementedError
	elif ((not sys.stdin.isatty()) or (arguments.force_from_stdin)):
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

	assert(requiredBlocks <= 65535) # block number is saved as short in qr code, we cannot create more blocks
	# TODO: replace with nicer check

	print("Using " + str(requiredBlocks) + " block(s) with " + str(blockSize) + " bytes")

	document = canvas.Canvas(arguments.output, pagesize=reportlab.lib.pagesizes.A4)
	document.setAuthor(id)
	document.setCreator("hardcopy.py")
	document.setProducer(socket.gethostname())
	document.setTitle(f"Hardcopy Paper Backup - {id}")

	# First page with restoration info + metainformation

	document.setFont("Courier", _fontsize)
	document.setLineWidth(0.4)

	document.drawString(_border, A4[1] - (25 + _fontsize), "Hardcopy Paper Backup")
	document.drawRightString(A4[0] - _border, A4[1] - (25 + _fontsize), "Page 1 of " + str(requiredBlocks + 1))
	document.line(_border, A4[1] - (30 + _fontsize), A4[0] - _border, A4[1] - (30 + _fontsize))

	document.drawString(_border, 25, id)
	document.drawRightString(A4[0] - _border, 25, "Created on " + str(datetime.date.today()))
	document.line(_border, 30 + _fontsize, A4[0] - _border, 30 + _fontsize)

	document.setFont("Courier-Bold", _fontsize * 1.2)
	document.drawCentredString(A4[0] // 2, A4[1] - (50 + (_fontsize * 1.2)), "This document contains a hardcopy paper backup of binary data")
	document.setFont("Courier", _fontsize * 1.2)
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 3), "Identifier (e.g. filename): " + id)
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 4), "Size of binary data:        " + str(len(data)) + " bytes")
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 5), "Date of backup:             " + str(datetime.date.today()))
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 6), "Backup created on:          " + socket.gethostname())

	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 8), "Block size used for backup: " + str(blockSize) + " bytes")
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 9), "Amount of blocks used:      " + str(requiredBlocks))
	document.drawString(_border + 130, A4[1] - (55 + (_fontsize * 1.2 + 2) * 10), "CRC32 of restored data:     " + hex(binascii.crc32(data)))
	
	qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_Q, border=0, box_size=32)
	qr.add_data("hcpb01," + base64.b64encode(bytes(id, 'utf-8')).decode('ascii') + "," + str(len(data)) + "," + str(blockSize)) # TODO: Auslagern, alles spaghetticode hier
	qr.make(True);

	qrAsImage = ImageReader(qr.make_image().get_image())
	document.drawImage(qrAsImage,
		_border + 15,
		A4[1] - 175,
		100,
		100)
		
	document.drawCentredString(A4[0] // 2,  A4[1] - (58 + (_fontsize * 1.2 + 2) * 12), "To restore this backup, follow one of the following restore methods:")
	document = _printTextToDocument(document, _border, 230, "1) Read the QR-Codes with Hardcopy Paper Backup\n\n"\
		"   Scan all pages (including this one) with any kind of scanner available to\n"\
		"   you and save the scans as images on your computer. Use 'python -m hardcopy'\n"\
		"   with the '-interactive-restore' argument and follow the instructions to to start the restore process.\n\n"\
		\
		"2) Read the QR-Codes manually\n\n"\
		"   Scan all pages (except this one) with any kind of scanner available to you\n"\
		"   and save the scans as image files on your computer. Use any available QR-Code\n"\
		"   reader to save the indivdual base64 blocks. Use any available base64 decoder\n"\
		"   to convert the encoded data blocks into binary data blocks. Concatenate the\n"\
		"   data blocks in the correct order to restore the original binary file.\n"\
		"   The integrity of the backup can be verified using the given CRC32 value above.\n\n"\
		\
		"3) Manual backup restoration\n\n"\
		"   On each page, below the QR-Code, the data block is also printed in base32.\n"\
		"   Every line contains up to 80 characters of base32 encoded data, printed in\n"\
		"   8 character chunks for enhanced readability. At the end of each line, five\n"\
		"   (grey) characters provide a Ascii85 encoded CRC32 checksum for the decoded\n"\
		"   data of the line, allowing individual verification of each line. \n"\
		"   are not strictly necessary for a successful backup restoration yadayadayada TODO\n")


	document.setFont("Courier-Oblique", _fontsize)
	document = _printTextToDocument(document, _border, 560, "import base64, sys, math, binascii\n"
		"from base64 import b85encode, b32decode\n"
		"dS, bS, eD = int(input('size of binary data: ')), int(input('block size used for backup: ')), ''\n"
		"rB = (dS // bS)\n"
		"if (dS % bS != 0): rB += 1\n"
		"for i in range(rB):\n"
		"   print(f'page {i + 2} of {rB + 1}')\n"
		"   if (((dS - (bS * i)) // bS) >= 1): rB, pD = math.ceil((bS * 8 + 4) / 5), ''\n"
		"   else: rB, pD = math.ceil(((dS - (bS * i)) * 8 + 4) / 5), ''\n"
		"   for n in range(math.ceil(rB / 80)):\n"
		"      lD, nL = '', False\n"
		"      while (not nL):\n"
		"         lD = input(f'input line {n + 1} of {math.ceil(rB / 80)}: ').upper().replace(' ','')\n"
		"         try:\n"
		"            c32 = b85encode(binascii.crc32(b32decode(lD)).to_bytes(4, byteorder='big'))\n"
		"         except (binascii.Error):\n"
		"            print('invalid line, restart')\n"
		"            continue\n"
		"         if (input(f'crc32 is {c32.decode(\"utf-8\")}, ok? ')!='no'): nL = True\n"
		"      pD += lD\n"
		"   eD += pD\n"
		"(open(input('enter filename: '), 'wb+').write(base64.b32decode(eD)))")

	document.setFont("Courier", _fontsize)
	document.showPage()

	# ... and data pages following

	#documentpages = [];

	for i in range(requiredBlocks):
		print("Creating page " + str(i+1) + " of " + str(requiredBlocks) + " ...")
		document.setFont("Courier", _fontsize)
		document.setLineWidth(0.4)

		print("\t... Writing header and footer ...")
		# Header -> page number
		document.drawString(_border, A4[1] - (25 + _fontsize), "Hardcopy Paper Backup")
		document.drawRightString(A4[0] - _border, A4[1] - (25 + _fontsize), "Page " + str(i+2) + " of " + str(requiredBlocks + 1))
		document.line(_border, A4[1] - (30 + _fontsize), A4[0] - _border, A4[1] - (30 + _fontsize))

		# Footer -> id (filename or something else)
		document.drawString(_border, 25, id)
		document.drawRightString(A4[0] - _border, 25, "Created on " + str(datetime.date.today()))
		document.line(_border, 30 + _fontsize, A4[0] - _border, 30 + _fontsize)

		print("\t... Creating QR-Code ...")
		dataBlock = data[(i * blockSize) : ((i+1) * blockSize)]
		b64EncodedDataBlock = base64.b64encode((i).to_bytes(2, byteorder='big')) + base64.b64encode(dataBlock)

		assert(b64EncodedDataBlock.decode('ascii')[3] == "=") # as we encoded a two byte (ushort) value to base64, we always (even at ushort_max)
															# should have a fill-character at the end of the first four bytes. We can use it to detect the end of the
															# page id and the start of the base64 encoded data block
															# TODO: replace with nicer check & error message, even though this should never fail

		qr = None

		try: # oh god why
			qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_Q, border=0, box_size=32)
			qr.add_data(b64EncodedDataBlock)
			qr.make(True);
			print("\t\t... using Error Correction Level Q (25% recoverable)")
		except (qrcode.exceptions.DataOverflowError):
			try: # oh go why²
				qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_M, border=0, box_size=32)
				qr.add_data(b64EncodedDataBlock)
				qr.make(True);
				print("\t\t... using Error Correction Level M (15% recoverable)")
			except (qrcode.exceptions.DataOverflowError):
				qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L, border=0, box_size=32)
				qr.add_data(b64EncodedDataBlock)
				qr.make(True);
				print("\t\t... using Error Correction Level L (7% recoverable)")

		assert(qr != None)

		qrAsImage = ImageReader(qr.make_image().get_image())
		document.drawImage(
			qrAsImage, _border + 72.5,
			A4[1] - (42.5 + _fontsize + (A4[0] - (2 * _border + 145))),
			A4[0] - (2 * _border + 145),
			A4[0] - (2 * _border + 145))

		print("\t... Writing bytes to file ...")

		b32EncodedDataBlock = base64.b32encode(dataBlock)

		requiredLines = len(b32EncodedDataBlock) // 80 # 80 => number of chars per line (actually 84, but 4 chars are for crc16)
		if ((len(b32EncodedDataBlock) % 80) != 0): requiredLines += 1 # max blocksize 2048 -> base32 -> 3280 chars / 80 = 41 lines max

		for lineCount in range(requiredLines):
			
			document.setFillAlpha(0.4)
			document.drawString(_border, A4[1] - (396 + ((_fontsize + 2) * lineCount)), f"{(lineCount + 1):02d}")
			document.setFillAlpha(1)

			lineData = b32EncodedDataBlock[(lineCount * 80) : ((lineCount+1) * 80)]
			line = ""
			for blockCount in range(10):
				block = lineData[(blockCount * 8) : ((blockCount+1) * 8)].decode('ascii')
				line += f"{block} "
			document.drawString(_border + 13.5, A4[1] - (396 + ((_fontsize + 2) * lineCount)), line) # TODO: Replace magic number 396px with dynamic stuff

			# crc over the base data, NOT the encoded base32 one

			crc32 = base64.b85encode(binascii.crc32(base64.b32decode(lineData)).to_bytes(4, byteorder='big'))
			document.setFillAlpha(0.4)
			document.drawRightString(A4[0] - _border, A4[1] - (396 + ((_fontsize + 2) * lineCount)), crc32)
			document.setFillAlpha(1)

		document.showPage()

	print("Paper backup creation successful! Saving output to " + arguments.output)
	document.save()

	return


if (__name__ == "__main__"):
	main(sys.argv[1:])
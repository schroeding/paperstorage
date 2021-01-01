import io
import math
import datetime
import binascii
import hashlib
import qrcode
from base64 import b64decode, b64encode, b32encode, b32decode, b85encode
from socket import gethostname
from random import random
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

class PaperStorage:

	A4 = (210, 297)     # The whole world... :-)
	LETTER = (216, 279) # ... except north america. why are you like this. :-(

	_border = 20 * mm
	_fontsize = None
	_font = None

	_softwareIdentifier = "Paperstorage Backup"

	def __init__(self,
		data: bytes = None,
		identifier: str = None,
		blockSize: int = 1500,
		size: (int, int) = A4,
		writeHostname: bool = True,
		writeDate: bool = True,
		watermark: str = None,
		fontname: str = 'Courier'):
		"""
		Creates a new PaperStorage object

		Parameters:
			data (bytes or None):
				the raw data that should be saved or None if data should be added later / should be restored
			identifier (str or None):
				an identifier for the specified data, like a filename or a (very brief) description
			blockSize (int):
				create blocks (pages) with the following amount of bytes
				must be between 50 and 1500 and should be multiple of 50, defaults to 1500
			size (int, int):
				tupel of the width and height of the new document in millimeters, defaults to DIN A4 (210mm x 297mm)
				PaperStorage.LETTER can be used for the north american 'letter' format
			writeHostname (bool):
				prints the hostname of this machine onto the document, defaults to True
			writeDate (bool):
				prints the current date onto the document, defaults to True
			watermark (str or None):
				embed a string as a watermark on every page, defaults to None
			fontname (str):
				sets the font to use in the pdf, defaults to Courier (built-in),
				must be a monospace font (no exception will be raised otherwise, but the layout will look horrible)
		"""
		if (not (isinstance(data, bytes) or (data is None))):
			if (isinstance(data, str)): raise TypeError('data must be bytes object or None - use classmethod fromStr to handle str')
			else: raise TypeError('data must be bytes object or None - check classmethods for other data types')
		self._rawData = data

		if (not (isinstance(identifier, str) or (identifier is None))): raise TypeError('identifier must be str or None')
		self._identifier = identifier

		if (not isinstance(blockSize, int)): raise TypeError('blockSize must be int')
		if (not (blockSize in range(50, 1501))): raise ValueError('blockSize must be between 50 and 1500')
		self._blockSize = blockSize

		if ((not isinstance(size, type((int, int)))) or (not isinstance(size[0], int)) or (not isinstance(size[1], int))):
			raise TypeError('size must be int tupel, e.g. (210, 297)')
		if ((size[0] <= 0) or (size[1] <= 0)): raise ValueError('height and width must be greater than zero')
		if (size[0] > size[1]): raise ValueError('landscape format is not supported')
		self._width = size[0]
		self._height = size[1]

		if (not isinstance(writeHostname, bool)): raise TypeError('writeHostname must be bool')
		self._writeHostname = writeHostname

		if (not isinstance(writeDate, bool)): raise TypeError('writeDate must be bool')
		self._writeDate = writeDate
		self._date = str(datetime.date.today())

		if (not (isinstance(watermark, bool) or (watermark is None))): raise TypeError('watermark must be str or None')
		self._watermark = watermark

		if (not isinstance(fontname, str)): raise TypeError('fontname must be str')
		self._font = fontname

		self._document = None
		self._binaryDocument = io.BytesIO()
		_maxFontsizeHeight = round(((self._height * mm) / 70), 1) # We must be able to print 70 lines of text ...
		_maxFontsizeWidth = None # ... and at least a full base32 line with 10 blocks a 8 characters + checksum and line number
		_base32MockUp = "xx 12345678 12345678 12345678 12345678 12345678 12345678 12345678 12345678 12345678 12345678 xxxx"
		for n in range(round(_maxFontsizeHeight * 10), 1, -1): # range can only use integers, so we multiply by 10, e.g. 2.5 => 25
			try: # stringWidth will throw an exception if the typeface does not exist
				if (stringWidth(_base32MockUp, self._font, (n / 10)) < ((self._width * mm) - (2 * self._border))):
					_maxFontsizeWidth = (n / 10) # we must divide by 10 to get the original float value
					break
			except (KeyError):
				raise ValueError('invalid fontname specified / font not found')
		if (_maxFontsizeWidth is None): raise ValueError('invalid document dimensions (too small width)')
		self._fontsize = min(_maxFontsizeWidth, _maxFontsizeHeight)


	@classmethod
	def fromStr(cls,
		data: str,
		encoding: str = 'utf-8',
		identifier: str = None,
		blockSize: int = 1500,
		size: (int, int) = A4,
		writeHostname: bool = True,
		writeDate: bool = True,
		watermark: str = None,
		fontname: str = 'Courier'):
		if ((not isinstance(data, str)) or (not isinstance(encoding, str))): raise TypeError('expected str')

		_strToBytes = bytes(data, encoding)
		return cls(_strToBytes, identifier=identifier, blockSize=blockSize, size=size, writeHostname=writeHostname, writeDate=writeDate, watermark=watermark, fontname=fontname)


	@classmethod
	def fromFile(cls,
		filename: str,
		size: (int, int) = A4):
		if (not isinstance(filename, str)): raise TypeError('expected str')
		raise NotImplementedError() # TODO: implement from file


	def __renderQRCode(self, data: str, wPos: int, hPos: int, size: int, force31: bool = False) -> None:
		_qrCode = None
		if ((len(data) >= 262) or force31):
			if (len(data) >= 1499):
				_qrCode = qrcode.QRCode(version=31, error_correction=qrcode.ERROR_CORRECT_M, border=0, box_size=16)
			else:
				_qrCode = qrcode.QRCode(version=31, error_correction=qrcode.ERROR_CORRECT_Q, border=0, box_size=16)
		else:
			_qrCode = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_M, border=0, box_size=16)
		_qrCode.add_data(data, optimize=20)
		_qrCode.make(True)
		assert(_qrCode != None)
		self._document.drawInlineImage(_qrCode.make_image().get_image(), wPos, (self._height * mm) - hPos - size, size, size)

	def __newPage(self, notFirstPage: bool = True) -> None:
		if (notFirstPage): self._document.showPage() # page break
		if (self._watermark != None):
			self._document.saveState()
			self._document.translate(1 * self._width * mm * 0.225, -1 * self._height * mm * 0.45)
			self._document.rotate(15)
			self._document.translate(0, 50)
			self._document.setFont(self._font, 50)
			self._document.setFillColorRGB(0, 0, 0, 0.03)
			self._document.drawCentredString((self._width * mm) / 2, (self._height * mm) / 2, self._watermark)
			self._document.restoreState()
		self.__renderLine(4 * self._fontsize)
		self.__renderText(f'Page {self._document.getPageNumber()} of {math.ceil(len(self._rawData) / self._blockSize) + 1}', 2 * self._fontsize, alignRight=True);
		self.__renderText(self._softwareIdentifier, 2 * self._fontsize)

		self.__renderLine((self._height * mm) - (4 * self._fontsize))
		self.__renderText(self._identifier, (self._height * mm) - (3.5 * self._fontsize))
		if (self._writeDate):
			self.__renderText(f'Created on {self._date}', (self._height * mm) - (3.5 * self._fontsize), alignRight=True)
		elif (self._writeHostname):
			self.__renderText(gethostname(), (self._height * mm) - (3.5 * self._fontsize), alignRight=True)
		else:
			self.__renderText(f'Page {self._document.getPageNumber()} of {math.ceil(len(self._rawData) / self._blockSize) + 1}',  (self._height * mm) - (3.5 * self._fontsize), alignRight=True);


	def __renderText(self, text: str,
		hPos: int,
		wPos: int = _border,
		maxWidth: int = None,
		bold: bool = False,
		fontsize: int = None,
		alignRight: bool = False,
		alignCenter: bool = False,
		alpha: float = 1.0) -> int:
		"""
		Renders a string or paragraph onto the PDF document

		Returns the height of the newly added text
		"""
		if (fontsize == None):
			fontsize = self._fontsize
		if (bold):
			self._document.setFont(f'{self._font}-Bold', fontsize)
		else:
			self._document.setFont(self._font, fontsize)
		if (maxWidth == None):
			maxWidth = (self._width * mm) - (2 * self._border)
		if (alignCenter):
			_drawString = self._document.drawCentredString
			wPos = (self._width * mm) / 2
		elif (alignRight):
			_drawString = self._document.drawRightString
			wPos = (self._width * mm) - wPos + stringWidth(' ', self._font, fontsize)
		else:
			_drawString = self._document.drawString
		self._document.setFillColorRGB(0, 0, 0, alpha)
		_textHeight = 1
		_lines = text.splitlines(False)
		for _line in _lines:
			_words = _line.split(' ')
			_textWidth = 0
			_writeableWords = ''
			for _word in _words:
				_wordWidth = stringWidth(f'{_word} ', self._font, fontsize)
				_textWidth += _wordWidth
				if (_textWidth > maxWidth):
					_drawString(wPos, (self._height * mm) - hPos - ((fontsize + 2) * _textHeight), _writeableWords)
					_textHeight += 1
					_textWidth = _wordWidth
					_writeableWords = ''
				_writeableWords += f'{_word} '
			_drawString(wPos, (self._height * mm) - hPos - ((fontsize + 2) * _textHeight), _writeableWords)
			_textHeight += 1
		return (_textHeight * (fontsize + 2))


	def __renderLine(self, hPos: int) -> None:
		"""
		Renders a line onto the PDF document
		"""
		self._document.setLineWidth(0.25)
		self._document.line(self._border, (self._height * mm) - hPos, (self._width * mm) - self._border, (self._height * mm) - hPos)


	def __renderPDF(self) -> bool:
		"""
		Creates the PDF document from the available data

		Returns False if generation failed, True otherwise
		"""
		if (self._rawData is None): return False
		if (self._identifier is None): self._identifier = f'Backup of {len(self._rawData)} byte file'
		self._document = Canvas(filename=self._binaryDocument, pagesize=(self._width * mm, self._height * mm))

		_amountOfBlocks = math.ceil(len(self._rawData) / self._blockSize) # + 1 = first page with meta information
		_crc32 = hex(binascii.crc32(self._rawData))
		_md5 = hashlib.md5(self._rawData).hexdigest()
		_sha256 = hashlib.sha256(self._rawData).hexdigest()
		_documentID = b64encode(round((random()*65535)).to_bytes(2, byteorder='big'))

		self._document.setTitle(f'{self._softwareIdentifier} - {self._identifier}')
		self.__newPage(False)
		# first page with meta info
		self.__renderText("This document contains a paper backup of binary data", 5 * self._fontsize, fontsize=(self._fontsize * 1.3),
			bold=True, alignCenter=True)
		_hPos = self.__renderText(f'Identifier (e.g. filename): {self._identifier}\n'\
			f'Size of binary data:        {len(self._rawData)} bytes\n'\
			f'{f"Date of backup:             {self._date}" if self._writeDate else ""}\n'\
			f'{f"Backup created on:          {gethostname()}" if self._writeHostname else ""}\n'\
			f'\n'\
			f'Block size used for backup: {self._blockSize} bytes\n'\
			f'Blocks used:                {_amountOfBlocks}\n'\
			f'CRC32 of restored backup:   {_crc32}\n'\
			f'MD5 hash of restored data:  {_md5}\n', 8 * self._fontsize, self._border + (0.25 * self._width * mm), fontsize=(self._fontsize * 1.2))
		_metadata = f'hcpb01,{_documentID.decode("ascii")},{b64encode((self._identifier).encode("utf-8")).decode("ascii")},{str(len(self._rawData))},{str(self._blockSize)},{_sha256}'
		self.__renderQRCode(_metadata, self._border + (0.025 * self._width * mm), 8 * self._fontsize, (0.20 * self._width * mm) - self._fontsize)
		# TODO: restore information here
		# end of first page
		for n in range(_amountOfBlocks):
			self.__newPage(True)
			_rawDataBlock = self._rawData[(n * self._blockSize) : ((n+1) * self._blockSize)]
			_blockID = b64encode((n).to_bytes(2, byteorder='big'))
			_qrData = (_blockID + _documentID + b64encode(_rawDataBlock))
			assert(_qrData.decode('ascii')[3] == "=") 	# as we encoded two two byte (ushort) value to base64, we always (even at ushort_max)
			assert(_qrData.decode('ascii')[7] == "=")	# should have a fill-character (=) at position 4 and 8. We can use it to detect the end of the
														# page id and the start of the base64 encoded data block
														# TODO: replace with nicer check & error message, even though this should *never* fail
			_qrSize = min((self._width * mm) - (2 * self._border), (self._height * mm) - (40 * self._fontsize * 1.15))
			self.__renderQRCode(_qrData.decode("ascii"), self._border + (((self._width * mm) - ((2 * self._border) + _qrSize)) / 2), 5 * self._fontsize, _qrSize, True)
			_b32DataBlock = b32encode(_rawDataBlock)
			_amountOfLines = math.ceil(len(_b32DataBlock) / 80)
			for k in range(_amountOfLines):
				_hPos = (6 * self._fontsize) + _qrSize + (k * self._fontsize * 1.15)
				_lineData = _b32DataBlock[(k * 80) : ((k+1) * 80)]
				_lineDataCrc32InBase85 = b85encode(binascii.crc32(b32decode(_lineData)).to_bytes(4, byteorder='big')).decode('ascii')
				_lineDataInBlocks = ''
				for i in range(10):
					_lineDataInBlocks += f'{_lineData[(i * 8) : ((i+1) * 8)].decode("ascii")} '
				self.__renderText(f'{(k+1):02d}', _hPos, alpha=0.4)
				self.__renderText(f'   {_lineDataInBlocks}', _hPos)
				self.__renderText(_lineDataCrc32InBase85, _hPos, alignRight=True, alpha=0.4)
		self._document.save()
		return True


	def savePDF(self, filename: str) -> bool:
		"""
		Saves the generated PDF document to the specified path

		Parameters:
			filename (str):
				filename to save the pdf to, must not be empty and should end with '.pdf'

		Returns False if generation failed or if the file could not be saved, True otherwise
		"""
		if ((not isinstance(filename, str)) or (len(filename) == 0)):
			raise TypeError('filename must be non-empty str') # Should be ValueError for ''

		if (not self.__renderPDF()):
			return False
		assert(self._document != None)
		try:
			_file = open(filename, "wb")
		except (Exception):
			return False
		_file.write(self._binaryDocument.getvalue())
		_file.close()
		return True

	def getPDF(self) -> bytes:
		"""
		Fetches the generated PDF document as a bytes object

		Returns None if generation failed, a bytes object otherwise
		"""
		if (not self.__renderPDF()):
			return None
		assert(self._document != None)
		return self._binaryDocument.getvalue()
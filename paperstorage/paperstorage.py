import io
import math
import datetime
import binascii
import hashlib
import qrcode
from base64 import b64encode, b64decode, b32encode, b32decode, b85encode
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
	_backupType = "binary data"
	_customFirstPage = ''

	def __init__(self,
		data: bytes = None,
		identifier: str = None,
		blockSize: int = 1500,
		size: (int, int) = A4,
		writeHostname: bool = True,
		writeDate: bool = True,
		watermark: str = None,
		fontname: str = 'Courier',
		noMetaPage: bool = False):
		"""Creates a new PaperStorage object

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
			noMetaPage (bool):
				no first page (with meta information and restore instructions) is printed
		"""
		self._documentID = None
		if (not (isinstance(data, bytes) or (data == None))):
			if (isinstance(data, str)): raise TypeError('data must be bytes object or None - use classmethod fromStr to handle str')
			else: raise TypeError('data must be bytes object or None - check classmethods for other data types')
		elif (data != None):
			self._documentID = b64encode(round((random()*65535)).to_bytes(2, byteorder='big'))
		self._rawData = data
		self._dataSize = 0 if (self._rawData == None) else len(self._rawData)

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

		if (not isinstance(noMetaPage, bool)): raise TypeError('noMetaPage must be bool')
		self._noMetaPage = noMetaPage

		self._blocks = dict()
		self._amountOfBlocks = 0
		self._sha256 = None
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
		fontname: str = 'Courier',
		noMetaPage: bool = False):
		if ((not isinstance(data, str)) or (not isinstance(encoding, str))): raise TypeError('expected str')

		_strToBytes = bytes(data, encoding)
		return cls(_strToBytes, identifier=identifier, blockSize=blockSize, size=size, writeHostname=writeHostname, writeDate=writeDate, watermark=watermark, fontname=fontname, noMetaPage=noMetaPage)


	@classmethod
	def fromFile(cls,
		filename: str,
		identifier: str = None,
		blockSize: int = 1500,
		size: (int, int) = A4,
		writeHostname: bool = True,
		writeDate: bool = True,
		watermark: str = None,
		fontname: str = 'Courier',
		noMetaPage: bool = False):
		if (not isinstance(filename, str)): raise TypeError('expected str')
		raise NotImplementedError() # TODO: implement from file


	def restoreMetaData(self, identifier: str, size: int, documentID: str = None, blockSize: int = 1500, sha256Hash: str = None) -> bool:
		"""
		Sets the meta data, typically to start the restore process of a backup

		Parameters:
			identifier (str):
				the identifier of the file that should be restored
			size (int):
				the size of the file in bytes
			documentID (str or None):
				the four character, base64 encoded document id or None to disable document id checks
				if no document id is specified, it's possible that two backups are mixed together
			blockSize (int)
				the block size used in the backup, can also be calculated with (number of base32 lines * 50), defaults to 1500
			sha256Hash (str or None)
				the sha256 hash of the file or None to disable any integrity check

		Returns False if any binary data is already loaded, True otherwise
		"""
		if (not isinstance(size, int)): raise TypeError('size must be int')
		if (not isinstance(blockSize, int)): raise TypeError('blockSize must be int')
		if (not (blockSize in range(50, 1501, 50))): raise ValueError('blocksize invalid, must be any multiple of 50 between 50 and 1500')
		if (self._rawData != None): return False

		self._identifier = identifier
		self._dataSize = size
		self._documentID = documentID
		self._blockSize = blockSize
		self._amountOfBlocks = math.ceil(self._dataSize / self._blockSize)
		self._sha256 = sha256Hash


	def restoreDataBlock(self, blockID: int, blockData: bytes, documentID: str = None):
		"""
		Sets a data block, typically during the restore process of a backup

		Partameters:
			blockID (int):
				block id of the block
			blockData (bytes):
				binary data of the data block
			documentID (str or None):
				the four character, base64 encoded document id or None to disable document id checks
				if no document id is specified, it's possible that two backups are mixed together

		Returns False is the block is already loaded or the document id is invalid, True otherwise
		"""
		if (not isinstance(blockID, int)): raise TypeError('blockID must be int')
		if (not isinstance(blockData, bytes)): raise TypeError('blockData must be bytes')
		if (self._rawData != None): return False
		if (self._blocks.get(blockID, None) != None): return False
		if ((self._documentID != None) and (documentID != None) and (self._documentID != documentID)): return False
		if (self._amountOfBlocks < (blockID + 1)): self._amountOfBlocks = blockID + 1
		if (len(blockData) > self._blockSize): self._blockSize = len(blockData)
		self._blocks[blockID] = blockData
		

	def restoreFromQRString(self, qrData: str) -> bool:
		"""
		Restores meta data or a data block from a QR data string

		Parameters:
			qrData (str):
				a string from a QR code, as-is without any modifications

		Returns False if the string is invalid, True otherwise
		"""
		if (qrData[:6] == 'hcpb01'):
			qrDataChunks = qrData.split(',')
			if (len(qrDataChunks) != 6):
				return False
			return self.restoreMetaData(b64decode(qrDataChunks[2].encode('ascii')).decode('utf-8'), int(qrDataChunks[3]), qrDataChunks[1], int(qrDataChunks[4]), qrDataChunks[5])
		elif ((len(qrData) > 8) and (qrData[3] == '=') and (qrData[7] == '=')):
			return self.restoreDataBlock(int.from_bytes(b64decode(qrData[0:4]), byteorder='big', signed=False), b64decode(qrData[8:]), str(qrData[4:8]))
		return False

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
		self.__renderText(f'Page {self._document.getPageNumber()} of {math.ceil(self._dataSize / self._blockSize) + (0 if self._noMetaPage else 1)}', 2.5 * self._fontsize, alignRight=True);
		self.__renderText(self._softwareIdentifier, 2.5 * self._fontsize)

		self.__renderLine((self._height * mm) - (4 * self._fontsize))
		self.__renderText(self._identifier, (self._height * mm) - (4 * self._fontsize))
		if (self._writeDate):
			self.__renderText(f'Created on {self._date}', (self._height * mm) - (4 * self._fontsize), alignRight=True)
		elif (self._writeHostname):
			self.__renderText(gethostname(), (self._height * mm) - (4 * self._fontsize), alignRight=True)
		else:
			self.__renderText(f'Page {self._document.getPageNumber()} of {math.ceil(self._dataSize / self._blockSize) + (0 if self._noMetaPage else 1)}',  (self._height * mm) - (4 * self._fontsize), alignRight=True);


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
		if (self._identifier is None): self._identifier = f'Backup of {self._dataSize} byte file'
		self._document = Canvas(filename=self._binaryDocument, pagesize=(self._width * mm, self._height * mm))

		self._amountOfBlocks = math.ceil(self._dataSize / self._blockSize)
		_crc32 = hex(binascii.crc32(self._rawData))
		_md5 = hashlib.md5(self._rawData).hexdigest()
		_sha256 = hashlib.sha256(self._rawData).hexdigest()
		
		self._document.setTitle(f'{self._softwareIdentifier} - {self._identifier}')
		# first page with meta info
		if (not self._noMetaPage):
			self.__newPage(False)
			self.__renderText(f'This document contains a paper backup of {self._backupType}', 5 * self._fontsize, fontsize=(self._fontsize * 1.3),
				bold=True, alignCenter=True)
			_hPos = 8 * self._fontsize
			_hPos += self.__renderText(f'Identifier:           {self._identifier}\n'\
				f'Size of binary data:  {len(self._rawData)} bytes\n'\
				f'{f"Date of backup:       {self._date}" if self._writeDate else ""}\n'\
				f'{f"Backup created on:    {gethostname()}" if self._writeHostname else ""}\n'\
				f'\n'\
				f'Block size of backup: {self._blockSize} bytes\n'\
				f'Blocks used:          {self._amountOfBlocks}\n'\
				f'CRC32 checksum:       {_crc32}\n'\
				f'MD5 hash:             {_md5}\n', _hPos, self._border + (0.24 * self._width * mm), fontsize=(self._fontsize * 1.2), maxWidth=(0.6 * self._width * mm))

			_metadata = f'hcpb01,{self._documentID.decode("ascii")},{b64encode((self._identifier).encode("utf-8")).decode("ascii")},{str(len(self._rawData))},{str(self._blockSize)},{_sha256}'
			self.__renderQRCode(_metadata, self._border + (0.02 * self._width * mm), 8 * self._fontsize, (0.20 * self._width * mm) - self._fontsize)

			if (self._customFirstPage != ''):
				self.__renderText(self._customFirstPage, _hPos, fontsize=(self._fontsize * 1.1))
			else:
				_offset = stringWidth('   ', self._font, self._fontsize)
				_hPos += self.__renderText('To restore this backup, follow one of the following restore methods:', _hPos + (self._fontsize * 0.3), fontsize=(self._fontsize * 1.2), alignCenter=True)
				_hPos += self.__renderText('1) Read the QR-Codes with PaperStorage', _hPos, fontsize=(self._fontsize * 1))
				_hPos += self.__renderText('Scan all pages (including this one) with any kind of scanner / scanning app available to you and save the resulting scans as images on your computer. Install Python and the PaperStorage module (available on pip, \'python -m pip install paperstorage\') on your computer and start the restore process by typing \'python -m paperstorage --interactive-restore\' into a terminal.',
					_hPos - (self._fontsize * 0.5), self._border + _offset, fontsize=(self._fontsize * 1), maxWidth=((self._width * mm) - (2 * self._border) - _offset))
				_hPos += self.__renderText('2) Read the QR-Codes manually', _hPos, fontsize=(self._fontsize * 1))
				_hPos += self.__renderText('Every page (except this first one) contains a QR-Code with one data block. Use any QR-Reader available to you to save the data blocks as plain text files. The first four characters of every data block contain the block id (starting from 0), the following four characters contain a document id, both Base64 encoded big endian integers. The remaining string is the binary data of the data block, also encoded in Base64. Concatenate the binary data in the correct order to restore the original file. The following shell script restores a backup from JPEG or PNG scans of a backup using zbar:',
					_hPos - (self._fontsize * 0.5), self._border + _offset, fontsize=(self._fontsize * 1), maxWidth=((self._width * mm) - (2 * self._border) - _offset))
				_hPos += self.__renderText('for i in *.{jpg,png}; do block=$(zbarimg --raw --quiet $i); if [ "$block" = "" ]; then \\\n'\
					'echo "image $i not readable!"; continue; fi; echo $block | tail -c +5 | base64 -d > "$(echo $block | \\\n'\
					'head -c 4 | base64 -d | od --endian big -A n -t u2 -w2 | xargs).hcpbblock"; done; \\\n'\
					'for i in *.hcpbblock; do cat $i >> restored_backup; rm -f $i; done;', _hPos - (self._fontsize), self._border + _offset, fontsize=(self._fontsize * 0.9))
				_hPos += self.__renderText('3) Manual backup restoration', _hPos, fontsize=(self._fontsize * 1))
				_hPos += self.__renderText('Each page also contains the binary data encoded in Base32, below the QR-Code. Each line contains a line number, up to 80 characters of base32 encoded data (splitted into 8 character chunks for enhanced readability). The last five characters are a Base85 encoded CRC32 checksum of the decoded binary data of the line, allowing the verification of each line. Only the Base32 encoded binary data is necessary to restore the original file. The following python script can be used to manually restore a backup from the Base32 data:',
					_hPos - (self._fontsize * 0.5), self._border + _offset, fontsize=(self._fontsize * 1), maxWidth=((self._width * mm) - (2 * self._border) - _offset))
				_hPos += self.__renderText('import base64, sys, math, binascii\n'\
					'from base64 import b85encode, b32decode\n'\
					'dS, bS, eD = int(input(\'size of binary data: \')), int(input(\'block size used for backup: \')), \'\'\n'\
					'rB = (dS // bS)\n'\
					'if (dS % bS != 0): rB += 1\n'\
					'for i in range(rB):\n'\
					'    print(f\'page {i + 2} of {rB + 1}\')\n'\
					'    if (((dS - (bS * i)) // bS) >= 1): rB, pD = math.ceil((bS * 8 + 4) / 5), \'\'\n'\
					'    else: rB, pD = math.ceil(((dS - (bS * i)) * 8 + 4) / 5), \'\'\n'\
					'    for n in range(math.ceil((rB - 1) / 80)):\n'\
					'        lD, nL = \'\', False\n'\
					'        while (not nL):\n'\
					'            lD = input(f\'input line {n + 1} of {math.ceil((rB - 1) / 80)}: \').upper().replace(\' \',\'\')\n'\
					'            try:\n'\
					'                c32 = b85encode(binascii.crc32(b32decode(lD)).to_bytes(4, byteorder=\'big\'))\n'\
					'            except (binascii.Error):\n'\
					'                print(\'invalid line, restart\')\n'\
					'                continue\n'\
					'            if (input(f\'crc32 is {c32.decode("utf-8")}, ok? \')!=\'no\'): nL = True\n'\
					'        pD += lD\n'\
					'    eD += pD\n'\
					'(open(input(\'enter filename: \'), \'wb+\').write(base64.b32decode(eD)))\n', _hPos - (self._fontsize), self._border + _offset, fontsize=(self._fontsize * 0.9))
		# end of first page
		for n in range(self._amountOfBlocks):
			self.__newPage(False if (self._noMetaPage and (n == 0)) else True)
			self._blocks[n] = self._rawData[(n * self._blockSize) : ((n+1) * self._blockSize)]
			_blockID = b64encode((n).to_bytes(2, byteorder='big'))
			_qrData = (_blockID + self._documentID + b64encode(self._blocks[n]))
			assert(_qrData.decode('ascii')[3] == "=") 	# as we encoded two two byte (ushort) value to base64, we always (even at ushort_max)
			assert(_qrData.decode('ascii')[7] == "=")	# should have a fill-character (=) at position 4 and 8. We can use it to detect the end of the
														# page id and the start of the base64 encoded data block
														# TODO: replace with nicer check & error message, even though this should *never* fail
			_qrSize = min((self._width * mm) - (2 * self._border), (self._height * mm) - (40 * self._fontsize * 1.15))
			self.__renderQRCode(_qrData.decode("ascii"), self._border + (((self._width * mm) - ((2 * self._border) + _qrSize)) / 2), 5.5 * self._fontsize, _qrSize, True)
			_b32DataBlock = b32encode(self._blocks[n])
			_amountOfLines = math.ceil(len(_b32DataBlock) / 80)
			for k in range(_amountOfLines):
				_hPos = (6.5 * self._fontsize) + _qrSize + (k * self._fontsize * 1.15)
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

	
	def setBackupType(self, typename: str) -> None:
		"""
		Changes the string that is written on the first page
		
		Parameters:
			typename (str):
				'This document contains a paper backup of [type]', defaults to 'binary data'

		Returns None
		"""
		if (not isinstance(typename, str)): raise TypeError('expected str')
		self._backupType = typename


	def setSoftwareIdentifier(self, softwareIdentifier: str) -> None:
		"""
		Changes the string that is written on the top left corner of every page
		
		Parameters:
			softwareIdentifier (str):
				string to print on the left corner of every page, defaults to 'PaperStorage Backup'

		Returns None
		"""
		if (not isinstance(softwareIdentifier, str)): raise TypeError('expected str')
		self._softwareIdentifier = softwareIdentifier


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


	def isDataReady(self) -> bool:
		"""
		Returns true if binary data is available, e.g. if all blocks of a backup are already read
		(or if the PaperStorage object was initialized with data), False otherwise
		"""
		if (self._rawData != None):
			return True
		else: 
			if (self._amountOfBlocks == 0):
				return False
			else:
				if (len(self._blocks) == self._amountOfBlocks):
					self._rawData = bytes()
					for n in range(self._amountOfBlocks):
						self._rawData += self._blocks[n]
					return True
		return False


	def getData(self) -> bytes:
		"""
		Fetches the binary data of the PaperStorage object
		
		Returns None if no data is available, a bytes object otherwise
		"""
		if (not self.isDataReady()):
			return None
		else:
			return self._rawData


	def getMissingDataBlocks(self) -> list:
		"""
		Returns a list with the ids of the missing data blocks

		Careful: Works only if the number of blocks is known and set (by reading the meta page first) or if the last page / block has already been read.
		"""
		_missingBlocks = []
		for n in range(self._amountOfBlocks):
			if (self._blocks.get(n, None) == None):
				_missingBlocks.append(n)
		return _missingBlocks
import io
import math
import datetime
from socket import gethostname
import reportlab
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
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
		if (not ((type(data) == bytes) or (data is None))):
			if (type(data) == str): raise TypeError('data must be bytes object or None - use classmethod fromStr to handle str')
			else: raise TypeError('data must be bytes object or None - check classmethods for other data types')
		self._rawData = data

		if (not ((type(identifier) == str) or (identifier is None))):
			raise TypeError('identifier must be str or None')
		self._identifier = identifier

		if (type(blockSize) != int):
			raise TypeError('blockSize must be int')
		if (not (blockSize in range(50, 1501))):
			raise ValueError('blockSize must be between 50 and 1500')
		self._blockSize = blockSize

		if ((type(size) != type((int, int))) or (type(size[0]) != int) or (type(size[1]) != int)):
			raise TypeError('size must be int tupel, e.g. (210, 297)')
		if ((size[0] <= 0) or (size[1] <= 0)):
			raise ValueError('height and width must be greater than zero')
		if (size[0] > size[1]):
			raise ValueError('landscape format is not supported')
		self._width = size[0]
		self._height = size[1]

		if (type(writeHostname) != bool):
			raise TypeError('writeHostname must be bool')
		self._writeHostname = writeHostname

		if (type(writeDate) != bool):
			raise TypeError('writeDate must be bool')
		self._writeDate = writeDate
		self._date = str(datetime.date.today())

		if (not ((type(watermark) == str) or (watermark is None))):
			raise TypeError('watermark must be str or None')
		self._watermark = watermark

		if (not ((type(fontname) == str))):
			raise TypeError('fontname must be str')
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
		if ((type(data) != str) or (type(encoding) != str)): raise TypeError('expected str')

		_strToBytes = bytes(data, encoding)
		return cls(_strToBytes, identifier=identifier, blockSize=blockSize, size=size, writeHostname=writeHostname, writeDate=writeDate, watermark=watermark, fontname=fontname)


	@classmethod
	def fromFile(cls,
		filename: str,
		size: (int, int) = A4):
		if (type(filename) != str): raise TypeError('expected str')

		raise NotImplementedError() # TODO: implement from file
		pass

	def __newPage(self, notFirstPage: bool = True) -> None:
		if (notFirstPage): self._document.showPage() # page break
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
		alignCenter: bool = False) -> int:
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
		_textHeight = 1
		_lines = text.splitlines(False)
		for _line in _lines:
			_words = _line.split()
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
		if (self._identifier is None): self._identifier = f'{len(self._rawData)} byte file'
		self._document = Canvas(filename=self._binaryDocument, pagesize=(self._width * mm, self._height * mm))
		
		self._document.setTitle(f'Paper Backup - {self._identifier}')
		self.__newPage(False)
		self.__newPage()
		self.__newPage()
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
		if ((type(filename) != str) or (len(filename) == 0)):
			raise TypeError('filename must be non-empty str') # Should be ValueError for ''

		if (not self.__renderPDF()):
			return False
		assert(self._document != None)
		try:
			_file = open(filename, "wb")
		except:
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
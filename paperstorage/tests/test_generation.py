import unittest
from paperstorage import PaperStorage

class TestGeneration(unittest.TestCase):

	def setUp(self):
		self.testDataStr = "Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu einem ungeheueren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken und sah, wenn er den Kopf ein wenig hob, seinen gewölbten, braunen, von bogenförmigen Versteifungen geteilten Bauch, auf dessen Höhe sich die Bettdecke, zum gänzlichen Niedergleiten bereit, kaum noch erhalten konnte. Seine vielen, im Vergleich zu seinem sonstigen Umfang kläglich dünnen Beine flimmerten ihm hilflos vor den Augen. " * 10
		self.testDocumentStr = PaperStorage.fromStr(self.testDataStr, identifier='Unittest String', size=PaperStorage.A4, writeDate=False, writeHostname=False, watermark='Unittest')
		self.testDocumentBytes = PaperStorage(bytes(self.testDataStr.encode('utf-8')), identifier='Unittest', size=PaperStorage.LETTER, writeDate=False, writeHostname=False, watermark='Unittest')
		self.testDocumentFile = PaperStorage.fromFile('paperstorage/tests/random_testfile', identifier='Unittest File', size=PaperStorage.A4, watermark='Unittest')
		self.testDocumentEmpty = PaperStorage()

	def testCreation(self):
		self.assertRaises(TypeError, PaperStorage, data='string') # string
		self.assertRaises(TypeError, PaperStorage, data=42424242) # int
		self.assertRaises(TypeError, PaperStorage, data=bytearray('string', 'utf-8')) # bytearray

		self.assertRaises(TypeError, PaperStorage, blockSize='1500') # string
		self.assertRaises(ValueError, PaperStorage, blockSize=49) # too low
		self.assertRaises(ValueError, PaperStorage, blockSize=1501) # too large
		self.assertRaises(ValueError, PaperStorage, blockSize=-1) # negative

		self.assertRaises(TypeError, PaperStorage, size=500) # not a tupel
		self.assertRaises(ValueError, PaperStorage, fontname='DoesNotExistSansSerif') # invalid font
		self.assertRaises(ValueError, PaperStorage.fromFile, filename='NonExistentFile') # invalid file

		self.assertRaises(TypeError, self.testDocumentStr.savePDF, '') # empty filename

		self.testDocumentFile._customFirstPage = self.testDataStr
		self.testDocumentFile.setBackupType('Unittest')
		self.testDocumentFile.setSoftwareIdentifier('Unittest')

		self.assertEqual(self.testDocumentEmpty.getPDF(), None)

		self.assertEqual(self.testDocumentStr.savePDF('test1.pdf'), True)
		self.assertEqual(self.testDocumentBytes.savePDF('test2.pdf'), True)
		self.assertEqual(self.testDocumentFile.savePDF('test3.pdf'), True)

		self.assertEqual(type(self.testDocumentStr.getPDF()), bytes)
		self.assertEqual(type(self.testDocumentBytes.getPDF()), bytes)
		self.assertEqual(type(self.testDocumentFile.getPDF()), bytes)

		self.assertEqual(self.testDocumentStr.getData(), self.testDocumentBytes.getData())
		
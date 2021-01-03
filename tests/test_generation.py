import unittest
from paperstorage import PaperStorage

class TestGeneration(unittest.TestCase):

	def setUp(self):
		self.testDataStr = "Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu einem ungeheueren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken und sah, wenn er den Kopf ein wenig hob, seinen gewölbten, braunen, von bogenförmigen Versteifungen geteilten Bauch, auf dessen Höhe sich die Bettdecke, zum gänzlichen Niedergleiten bereit, kaum noch erhalten konnte. Seine vielen, im Vergleich zu seinem sonstigen Umfang kläglich dünnen Beine flimmerten ihm hilflos vor den Augen." * 4
		self.testDocumentStr = PaperStorage.fromStr(self.testDataStr, size=PaperStorage.A4, blockSize=1000, writeDate=False, writeHostname=False)
		self.testDocumentStrLetter = PaperStorage.fromStr(self.testDataStr, size=PaperStorage.LETTER)
		#self.testDocumentFile = PaperStorage.fromFile('random_testfile', size=PaperStorage.A4)

	def testCreation(self):
		self.assertRaises(TypeError, PaperStorage, data='string') # string
		self.assertRaises(TypeError, PaperStorage, data=42424242) # int
		self.assertRaises(TypeError, PaperStorage, data=bytearray('string', 'utf-8')) # bytearray

		self.assertRaises(TypeError, PaperStorage, blockSize='1500') # string
		self.assertRaises(ValueError, PaperStorage, blockSize=49) # too low
		self.assertRaises(ValueError, PaperStorage, blockSize=1501) # too large
		self.assertRaises(ValueError, PaperStorage, blockSize=-1) # negative

		self.assertRaises(TypeError, self.testDocumentStr.savePDF, '') # empty filename

		self.assertEqual(self.testDocumentStr.savePDF('test1.pdf'), True)
		self.assertEqual(self.testDocumentStrLetter.savePDF('test2.pdf'), True)
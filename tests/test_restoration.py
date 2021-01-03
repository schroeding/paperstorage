import unittest
from paperstorage import PaperStorage

class TestRestoration(unittest.TestCase):

	def setUp(self):
		self.testDataStr = "Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu einem ungeheueren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken und sah, wenn er den Kopf ein wenig hob, seinen gewölbten, braunen, von bogenförmigen Versteifungen geteilten Bauch, auf dessen Höhe sich die Bettdecke, zum gänzlichen Niedergleiten bereit, kaum noch erhalten konnte. Seine vielen, im Vergleich zu seinem sonstigen Umfang kläglich dünnen Beine flimmerten ihm hilflos vor den Augen. " * 10
		self.testDocument = PaperStorage()
		
	def testRestore(self):
		self.assertEqual(self.testDocument.restoreFromFolder('tests/sample_images'), True)
		self.assertEqual(self.testDocument.getData(), bytes(self.testDataStr.encode('utf-8')))
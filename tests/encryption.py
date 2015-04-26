# -*- coding: utf-8 -*-
from e89_syncing.security import encrypt_message,decrypt_message
import unittest
import array

class MockObject(object):
    def __init__(self, mock_attrs):
        self.mock_attrs = mock_attrs

    def __getattr__(self, attr_name):
        if self.mock_attrs.has_key(attr_name):
            return self.mock_attrs[attr_name]
        else:
            return MockObject(self.mock_attrs)

class TestEncryption(unittest.TestCase):

    def test_active(self):

        # Encryption/Decryption
        settings = MockObject({"SYNC_ENCRYPTION":True, "SYNC_ENCRYPTION_PASSWORD":"1234"})
        msg = u"Ação"
        encrypted = encrypt_message(msg,settings=settings)
        decrypted = decrypt_message(encrypted,settings=settings)

        self.assertEqual(msg, decrypted)

        # Java encrypt/Python decrypt
        java_enc=[3, 1, -45, 39, -92, 29, -52, 41, -43, 58, 96, -51, 18, 1, 23, -82, -57, -83, 87, -56, 78,
                  2, -124, 62, 68, -112, -64, 99, -121, -125, -44, 9, -94, 94, -37, -56, -69, 95, 114, 114,
                  102, 11, 94, 32, 37, 102, -105, -88, -4, 62, 61, -15, 26, 112, 118, 70, 84, 87, 52, 63, 47,
                  -22, 109, -78, 83, -34, -113, -69, 36, 29, 112, 126, 50, 6, -112, -21, 112, -46, -107, 97,
                  33, 118]

        java_enc_s=array.array('b',java_enc).tostring()
        decrypted = decrypt_message(java_enc_s,settings=settings)

        self.assertEqual(msg, decrypted)


    def test_inactive(self):

        settings = MockObject({"SYNC_ENCRYPTION":False})

        msg = u"Ação"
        encrypted = encrypt_message(msg,settings=settings)
        self.assertEqual(msg, encrypted)

        decrypted = decrypt_message(encrypted,settings=settings)
        self.assertEqual(msg, decrypted)


if __name__ == '__main__':
    unittest.main()
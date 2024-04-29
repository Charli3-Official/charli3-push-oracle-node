""" Decrypts the response from the API """
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

AES_KEY = "***REMOVED***"
IV = "0000000000000000"


def decrypt_response(encrypted_response):
    """Decrypts the response from the API"""
    print(encrypted_response)
    cipher = AES.new(AES_KEY.encode(), AES.MODE_CBC, iv=IV.encode())
    encrypted_data = base64.b64decode(encrypted_response)
    print("here:", encrypted_data)
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return decrypted_data.decode("utf-8")

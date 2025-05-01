from cryptography.fernet import Fernet
from django.conf import settings
def encrypt_data(raw_text):
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(raw_text.encode()).decode()

def decrypt_data(enc_text):
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(enc_text.encode()).decode()
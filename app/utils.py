import secrets
import string

def generate_passwrord(length=15):
    alphabet = string.ascii_letters + string.digits 
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password
                                                                                                                                                                                                                                        
from pgpy import PGPKey, PGPMessage
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings

# Déchiffrement d'un message PGP avec passphrase
def decrypt_pgp_message(private_key_path, public_key_path, input_file, output_file, passphrase="test1234"):
    try:
        # Charger la clé privée
        with open(private_key_path, "rb") as key_file:
            priv_key, _ = PGPKey.from_file(key_file.name)

        # Déverrouiller la clé avec la passphrase
        if priv_key.is_protected:
            priv_key.unlock(passphrase)

        # Lire le message chiffré
        with open(input_file, "r") as f:
            encrypted_message = PGPMessage.from_file(f.name)

        # Déchiffrer le message
        decrypted_message = priv_key.decrypt(encrypted_message).message

        # Sauvegarder le message déchiffré
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(decrypted_message)

        return True
    except Exception as e:
        print(f"Erreur de déchiffrement : {str(e)}")
        return False

# Lecture d'un fichier
def read_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()





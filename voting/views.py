
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CoVotant, DeVotant
import gnupg
import os
from django.core.mail import EmailMessage, get_connection
from imaplib import IMAP4_SSL
from email import message_from_bytes
import email
import imaplib
from email.policy import default
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from .models import DeVotant  
from .utils import decrypt_pgp_message, read_file

# Configuration GPG

GPG_KEYS_DIR = "C:/Users/oussa/voting_system"
gpg = gnupg.GPG(gpgbinary="C:/Program Files (x86)/gnupg/bin/gpg.exe")

def home(request):
    messages.success(request, "Bienvenue sur l'application de vote !")
    return render(request, "base.html")

def send_encrypted_mail(to_email, subject, message):
    """Envoie un email avec un message chiffré."""
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email='', # adresse gmail associée aux votants
        to=[to_email]
    )
    email.send()

def votant(request):
    """Fonction permettant à un votant de soumettre son vote de manière sécurisée."""
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        date_naissance = request.POST.get('date_naissance')
        identifiant = request.POST.get('identifiant')
        bulltinvote = request.POST.get('bulltinvote')

        # Vérification des champs
        if not (nom and prenom and date_naissance and identifiant and bulltinvote):
            messages.error(request, "Tous les champs sont obligatoires.")
            return render(request, 'votant.html')

        try:
            # Vérifier si l'identifiant a déjà voté
            if CoVotant.objects.filter(identification=identifiant).exists() or DeVotant.objects.filter(identification=identifiant).exists():
                messages.error(request, f"L'identifiant {identifiant} a déjà voté.")
                return render(request, 'votant.html')

            # Importer et récupérer la clé privée du votant
            with open(os.path.join(GPG_KEYS_DIR, "privkeyvotant.asc"), "r") as f:
                import_result = gpg.import_keys(f.read())

            # Récupérer le fingerprint de la clé privée du votant
            if import_result.results:
                votant_private_fingerprint = import_result.results[0]['fingerprint']
            else:
                messages.error(request, "Erreur : Impossible de charger la clé privée du votant.")
                return render(request, 'votant.html')

            # Charger les clés publiques de CO et DE
            with open(os.path.join(GPG_KEYS_DIR, "pubkeyco.asc"), "r") as f:
                gpg.import_keys(f.read())
            with open(os.path.join(GPG_KEYS_DIR, "pubkeyde.asc"), "r") as f:
                gpg.import_keys(f.read())

            # Création des messages à chiffrer
            identite_votant = f";;{identifiant};;{prenom};;{nom};;{date_naissance};;"
            vote_contenu = f"{identifiant};;{bulltinvote}"

            # 🔹 Chiffrement avec les bonnes clés publiques et signature avec la clé privée du votant
            identite_chiffree_co = gpg.encrypt(identite_votant, recipients=['samuel96rico@gmail.com'], sign=votant_private_fingerprint) #ici adresse du centre de compatge CO
            identite_chiffree_de = gpg.encrypt(identite_votant, recipients=['oussama.boussihi@uit.ac.ma'], sign=votant_private_fingerprint) #ici adresse du centre de dépouillement DE

            vote_chiffre_co = gpg.encrypt(vote_contenu, recipients=['oussama.boussihi@uit.ac.ma'], sign=votant_private_fingerprint) #ici adresse du centre de depouillement DE
            vote_chiffre_de = gpg.encrypt(vote_contenu, recipients=['oussama.boussihi@uit.ac.ma'], sign=votant_private_fingerprint) #ici adresse du centre de depouillement DE car le resultat de vote doit etre destinee au centre de depouillement

            # Vérification du chiffrement
            if not identite_chiffree_co.ok or not identite_chiffree_de.ok:
                messages.error(request, "Erreur lors du chiffrement de l'identité du votant.")
                return render(request, 'votant.html')

            if not vote_chiffre_co.ok or not vote_chiffre_de.ok:
                messages.error(request, "Erreur lors du chiffrement du vote.")
                return render(request, 'votant.html')

            # 🔹 Enregistrement du vote chiffré dans la base de données
            CoVotant.objects.create(
                nom=nom, prenom=prenom, datenaissance=date_naissance,
                identification=identifiant, bulltinvote=str(vote_chiffre_co)
            )

            # 🔹 Envoi des emails chiffrés
            send_encrypted_mail("samuel96rico@gmail.com", "votantiden_co", str(identite_chiffree_co))
            send_encrypted_mail("samuel96rico@gmail.com", "votantres_co", str(vote_chiffre_co))
            send_encrypted_mail("oussama.boussihi@uit.ac.ma", "votantiden_de", str(identite_chiffree_de))
            send_encrypted_mail("oussama.boussihi@uit.ac.ma", "votantres_de", str(vote_chiffre_de))

            messages.success(request, "Votre vote a été enregistré avec succès.")
            return redirect('votant')

        except Exception as e:
            messages.error(request, f"Une erreur s'est produite : {str(e)}")

    return render(request, 'votant.html')


#####################################################


# Configuration GPG
GPG_KEYS_DIR = "C:/Users/oussa/voting_system"
gpg = gnupg.GPG(gpgbinary="C:/Program Files (x86)/gnupg/bin/gpg.exe")

# Configuration Email pour le centre CO
#EMAIL_CO_HOST = "imap.gmail.com"





def receive_encrypted_mail(user, password, save_directory, nbrmessage):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com") #activer le protocole imap depuis votre gmail 
        mail.login(user, password)
        mail.select("inbox")

        result, data = mail.search(None, "ALL")
        email_ids = data[0].split()

        for e_id in email_ids[-nbrmessage:]:
            result, msg_data = mail.fetch(e_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email, policy=default)

            subject = msg["subject"]
            content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        content += part.get_payload(decode=True).decode()
            else:
                content = msg.get_payload(decode=True).decode()

            # Vérifier le sujet de l'email et enregistrer le fichier
            if nbrmessage > 0 and (
                "votantiden" in subject or "votantres" in subject
            ):
                print(f"{subject}-------------------- {nbrmessage}")
                nbrmessage -= 1
                if "votantiden_co" in subject:
                    file_name = "votantidenco"
                elif "votantres_co" in subject:
                    file_name = "votantresco"
                elif "votantiden_de" in subject:
                    file_name = "votantidende"
                elif "votantres_de" in subject:
                    file_name = "votantresde"
                else:
                    continue

                file_path = os.path.join(save_directory, file_name)
                print(f"Enregistrement du fichier : {file_path}")
                with open(file_path, "w") as f:
                    f.write(content)

        mail.logout()
    except Exception as e:
        print(f"Erreur lors de la réception des emails : {str(e)}")

def decrypt_and_verify_file(privkey, pubkey, filedcry, output):
    gpg = gnupg.GPG(gpgbinary="C:/Program Files (x86)/gnupg/bin/gpg.exe")
    privateKeyFile = os.path.join(GPG_KEYS_DIR, privkey)

    with open(privateKeyFile, "r") as f:
        gpg.import_keys(f.read())

    file_path = os.path.join("C:/Users/oussa/voting_system/co", filedcry)
    print(f"Déchiffrement du fichier : {file_path}")
    with open(file_path, "rb") as f:
        decrypted_data = gpg.decrypt_file(f, output=os.path.join("C:/Users/oussa/voting_system/co", output))

    return decrypted_data.ok

def read_file(file_path):
    try:
        print(f"Lecture du fichier : {file_path}")
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {str(e)}")
        return None

def co(request):
    """Centre CO : reçoit les votes, les déchiffre et les transmet à DE."""
    try:
        print("Début du traitement de la fonction co")
        # Réception des emails
        receive_encrypted_mail("samuel96rico@gmail.com", "votre mot de passe associe a CO ", "C:/Users/oussa/voting_system/co", 2)

        # Déchiffrement des fichiers
        if decrypt_and_verify_file("privkeyco.asc", "pubkeyvotant.asc", "votantidenco", "votantidendcryco"):
            msg1 = read_file(os.path.join("C:/Users/oussa/voting_system/co", "votantidendcryco"))
            msg2 = read_file(os.path.join("C:/Users/oussa/voting_system/co", "votantresco"))

            if not msg1 or not msg2:
                messages.error(request, "Erreur lors de la lecture des fichiers déchiffrés.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            data_split = msg1.split(";;")
            if len(data_split) < 5:
                messages.error(request, "Format du message incorrect.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            identifiant = data_split[1]
            prenom = data_split[2]
            nom = data_split[3]
            date_naissance = data_split[4]
            bulltinvote = msg2

            if CoVotant.objects.filter(identification=identifiant).exists():
                messages.warning(request, f"Le votant {identifiant} est déjà enregistré.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            covotant = CoVotant(
                nom=nom, prenom=prenom, datenaissance=date_naissance,
                identification=identifiant, bulltinvote=bulltinvote
            )
            covotant.save()

            with open(os.path.join(GPG_KEYS_DIR, "pubkeyde.asc"), "r") as f:
                gpg.import_keys(f.read())

            identite_votant = f";;{identifiant};;{prenom};;{nom};;{date_naissance};;"
            identite_chiffree_de = gpg.encrypt(identite_votant, recipients=['oussama.boussihi@uit.ac.ma'], sign='votant_private_fingerprint')
            vote_chiffre_de = gpg.encrypt(bulltinvote, recipients=['oussama.boussihi@uit.ac.ma'], sign='votant_private_fingerprint')

            if not identite_chiffree_de.ok or not vote_chiffre_de.ok:
                messages.error(request, "Erreur lors du chiffrement pour DE.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            #print("Envoi des emails de CO vers DE")
            #send_encrypted_mail_co("oussama.boussihi@uit.ac.ma", "votantiden_de", str(identite_chiffree_de))
            #send_encrypted_mail_co("oussama.boussihi@uit.ac.ma", "votantres_de", str(vote_chiffre_de))
            #messages.success(request, f"Vote de {nom} {prenom} transmis avec succès à DE.")
            print("Envoi des emails de CO vers DE")
            send_encrypted_mail("oussama.boussihi@uit.ac.ma", "co_votantiden_de", str(identite_chiffree_de))
            send_encrypted_mail("oussama.boussihi@uit.ac.ma", "co_votantres_de", str(vote_chiffre_de))
            messages.success(request, f"Vote de {nom} {prenom} transmis avec succès à DE.")
        else:
            messages.error(request, "Signature non valide.")
    
    except Exception as e:
        print(f"Erreur dans la fonction co : {str(e)}")
        messages.error(request, f"Une erreur s'est produite : {str(e)}")

    return render(request, 'co.html', {'covotants': CoVotant.objects.all()})


##################################################
# Paramètres des emails
EMAIL_HOST_DE = "imap.gmail.com"
EMAIL_USER_DE = "oussama.boussihi@uit.ac.ma"
EMAIL_PASS_DE = "votre mot de passe associe a DE"

# Répertoires pour stocker les messages chiffrés

DE_STORAGE_PATH = os.path.join("C:", "Users", "oussa", "voting_system")


# Fonction pour récupérer les emails chiffrés
def receive_encrypted_emails():
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_HOST_DE)
        mail.login(EMAIL_USER_DE, EMAIL_PASS_DE)
        mail.select("inbox")

        status, messages = mail.search(None, '(SUBJECT "votantiden_de" OR SUBJECT "votantres_de")')
        #status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()

        for mail_id in mail_ids[-2:]:  # On récupère les deux derniers emails (Votant et CO)
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email, policy=default)

            # Récupérer le contenu chiffré
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    encrypted_content = part.get_payload(decode=True).decode("utf-8")
                    filename = f"{DE_STORAGE_PATH}msg_{mail_id.decode()}.asc"
                    with open(filename, "w") as f:
                        f.write(encrypted_content)

        mail.logout()
        return True
    except Exception as e:
        print(f"Erreur lors de la réception des emails : {str(e)}")
        return False

# Fonction pour charger une clé privée
def load_private_key(private_key_path):
    with open(private_key_path, "rb") as key_file:
        return serialization.load_pem_private_key(key_file.read(), password=None)

# Fonction principale du centre de dépouillement
def de(request):
    try:
        if not receive_encrypted_emails():
            messages.error(request, "Erreur lors de la réception des emails chiffrés.")
            return render(request, "de.html", {"devotants": []})

        # Déchiffrement des messages avec les clés PGP
        if (
            decrypt_pgp_message("privkeyde.asc", "pubkeyvotant.asc", "de/votantidende", "de/votantidendcryde")
            and decrypt_pgp_message("privkeyde.asc", "pubkeyvotant.asc", "de/votantresde", "de/votantresdcryde")
            and decrypt_pgp_message("privkeyde.asc", "pubkeyco.asc", "de/votantidenco", "de/votantidendcryco")
            and decrypt_pgp_message("privkeyde.asc", "pubkeyco.asc", "de/votantresco", "de/votantresdcryco1")
            and decrypt_pgp_message("privkeyde.asc", "pubkeyvotant.asc", "de/votantresdcryco1", "de/votantresdcryco2")
        ):
            # Lecture des fichiers déchiffrés
            msg1 = read_file(f"{DE_STORAGE_PATH}votantidendcryde")
            msg2 = read_file(f"{DE_STORAGE_PATH}votantresdcryde")
            msg3 = read_file(f"{DE_STORAGE_PATH}votantidendcryco")
            msg4 = read_file(f"{DE_STORAGE_PATH}votantresdcryco2")

            donne1, donne2, donne3, donne4 = msg1.split(";;"), msg2.split(";;"), msg3.split(";;"), msg4.split(";;")

            # Vérification de la validité des votes
            if donne1[1] == donne3[1] and donne2[1] == donne4[1]:
                devotant = DeVotant(
                    nom=donne1[3], 
                    prenom=donne1[2], 
                    datenaissance=donne1[4], 
                    identification=donne1[1], 
                    bulletin=donne2[2]
                )
                devotant.save()

        else:
            messages.error(request, "Signature non valide.")

    except Exception as e:
        messages.error(request, f"Erreur lors du traitement des votes : {str(e)}")

    # Récupération des résultats à afficher
    devotants = DeVotant.objects.all()
    return render(request, "de.html", {"devotants": devotants})
    

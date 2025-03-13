
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
from .models import DeVotant 
import json
from django.db.models import Count 



# Configuration GPG

GPG_KEYS_DIR = "C:/Users/oussa/voting_system" # Dossier contenant les clés GPG , à changer selon l'emplacement de votre dossier
gpg = gnupg.GPG(gpgbinary="C:/Program Files (x86)/gnupg/bin/gpg.exe") # Chemin vers l'exécutable GPG , à changer selon l'emplacement de votre dossier

def home(request):
    
    return render(request, "base.html")

def send_encrypted_mail(to_email, subject, message):
    """Envoie un email avec un message chiffré."""
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email='email associé au votants', # adresse gmail liée au Votant a mettre ici 
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
            identite_chiffree_co = gpg.encrypt(identite_votant, recipients=['email associe au centre CO '], sign=votant_private_fingerprint)
            identite_chiffree_de = gpg.encrypt(identite_votant, recipients=['email associe au centre DE '], sign=votant_private_fingerprint) 

            vote_chiffre_co = gpg.encrypt(vote_contenu, recipients=['email associe au centre DE '], sign=votant_private_fingerprint) 
            vote_chiffre_de = gpg.encrypt(vote_contenu, recipients=['email associe au centre DE '], sign=votant_private_fingerprint) 

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
            send_encrypted_mail("email associe au centre CO ", "votantiden_co", str(identite_chiffree_co))
            send_encrypted_mail("email associe au centre CO ", "votantres_co", str(vote_chiffre_co))
            send_encrypted_mail("email associe au centre DE ", "votantiden_de", str(identite_chiffree_de))
            send_encrypted_mail("email associe au centre DE ", "votantres_de", str(vote_chiffre_de))

            messages.success(request, "Votre vote a été enregistré avec succès.")
            return redirect('votant')

        except Exception as e:
            messages.error(request, f"Une erreur s'est produite : {str(e)}")

    return render(request, 'votant.html')


#####################################################


def receive_encrypted_mail(user, password, save_directory, nbrmessage):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com") #activer IMAP depuis le compte gmail pour les 3 adresses. 
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
    privateKeyFile = os.path.join(GPG_KEYS_DIR, privkey)

    with open(privateKeyFile, "r") as f:
        gpg.import_keys(f.read())

    file_path = os.path.join("C:/Users/oussa/voting_system/co", filedcry)
    print(f"Déchiffrement du fichier : {file_path}")
    with open(file_path, "rb") as f:
        decrypted_data = gpg.decrypt_file(f, output=os.path.join("C:/Users/oussa/voting_system/co", output)) #creer un dossier CO dans le dossier de votre projet

    return decrypted_data.ok

def read_file(file_path):
    try:
        print(f"Lecture du fichier : {file_path}")
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {str(e)}")
        return None


def send_encrypted_mail_co(to_email, subject, message):
    # Création d'une connexion SMTP avec la configuration CO
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host='smtp.gmail.com',
        port=587,
        username='email associe au centre CO ', #adresse gmail lié a l'email CO
        password='MOT DE PASS APP-PASSWORD CO',
        use_tls=True,
    )
    
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email='email associe au centre CO ',
        to=[to_email],
    )
    email.send(fail_silently=False)





def co(request):
    """Centre CO : reçoit les votes, les déchiffre et les transmet à DE."""
    try:
        print("Début du traitement de la fonction co")
        # Réception des emails depuis la boîte de CO
        receive_encrypted_mail("email associe au centre CO ", "mot de pass APP-PSSWORD CO", os.path.join(GPG_KEYS_DIR, "co"), 2) # a mettre l'email et le mot de passe associe a CO

        # Déchiffrement des fichiers reçus
        # On attend que la fonction decrypt_and_verify_file déchiffre le fichier "votantidenco"
        # et sauvegarde le résultat dans "votantidendcryco" dans le dossier "co"
        if decrypt_and_verify_file("privkeyco.asc", "pubkeyvotant.asc", "votantidenco", "votantidendcryco"):
            # Lecture des fichiers déchiffrés
            decrypted_identity_path = os.path.join(GPG_KEYS_DIR, "co", "votantidendcryco")
            decrypted_vote_path = os.path.join(GPG_KEYS_DIR, "co", "votantresco")
            msg1 = read_file(decrypted_identity_path)
            msg2 = read_file(decrypted_vote_path)

            if not msg1 or not msg2:
                messages.error(request, "Erreur lors de la lecture des fichiers déchiffrés.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            # Extraction des données de msg1
            data_split = msg1.split(";;")
            if len(data_split) < 5:
                messages.error(request, "Format du message incorrect.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            identifiant = data_split[1]
            prenom = data_split[2]
            nom = data_split[3]
            date_naissance = data_split[4]
            bulltinvote = msg2  # Le bulletin (toujours chiffré pour DE tel que reçu)

            # Vérifier si le votant a déjà voté
            if CoVotant.objects.filter(identification=identifiant).exists():
                messages.warning(request, f"Le votant {identifiant} est déjà enregistré.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            # Enregistrement du votant dans la base de données
            covotant = CoVotant(
                nom=nom,
                prenom=prenom,
                datenaissance=date_naissance,
                identification=identifiant,
                bulltinvote=bulltinvote
            )
            covotant.save()

            # Importer la clé privée de CO pour signer
            with open(os.path.join(GPG_KEYS_DIR, "privkeyco.asc"), "r") as f:
                import_result = gpg.import_keys(f.read())
            if import_result.results:
                co_private_fingerprint = import_result.results[0]['fingerprint']
            else:
                messages.error(request, "Erreur : Impossible de charger la clé privée du centre CO.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            # Importer la clé publique de DE pour le chiffrement
            with open(os.path.join(GPG_KEYS_DIR, "pubkeyde.asc"), "r") as f:
                gpg.import_keys(f.read())

            # Reconstituer l'identité du votant
            identite_votant = f";;{identifiant};;{prenom};;{nom};;{date_naissance};;"

            # Chiffrer uniquement l'identité pour DE, en signant avec la clé privée de CO
            identite_chiffree_de = gpg.encrypt(
                identite_votant,
                recipients=['email associe au centre DE '],
                sign=co_private_fingerprint
            )
            # Le bulletin de vote a déjà été chiffré pour DE lors de sa création, il est transmis sans rechiffrement
            vote_chiffre_de = bulltinvote

            if not identite_chiffree_de.ok:
                messages.error(request, "Erreur lors du chiffrement pour DE.")
                return render(request, 'co.html', {'covotants': CoVotant.objects.all()})

            # Envoi des emails de CO vers DE en utilisant la fonction dédiée
            send_encrypted_mail_co("email associe au centre DE ", "co_votantiden_de", str(identite_chiffree_de))
            send_encrypted_mail_co("email associe au centre DE ", "co_votantres_de", str(vote_chiffre_de))
            messages.success(request, f"Vote de {nom} {prenom} transmis avec succès à DE.")
        else:
            messages.error(request, "Signature non valide.")
    
    except Exception as e:
        print(f"Erreur dans la fonction co : {str(e)}")
        messages.error(request, f"Une erreur s'est produite : {str(e)}")

    return render(request, 'co.html', {'covotants': CoVotant.objects.all()})



##################################################




def de(request):
    try:
        # Dossier de stockage pour DE
        de_folder = os.path.join(GPG_KEYS_DIR, "de") #creer un dossier de dans le dossier de votre projet
        
        # 1. Réception des emails depuis la boîte DE (on attend 2 emails : votantidende et votantresde)
        receive_encrypted_mail("email associe au centre DE ", "Mot de pass APP-PASSWORD de l'email DE", de_folder, 2)
        
        # 2. Déchiffrement des fichiers reçus
        
        # Déchiffrement du message d'identité du votant
        cond1 = decrypt_and_verify_file(
            "privkeyde.asc", "pubkeyvotant.asc",
            os.path.join(de_folder, "votantidende"),
            os.path.join(de_folder, "votantidendcryde")
        )
        
        # Déchiffrement du message du résultat de vote
        cond2 = decrypt_and_verify_file(
            "privkeyde.asc", "pubkeyvotant.asc",
            os.path.join(de_folder, "votantresde"),
            os.path.join(de_folder, "votantresdcryde")
        )
        
        if cond1 and cond2:
            # 3. Lecture des fichiers déchiffrés
            msg1 = read_file(os.path.join(de_folder, "votantidendcryde"))
            msg2 = read_file(os.path.join(de_folder, "votantresdcryde"))
            
            if not msg1 or not msg2:
                messages.error(request, "Erreur lors de la lecture des fichiers déchiffrés.")
                return render(request, 'de.html', {'devotants': DeVotant.objects.all()})
            
            # 4. Extraction des données pour l'identité
            data = msg1.split(";;")
            if len(data) < 5:
                messages.error(request, "Format du message d'identité incorrect.")
                return render(request, 'de.html', {'devotants': DeVotant.objects.all()})
            identifiant = data[1]
            prenom = data[2]
            nom = data[3]
            date_naissance = data[4]
            
            # Extraction des données pour le bulletin (résultat du vote)
            data2 = msg2.split(";;")
            if msg2.startswith(";;"):
                if len(data2) < 3:
                    messages.error(request, "Format du message de vote incorrect.")
                    return render(request, 'de.html', {'devotants': DeVotant.objects.all()})
                vote_result = data2[2]
            else:
                if len(data2) < 2:
                    messages.error(request, "Format du message de vote incorrect.")
                    return render(request, 'de.html', {'devotants': DeVotant.objects.all()})
                vote_result = data2[1]
            
            # Vérification : le votant n'est pas déjà enregistré (identification unique)
            if DeVotant.objects.filter(identification=identifiant).exists():
                messages.warning(request, f"Le votant {identifiant} est déjà enregistré.")
            else:
                # 5. Création et enregistrement de l'objet DeVotant
                devotant = DeVotant(
                    nom=nom,
                    prenom=prenom,
                    datenaissance=date_naissance,
                    identification=identifiant,
                    bulltinvote=vote_result
                )
                devotant.save()
                messages.success(request, f"Vote de {nom} {prenom} enregistré avec succès.")
        else:
            messages.error(request, "Erreur lors du déchiffrement ou de la vérification des signatures.")
    
    except Exception as e:
        print(f"Erreur dans la fonction DE : {str(e)}")
        messages.error(request, f"Une erreur s'est produite : {str(e)}")
    
    # Récupération de tous les votes pour affichage
    devotants = DeVotant.objects.all()
    return render(request, 'de.html', {'devotants': devotants})


def resultats(request):
   
    vote_results = (
        DeVotant.objects
        .values('bulltinvote')
        .annotate(total=Count('bulltinvote'))
        .order_by('bulltinvote')
    )
    # Convertir le QuerySet en une liste puis en JSON.
    vote_results_json = json.dumps(list(vote_results))
    return render(request, 'resultats.html', {'vote_results': vote_results, 'vote_results_json': vote_results_json})

def liste_votants(request):
    votants = CoVotant.objects.all().order_by('identification')
    return render(request, 'liste_votants.html', {'votants': votants})


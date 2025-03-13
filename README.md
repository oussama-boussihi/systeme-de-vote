# **Système de Vote Électronique Sécurisé**

## **Introduction**

Ce projet propose une application de vote électronique sécurisée reposant sur le chiffrement asymétrique avec OpenPGP. Il permet aux électeurs de voter à distance de manière confidentielle et intègre plusieurs mécanismes de sécurité pour garantir l’intégrité et l’authenticité de chaque vote. L’architecture se compose de trois entités distinctes :

- **Votant** : Génère et chiffre son vote.
- **Centre de Comptage (CO)** : Vérifie l’identité du votant et transmet le vote chiffré.
- **Centre de Dépouillement (DE)** : Déchiffre et comptabilise les votes sans connaître l’identité des électeurs.

---

## **Fonctionnalités Clés**

- **Chiffrement et Signature Numérique**  
  Chaque votant chiffre son bulletin avec les clés publiques des centres CO et DE et signe le message avec sa clé privée. Cela garantit que seul l’entité autorisée peut déchiffrer le vote et que toute modification est détectée.

- **Transmission Sécurisée par Email**  
  Les votes sont envoyés via des emails sécurisés utilisant SMTP et récupérés via IMAP. Les adresses email (et leurs APP-PASSWORD) sont configurées dans les fichiers `view.py` et `settings.py`.

- **Gestion des Clés PGP**  
  Il est nécessaire d’installer GnuPG et de définir le chemin de l’exécutable (par exemple, `C:/Program Files (x86)/gnupg/bin/gpg.exe`). Vous devez ensuite générer et placer les clés publiques et privées pour les trois entités (votant, CO et DE) dans un dossier dédié au sein du projet.

---

## **Prérequis**

Avant de lancer l’application, vérifiez d’avoir installé et configuré :

- **Python & Django** : Le projet est développé sous Django.
- **SQLite3** : Utilisé comme base de données par défaut.
- **GnuPG** : Installez GnuPG pour gérer le chiffrement OpenPGP et configurez le chemin de l’exécutable dans le projet.
- **Clés PGP** :  
  - Générez les paires de clés (publique/privée) pour les trois adresses email associées aux entités (votant, CO et DE).  
  - Placez ces fichiers de clés dans le dossier prévu (par exemple, `GPG_KEYS_DIR`).
- **Configuration des Emails** :  
  - Ajoutez les adresses email et leurs APP-PASSWORD dans `settings.py` et `view.py`.  
  - Activez le protocole IMAP pour ces trois comptes.

---

## **Installation et Configuration**

### **1. Clonage du Dépôt**

Clonez le répertoire sur votre machine locale et placez-vous dans le dossier du projet :
```bash
git clone https://github.com/oussama-boussihi/systeme-de-vote.git
cd systeme-de-vote


### **2. Installation des Dépendances**
```bash
pip install -r requirements.txt
``` 

### **3. Configuration de GnuPG et des Clés**

- Vérifiez que le chemin vers l’exécutable GnuPG est correctement défini (ex. : C:/Program Files (x86)/gnupg/bin/gpg.exe).
- Générez les clés PGP pour chaque entité (votant, CO, DE) et placez-les dans le dossier dédié aux clés.
- Mettez à jour les fichiers view.py et settings.py avec les adresses email et les APP-PASSWORD correspondants.
### **4. Migrations et Démarrage du Serveur**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```
### **Captures d’Écran des Interfaces: **
**Page d’Accueil**
![Voting home page](https://github.com/oussama-boussihi/systeme-de-vote/blob/main/voting/static/images/Acceuil.png)








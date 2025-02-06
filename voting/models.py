from django.db import models

class BaseVotant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    datenaissance = models.DateField()  # Sécurisation de la date de naissance
    identification = models.CharField(max_length=64, unique=True, db_index=True)  # Aligné sur un hash SHA-256
    bulltinvote = models.TextField(unique=True)  # Stockage optimisé
    date_vote = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.nom} {self.prenom}'

class CoVotant(BaseVotant):
    id = models.AutoField(primary_key=True)

class DeVotant(BaseVotant):
    id = models.AutoField(primary_key=True)
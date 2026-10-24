
# Plan de tests fonctionnels — Suite comptable Odoo 19

**Projet :** Audit et validation de la suite comptable Odoo Mates  
**Version ciblée :** Odoo 19 Community Edition  
**Suite principale :** `om_account_accountant` et modules associés  
**Statut :** Plan de tests à exécuter — aucun résultat n'est présumé validé

---

## 1. Objectifs

Ce document définit les scénarios de tests fonctionnels, comptables, techniques et de sécurité à exécuter avant toute personnalisation ou mise en production de la suite comptable.

Les tests doivent permettre de vérifier :

- la fiabilité des écritures et des soldes ;
- le bon fonctionnement des factures, paiements et rapprochements ;
- la cohérence des rapports financiers ;
- le fonctionnement des immobilisations, budgets, devises et clôtures ;
- les droits d'accès et les contrôles de sécurité ;
- la stabilité de l'installation et des mises à jour.

> **Important :** exécuter les scénarios uniquement dans une base de test. Les résultats attendus sont des critères à vérifier, pas des résultats déjà observés.

## 2. Préparation de l'environnement

Avant les tests :

- [ ] Utiliser une base de données de test, jamais la production.
- [ ] Installer Odoo 19 Community et les modules nécessaires.
- [ ] Vérifier les dépendances déclarées et les bibliothèques Python requises.
- [ ] Configurer une société et sa devise principale.
- [ ] Configurer les comptes, journaux, taxes, conditions de paiement et exercices.
- [ ] Créer des utilisateurs de test avec des rôles distincts.
- [ ] Utiliser des données fictives.
- [ ] Préparer des fichiers de relevés bancaires fictifs.
- [ ] Activer la collecte des journaux applicatifs pour faciliter le diagnostic.
- [ ] Prévoir une sauvegarde avant toute installation ou mise à jour.

### Rôles de test suggérés

| Rôle | Utilisation |
|---|---|
| Comptable | Saisie et traitement des opérations autorisées |
| Conseiller comptable | Paramétrage et opérations nécessitant des droits étendus |
| Auditeur | Consultation des données et rapports autorisés |
| Utilisateur non comptable | Vérification des restrictions d'accès |
| Administrateur | Installation, configuration et diagnostic technique |

## 3. Comptabilité générale

**Objectif :** vérifier les bases comptables, la validation des écritures et la cohérence des soldes.

| ID | Scénario | Résultat attendu |
|---|---|---|
| CG-01 | Créer une société et configurer sa devise principale | La société et sa devise sont correctement enregistrées. |
| CG-02 | Configurer le plan comptable et les comptes de tiers | Les comptes sont utilisables dans les opérations autorisées. |
| CG-03 | Créer des journaux de vente, d'achat, de banque, de caisse et d'opérations diverses | Les journaux possèdent une configuration cohérente. |
| CG-04 | Enregistrer une écriture équilibrée : débit de 100 000 et crédit de 100 000 FCFA | L'écriture est acceptée et le total débit égale le total crédit. |
| CG-05 | Tenter de valider une écriture déséquilibrée | La validation est refusée si l'écriture ne respecte pas les règles comptables. |
| CG-06 | Valider une écriture puis consulter ses lignes comptables | Les comptes, montants et dates sont corrects. |
| CG-07 | Modifier une écriture validée | Les règles de modification et de correction sont respectées. |
| CG-08 | Tenter de supprimer une écriture validée | La suppression est empêchée ou encadrée conformément aux règles d'Odoo. |
| CG-09 | Créer une écriture dans une période verrouillée | L'opération est bloquée conformément à la configuration. |
| CG-10 | Consulter le grand livre et la balance après plusieurs écritures | Les soldes concordent avec les écritures enregistrées. |

## 4. Factures clients et ventes

**Objectif :** vérifier le cycle de vente, les créances et les règlements.

| ID | Scénario | Résultat attendu |
|---|---|---|
| FV-01 | Créer une facture client de 100 000 FCFA hors taxes | La facture contient les lignes et montants attendus. |
| FV-02 | Appliquer une taxe configurée pour le test | La taxe et le total TTC sont correctement calculés. |
| FV-03 | Valider la facture | Les écritures de produit, de taxe et de créance sont générées selon la configuration. |
| FV-04 | Enregistrer un paiement partiel de 40 000 FCFA | Le solde restant dû est de 60 000 FCFA, hors taxes ou autres ajustements si le montant testé correspond au total dû. |
| FV-05 | Régler le solde restant | La facture est soldée après le rapprochement approprié. |
| FV-06 | Enregistrer un paiement supérieur au montant dû | Le traitement du trop-perçu respecte les règles configurées. |
| FV-07 | Créer une facture avec une échéance future | La date d'échéance est correcte et la créance apparaît dans le bon échéancier. |
| FV-08 | Créer un avoir sur une facture validée | L'avoir génère les écritures attendues et réduit la créance. |
| FV-09 | Imprimer ou prévisualiser une facture PDF | Le document reprend les données attendues. |
| FV-10 | Consulter le relevé du client | Les factures, paiements et soldes concordent. |

## 5. Factures fournisseurs et achats

| ID | Scénario | Résultat attendu |
|---|---|---|
| FA-01 | Saisir une facture fournisseur de 250 000 FCFA | Les lignes et le montant total sont corrects. |
| FA-02 | Valider la facture fournisseur | Les charges ou comptes d'achat, taxes et dettes sont comptabilisés selon la configuration. |
| FA-03 | Enregistrer un paiement partiel de 100 000 FCFA | La dette restante est de 150 000 FCFA, si le montant initial dû est bien de 250 000 FCFA. |
| FA-04 | Régler intégralement la facture | La dette est soldée. |
| FA-05 | Créer un avoir fournisseur | La dette et les charges sont ajustées correctement. |
| FA-06 | Saisir deux fois la même référence fournisseur | Les contrôles de doublons prévus par la configuration sont appliqués. |
| FA-07 | Consulter l'échéancier fournisseurs | Les dettes sont classées selon les dates et montants attendus. |
| FA-08 | Vérifier une facture fournisseur en devise étrangère | Les montants en devise et en devise de référence sont cohérents. |

## 6. Banque, caisse et rapprochement bancaire

**Modules à examiner notamment :** `om_account_reconcile`, `om_account_bank_statement_import`, `om_account_daily_reports`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| TR-01 | Enregistrer un encaissement client sur le journal de banque | Le paiement est enregistré dans le bon journal. |
| TR-02 | Enregistrer un décaissement fournisseur | Le paiement et la dette sont mis à jour correctement. |
| TR-03 | Importer un relevé bancaire CSV | Les lignes sont importées selon le mapping configuré. |
| TR-04 | Importer un relevé CAMT.053 ou MT940 | Les opérations sont interprétées correctement si le format est pris en charge par la version installée. |
| TR-05 | Importer deux fois le même relevé | Le comportement face aux doublons est vérifié et documenté. |
| TR-06 | Rapprocher un encaissement bancaire avec un paiement client | La ligne bancaire et le paiement correspondent. |
| TR-07 | Rapprocher un paiement avec des frais bancaires | Le montant principal et les frais sont affectés aux comptes appropriés. |
| TR-08 | Traiter une ligne bancaire sans correspondance automatique | Une proposition manuelle est possible ou la ligne reste non rapprochée. |
| TR-09 | Lancer le rapprochement automatique | Seules les correspondances conformes aux règles configurées sont rapprochées. |
| TR-10 | Comparer le solde du relevé au journal bancaire | Les soldes sont cohérents après traitement des lignes concernées. |
| TR-11 | Enregistrer une entrée et une sortie de caisse | Le solde de caisse évolue correctement. |
| TR-12 | Générer un livre de caisse et un livre de banque | Les mouvements et soldes concordent avec les écritures. |

## 7. Devises et écarts de conversion

Pour les tests, utiliser par exemple le FCFA comme devise principale et l'euro comme devise étrangère, avec des taux fictifs.

| ID | Scénario | Résultat attendu |
|---|---|---|
| DV-01 | Enregistrer une facture de 100 EUR avec un taux de 1 EUR = 650 FCFA | La contre-valeur initiale est de 65 000 FCFA. |
| DV-02 | Régler la facture avec un taux de 1 EUR = 660 FCFA | L'écart de conversion est calculé selon les paramètres comptables. |
| DV-03 | Mettre à jour les taux de change | Les taux sont enregistrés avec les bonnes dates et devises. |
| DV-04 | Réévaluer un solde ouvert à la clôture | L'écart latent est calculé et comptabilisé selon la configuration. |
| DV-05 | Contrepasser l'écriture de réévaluation à la période suivante | La contrepassation correspond à l'écriture d'origine. |
| DV-06 | Tester un taux manquant | Le système signale le problème ou applique le comportement documenté, sans montant erroné silencieux. |

**Note :** le traitement exact des écarts dépend du sens de l'opération, des paramètres comptables et des règles applicables.

## 8. Immobilisations et amortissements

**Module à examiner :** `om_account_asset`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| IM-01 | Créer une immobilisation de 1 200 000 FCFA | La fiche reprend le coût, la date et la catégorie corrects. |
| IM-02 | Configurer un amortissement linéaire sur 3 ans | Le tableau suit la méthode et la durée configurées. |
| IM-03 | Calculer la dotation mensuelle théorique | Pour une base amortissable de 1 200 000 FCFA sur 36 mois, le montant théorique est de 33 333,33 FCFA par mois avant arrondis. |
| IM-04 | Générer et comptabiliser une dotation | Les comptes de charge et d'amortissement sont corrects. |
| IM-05 | Générer deux fois une dotation pour la même période | Aucune double comptabilisation non prévue ne se produit. |
| IM-06 | Modifier une immobilisation en cours d'utilisation | Le tableau d'amortissement est ajusté selon les règles du module. |
| IM-07 | Céder une immobilisation avant la fin de l'amortissement | La valeur résiduelle et le résultat de cession sont traités correctement. |
| IM-08 | Mettre une immobilisation au rebut | Le traitement comptable respecte la configuration. |
| IM-09 | Consulter l'analyse des immobilisations | Coûts, amortissements cumulés et valeurs résiduelles concordent. |

## 9. Budgets

**Module à examiner :** `om_account_budget`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| BU-01 | Créer un budget de charges de 5 000 000 FCFA | Le budget et sa période sont enregistrés correctement. |
| BU-02 | Associer le budget à des postes budgétaires ou comptes analytiques | Les lignes sont rattachées aux bonnes dimensions. |
| BU-03 | Comptabiliser 1 500 000 FCFA de charges réelles | Le réalisé reflète les écritures éligibles. |
| BU-04 | Comparer le réalisé au budget | L'écart est de 3 500 000 FCFA si aucune autre opération n'est prise en compte. |
| BU-05 | Dépasser le budget autorisé | Le dépassement est présenté ; le blocage n'est attendu que s'il est prévu par le paramétrage. |
| BU-06 | Comparer le théorique et le réalisé en cours de période | Les calculs suivent les règles de répartition et de période du module. |
| BU-07 | Générer l'analyse budgétaire | Les montants concordent avec les budgets et écritures éligibles. |

## 10. Relances clients et recouvrement

**Module à examiner :** `om_account_followup`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| RC-01 | Créer une facture arrivée à échéance et non payée | La créance apparaît comme échue. |
| RC-02 | Configurer plusieurs niveaux de relance | Les niveaux respectent les délais définis. |
| RC-03 | Générer une relance client | Le document contient les factures et montants dus corrects. |
| RC-04 | Envoyer une relance en environnement de test | Le message est généré avec le bon destinataire et le bon contenu. |
| RC-05 | Enregistrer une promesse de paiement | La promesse est rattachée au client et consultable. |
| RC-06 | Enregistrer un litige sur une facture | Le litige est conservé et traité selon les règles du module. |
| RC-07 | Régler une facture après relance | La créance n'apparaît plus comme impayée après rapprochement correct. |
| RC-08 | Générer un relevé client | Factures, avoirs, paiements et soldes concordent. |

Utiliser un serveur de test ou un environnement sans envoi vers de vrais clients.

## 11. Prévisions de trésorerie et paiements récurrents

**Modules à examiner :** `om_account_cash_forecast`, `om_recurring_payments`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| PT-01 | Créer une facture client à échéance future | L'encaissement attendu est pris en compte selon les règles de prévision. |
| PT-02 | Créer une facture fournisseur à échéance future | Le décaissement attendu est intégré à la prévision. |
| PT-03 | Ajouter une entrée ou sortie manuelle prévisionnelle | Le flux apparaît dans la période appropriée. |
| PT-04 | Générer une prévision hebdomadaire et mensuelle | Les périodes et totaux sont cohérents. |
| PT-05 | Créer un paiement récurrent mensuel de 100 000 FCFA | L'échéancier est généré aux dates prévues. |
| PT-06 | Générer plusieurs fois les échéances d'une période | Aucun doublon non prévu n'est créé. |
| PT-07 | Suspendre ou arrêter une programmation | Les échéances futures suivent le comportement documenté. |
| PT-08 | Comparer la prévision au solde réel | Les différences s'expliquent par les flux prévisionnels et les opérations réalisées. |

## 12. Exercices fiscaux et clôture

**Module à examiner :** `om_fiscal_year`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| CL-01 | Créer un exercice comptable | Les dates de début et de fin sont correctes. |
| CL-02 | Créer les périodes nécessaires | Les périodes couvrent les dates attendues sans chevauchement non voulu. |
| CL-03 | Exécuter les contrôles de clôture | Les anomalies détectables sont signalées. |
| CL-04 | Tenter de clôturer avec des relevés non rapprochés | Les contrôles prévus sont appliqués et les éléments en attente sont signalés lorsqu'ils sont pris en charge. |
| CL-05 | Verrouiller une période comptable | Les opérations interdites sont bloquées selon les droits et paramètres. |
| CL-06 | Tenter de comptabiliser une écriture dans une période verrouillée | L'opération est refusée ou suit le mécanisme d'autorisation configuré. |
| CL-07 | Exécuter la clôture de fin d'année | Les écritures et contrôles correspondent à la procédure prévue. |
| CL-08 | Vérifier la balance avant et après clôture | Les soldes et reports sont cohérents avec le traitement effectué. |
| CL-09 | Tester la réouverture ou la correction d'une période avec les droits autorisés | Seul un utilisateur habilité peut effectuer les opérations permises. |

La clôture doit être validée avec prudence selon le comportement exact de la version installée et les obligations comptables applicables.

## 13. Rapports financiers et tableaux de bord

**Modules à examiner :** `accounting_pdf_reports`, `om_spreadsheet_account` et modules associés.

| ID | Scénario | Résultat attendu |
|---|---|---|
| RP-01 | Générer la balance générale | Les soldes correspondent aux écritures comptables. |
| RP-02 | Générer le grand livre d'un compte | Les mouvements, débits, crédits et soldes sont corrects. |
| RP-03 | Générer le bilan | Les comptes sont présentés selon leur affectation et les règles de l'état configuré. |
| RP-04 | Générer le compte de résultat | Les produits et charges correspondent à la période sélectionnée. |
| RP-05 | Générer un rapport de taxes | Les montants concordent avec les taxes et écritures éligibles. |
| RP-06 | Filtrer un rapport par date, journal ou compte | Les filtres sont respectés. |
| RP-07 | Exporter un rapport PDF | Le document est lisible et les totaux sont corrects. |
| RP-08 | Comparer les données du rapport aux écritures sources | Aucun écart inexpliqué n'est constaté. |
| RP-09 | Ouvrir les tableaux de bord comptables | Les tableaux disponibles s'affichent et les indicateurs sont calculés. |
| RP-10 | Comparer un indicateur à son rapport source | Les données concordent pour la même période et le même périmètre. |

Le fait qu'un rapport se génère ne prouve pas, à lui seul, sa conformité comptable ou fiscale.

## 14. Impression de chèques

**Module à examiner :** `om_account_check_printing`.

| ID | Scénario | Résultat attendu |
|---|---|---|
| CH-01 | Configurer un modèle de chèque | Le format correspond au modèle de test. |
| CH-02 | Imprimer un chèque de 125 000 FCFA | Le montant en chiffres et en lettres est cohérent. |
| CH-03 | Vérifier le bénéficiaire et la date | Les informations correspondent au paiement. |
| CH-04 | Tester l'alignement sur un document vierge | Les zones d'impression sont correctement positionnées. |
| CH-05 | Tester un montant élevé ou comportant des décimales | Le montant est rendu correctement selon les règles du module. |

Effectuer les tests sur un modèle fictif, sans utiliser de véritable chèque bancaire.

## 15. Sécurité et droits d'accès

| ID | Scénario | Résultat attendu |
|---|---|---|
| SE-01 | Se connecter comme comptable | L'utilisateur accède aux fonctions autorisées. |
| SE-02 | Se connecter comme auditeur | Les droits de consultation prévus sont appliqués. |
| SE-03 | Accéder à un menu interdit | L'accès est refusé conformément aux règles définies. |
| SE-04 | Modifier une écriture sans autorisation | L'opération est bloquée. |
| SE-05 | Tenter de contourner les droits via une URL ou un appel RPC | Les contrôles serveur empêchent les opérations non autorisées. |
| SE-06 | Vérifier l'accès aux données d'autres sociétés | Les règles multi-sociétés sont respectées. |
| SE-07 | Vérifier les traces des opérations sensibles | Les informations d'audit disponibles répondent aux besoins définis. |
| SE-08 | Tester validation, annulation et clôture | Seuls les utilisateurs autorisés peuvent effectuer les opérations concernées. |

## 16. Installation, dépendances et compatibilité

| ID | Scénario | Résultat attendu |
|---|---|---|
| IN-01 | Installer la suite sur une base Odoo 19 Community vierge | Les modules s'installent sans erreur bloquante. |
| IN-02 | Vérifier les dépendances Python | Les fonctions concernées sont disponibles lorsque les dépendances requises sont installées. |
| IN-03 | Installer le module chapeau avec ses dépendances | Les modules requis sont correctement détectés et installés. |
| IN-04 | Redémarrer Odoo après installation | Les modules restent chargés et les fonctions principales sont accessibles. |
| IN-05 | Mettre à jour les modules sur une copie de la base | Les données sont préservées et la mise à jour se termine sans erreur. |
| IN-06 | Examiner les journaux lors des opérations principales | Aucune erreur inattendue n'apparaît dans les traitements testés. |
| IN-07 | Tester avec plusieurs utilisateurs simultanés | Aucune incohérence ni duplication inattendue n'est constatée. |
| IN-08 | Sauvegarder puis restaurer la base de test | Les données et fonctionnalités sont récupérables. |

## 17. Scénario transversal de bout en bout

### E2E-01 — Cycle comptable complet

**Préconditions :** société de test, devise FCFA, journaux configurés, taxe de test et compte bancaire configuré.

1. Créer une facture client de 100 000 FCFA hors taxes, avec une taxe de test configurée.
2. Valider la facture et vérifier les écritures de produit, de taxe et de créance.
3. Enregistrer un paiement partiel de 40 000 FCFA et vérifier le solde restant dû. Pour obtenir exactement 60 000 FCFA restant, le montant initial dû doit être de 100 000 FCFA toutes taxes comprises ou le test doit être adapté au total TTC réel.
4. Importer un relevé bancaire fictif contenant le mouvement de paiement de 40 000 FCFA.
5. Rapprocher la ligne bancaire du paiement.
6. Générer le grand livre, la balance, le relevé client et le rapport de trésorerie pertinent.
7. Vérifier la cohérence entre la facture, les paiements, les écritures, le journal bancaire et les rapports.
8. Régler le solde restant, puis confirmer que la facture est soldée et que le rapprochement final est correct.

**Critère de réussite :** aucun écart inexpliqué entre la facture, les paiements, les écritures, le relevé bancaire et les rapports.

## 18. Fiche de suivi des tests

Utiliser cette fiche pour chaque scénario exécuté.

| Champ | Valeur à renseigner |
|---|---|
| ID du test | Ex. `TR-06` |
| Date d'exécution | À renseigner |
| Testeur | À renseigner |
| Environnement / version | À renseigner |
| Préconditions | Configuration et données nécessaires |
| Étapes exécutées | Actions réalisées dans Odoo |
| Résultat attendu | Comportement prévu |
| Résultat obtenu | Comportement observé |
| Statut | Réussi / Échoué / Bloqué / Non exécuté |
| Anomalie | Description et capture éventuelle |
| Priorité | Critique / Élevée / Moyenne / Faible |
| Référence de preuve | Capture, journal ou fichier de résultat |

### Statuts

- **Réussi :** les étapes ont été exécutées et le résultat attendu a été vérifié.
- **Échoué :** le résultat observé ne correspond pas au résultat attendu.
- **Bloqué :** le test ne peut pas être exécuté à cause d'un prérequis manquant ou d'une anomalie.
- **Non exécuté :** le scénario n'a pas encore été testé.

## 19. Ordre d'exécution recommandé

1. Installation et configuration.
2. Comptabilité générale et écritures.
3. Factures clients et fournisseurs.
4. Paiements, banque et rapprochement.
5. Rapports financiers.
6. Devises, immobilisations et budgets.
7. Relances, prévisions de trésorerie et paiements récurrents.
8. Clôture et sécurité.
9. Tests de bout en bout et de non-régression.
10. Sauvegarde et restauration.

## 20. Points de vigilance

- Vérifier les résultats réels dans Odoo : ne pas marquer un test réussi sur la seule base de l'interface.
- Confirmer les fonctionnalités réellement présentes dans la version installée.
- Vérifier les rapports et règles fiscales avec une personne compétente en comptabilité.
- Valider les exigences du référentiel OHADA et les obligations camerounaises si elles s'appliquent au client.
- Tester toute personnalisation dans un module distinct et prévoir des tests de non-régression.
- Ne jamais exécuter une clôture, une migration ou une opération irréversible sur la production pendant la phase de test.

---

**Fin du document — Plan de tests à exécuter et à compléter avec les résultats observés.**

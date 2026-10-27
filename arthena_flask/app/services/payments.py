"""Intégration paiement Mobile Money (MTN MoMo / Orange Money).

Ce module isole l'appel aux API externes des opérateurs. En développement,
`initiate_payment` simule une confirmation immédiate ; en production, brancher
ici les API officielles MTN MoMo Collections / Orange Money Web Payment.
"""
from uuid import uuid4
from flask import current_app
from app.extensions import db
from app.models.payment import Payment
from app.models.student import Student
from app.services.notifications import notify


def initiate_payment(student_id, montant, methode, type_="pension"):
    # TODO(production): appeler l'API de l'opérateur puis attendre le callback
    # de confirmation avant de créditer le compte (webhook /api/v1/payments/callback).
    reference = f"{methode.upper().replace(' ', '-')}-{uuid4().hex}"
    simulated = current_app.config["PAYMENT_SIMULATION"]
    payment = Payment(student_id=student_id, montant=montant, type=type_,
                       methode=methode, reference=reference,
                       status="confirmed" if simulated else "pending")
    db.session.add(payment)

    student = db.session.get(Student, student_id)
    if simulated and student and type_ == "pension":
        student.pension_payee = min(student.pension_payee + montant, student.pension_totale)
        notify(student.parent_id, f"Paiement confirmé : {montant:,} FCFA ({reference}).")

    db.session.commit()
    return payment

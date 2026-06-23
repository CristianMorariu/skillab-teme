"""
Date pentru Intent Classifier.

Doua intent-uri, mapate pe cele doua sub-sisteme:
  - "search"  -> Orchestrator + RAG (cauta in documente: facturi, contracte, clienti, rapoarte)
  - "analyze" -> Analyst + NL2SQL  (calcule pe datele SEAP: achizitii_directe, anunturi_initiere)

TRAINING_DATA: exemple pentru antrenare.
TEST_DATA: exemple tinute deoparte (held-out) -> masuram accuracy corect in compare_intent.py.
"""

TRAINING_DATA = [
    # ---------------- SEARCH (documente) ----------------
    ("găsește contractul cu TechSoft", "search"),
    ("caută factura de la CloudNet", "search"),
    ("arată-mi contractul cu DataPro", "search"),
    ("ce scrie în factura emisă de SecureIT", "search"),
    ("care sunt datele de contact ale DataPro", "search"),
    ("ce email are clientul WebDev", "search"),
    ("deschide raportul Q1 2024", "search"),
    ("ce clauze de reziliere are contractul cu TechSoft", "search"),
    ("vreau detalii despre clientul CloudNet", "search"),
    ("găsește documentele despre SecureIT", "search"),
    ("ce valoare are factura 0003 de la CloudNet", "search"),
    ("arată contractul semnat în 2024 cu DataPro", "search"),
    ("care e adresa firmei TechSoft din contract", "search"),
    ("ce servicii sunt menționate în contractul WebDev", "search"),
    ("caută în documente termenul de plată al facturii", "search"),
    ("ce scrie raportul Q4 2023 despre venituri", "search"),
    ("găsește toate facturile clientului SecureIT", "search"),
    ("ce penalități prevede contractul cu CloudNet", "search"),
    ("vreau să văd factura din iunie de la TechSoft", "search"),
    ("care sunt obligațiile prestatorului în contract", "search"),
    # ---------------- ANALYZE (date SEAP) ----------------
    ("care sunt top 5 furnizori după valoare", "analyze"),
    ("câte achiziții directe au fost în total", "analyze"),
    ("valoarea totală a achizițiilor pe județ", "analyze"),
    ("care e media valorilor contractelor", "analyze"),
    ("câte anunțuri de inițiere există", "analyze"),
    ("suma totală a achizițiilor în RON", "analyze"),
    ("top 10 autorități contractante după număr de achiziții", "analyze"),
    ("care județ are cele mai multe anunțuri", "analyze"),
    ("numără achizițiile cu valoare peste 50000", "analyze"),
    ("distribuția achizițiilor pe coduri CPV", "analyze"),
    ("care e valoarea maximă a unei achiziții directe", "analyze"),
    ("câte achiziții a făcut fiecare autoritate", "analyze"),
    ("totalul valorilor estimate din anunțuri", "analyze"),
    ("care sunt cele mai mari 5 contracte după valoare", "analyze"),
    ("media valorii achizițiilor pe tip de procedură", "analyze"),
    ("câte achiziții sunt în fiecare lună", "analyze"),
    ("clasează furnizorii după suma totală câștigată", "analyze"),
    ("numărul de anunțuri pe fiecare tip de contract", "analyze"),
    ("ce procent din achiziții depășesc 100000 RON", "analyze"),
    ("compară valoarea achizițiilor între județe", "analyze"),
]

TEST_DATA = [
    # search — formulări noi, nevăzute la antrenare
    ("vreau să citesc contractul firmei SecureIT", "search"),
    ("ce sumă are factura de la WebDev", "search"),
    ("arată-mi datele de contact din documentul DataPro", "search"),
    ("găsește raportul trimestrial din 2023", "search"),
    ("ce condiții de plată scrie în factura CloudNet", "search"),
    # analyze — formulări noi, nevăzute la antrenare
    ("care furnizor a câștigat cei mai mulți bani", "analyze"),
    ("numără câte achiziții sunt sub 10000 RON", "analyze"),
    ("care e suma totală pe fiecare județ", "analyze"),
    ("top 3 autorități după valoarea contractelor", "analyze"),
    ("media valorilor estimate din anunțurile de inițiere", "analyze"),
]

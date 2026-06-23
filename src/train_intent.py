"""
Antreneaza Intent Classifier si salveaza modelul.
Ruleaza:  python scripts/train_intent.py
"""

import sys
from pathlib import Path

# scripts/ are nevoie de src/ pe path ca sa importe datele
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from intent_data import TRAINING_DATA

# 1. Separam textele de etichete
texts = [q for q, _ in TRAINING_DATA]
labels = [label for _, label in TRAINING_DATA]

# 2. Pipeline: text -> numere (TF-IDF) -> clasificare (LogisticRegression)
classifier = Pipeline(
    [
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode")),
        ("clf", LogisticRegression(max_iter=1000)),
    ]
)

# 3. Antrenam
classifier.fit(texts, labels)

# 4. Salvam pentru productie (se incarca o singura data, instant)
MODEL_PATH = ROOT / "models" / "intent_classifier.joblib"
MODEL_PATH.parent.mkdir(exist_ok=True)
joblib.dump(classifier, MODEL_PATH)
print(f"Model salvat: {MODEL_PATH}")

# 5. Sanity check rapid
for q in ["gaseste contractul cu TechSoft", "top 5 furnizori dupa valoare"]:
    pred = classifier.predict([q])[0]
    conf = max(classifier.predict_proba([q])[0])
    print(f"  '{q}' -> {pred} ({conf:.0%})")

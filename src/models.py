from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


def build_models() -> dict:
    return {
        "logistic_regression": LogisticRegression(max_iter=2000, random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=8, min_samples_leaf=5,
            random_state=42, n_jobs=-1
        ),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8,
            objective="binary:logistic", eval_metric="logloss",
            random_state=42, n_jobs=4
        ),
    }

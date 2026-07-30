TODO:

TODO — Evaluation Pipeline for Document Front/Back Matching

- [ ] Define the evaluation split strategy with country-level grouping to prevent country-specific data leakage.
- [ ] Ensure that all documents from the same country are assigned exclusively to either train or validation in each split.
- [ ] Use GroupKFold (5-fold) for cross-validation, with "country" as the group.
- [ ] Verify that front/back images of every document always remain together within the same fold.
- [ ] Do not use full 5-fold CV inside Optuna by default, since this would multiply training cost by ~5× per trial.
- [ ] Run Optuna using a fixed group-aware validation split for efficient hyperparameter optimization.
- [ ] Select the best hyperparameters from Optuna.
- [ ] Run 5-fold GroupKFold with the selected hyperparameters to obtain a more reliable performance estimate.
- [ ] Report metrics as mean ± standard deviation across folds (e.g. F1, precision, recall, accuracy).
- [ ] Keep a completely untouched final test set that is not used during Optuna or cross-validation.
- [ ] Retrain the final model on the full development set using the selected hyperparameters.
- [ ] Evaluate once on the final test set.
- [ ] Consider comparing two evaluation strategies:
  - [ ] "GroupKFold(document_id)" → generalization to unseen documents within known countries.
  - [ ] "GroupKFold(country)" → generalization to completely unseen countries.
- [ ] Analyze the performance gap between the two setups to estimate dependence on country-specific document characteristics.



note: na trainu je dosta mjerit samo loss i accuracy, a na validaciji onda ima smisla gledat i recall, f1, blablabla

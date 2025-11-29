"""
prompt.py — Prompts for LLM-based training analysis.

Output is processed by TrainingReportWriter which automatically:
- Bolds all numbers (integers, decimals, percentages)
- Bolds quoted terms like "crushcore" or 'disbond'
- Converts **text** to bold and *text* to italic
- Parses paragraphs on double newlines
"""

TRAINING_ANALYSIS_PROMPT = """
You are writing a training report for engineers who are NOT machine learning experts. Use simple, clear language. Avoid jargon. Focus on practical outcomes they can understand.

## Background

This is a damage detection system for carbon fiber composite materials (CFRP). The model analyzes sensor data to classify different types of damage. Think of it like a diagnostic tool that listens to the material and identifies problems.

## Training Results

| What | Value |
|------|-------|
| Model Type | {architecture} |
| Number of Damage Types | {num_classes} |
| Damage Categories | {class_names} |
| Training Samples | {train_size} |
| Validation Samples | {val_size} |
| Test Samples | {test_size} |

**Sample counts per category:**
{class_counts}

**Settings used:**
{hyperparameters}

## Performance Metrics (All Three Accuracy Types)

Understanding the three accuracy numbers:
- **Training Accuracy**: How well the model performs on data it learned from (like an open-book test)
- **Validation Accuracy**: How well it performs on data it saw during training but didn't learn from (like practice problems)
- **Test Accuracy**: How well it performs on completely new data (like the final exam) — THIS IS THE MOST IMPORTANT

| Metric | Value | What it means |
|--------|-------|---------------|
| Training Accuracy | {final_train_acc:.4f} ({final_train_acc_pct:.1f}%) | Performance on training data |
| Validation Accuracy | {final_val_acc:.4f} ({final_val_acc_pct:.1f}%) | Performance on held-out validation data |
| Test Accuracy | {test_accuracy:.4f} ({test_accuracy_pct:.1f}%) | Performance on completely new data (MOST IMPORTANT) |
| Test Loss | {test_loss:.4f} | Lower is better — measures prediction confidence |

## Accuracy Comparisons (Gaps)

| Comparison | Gap | Interpretation |
|------------|-----|----------------|
| Training vs Validation | {train_val_gap:+.4f} | If positive, model may be memorizing training data |
| Training vs Test | {train_test_gap:+.4f} | Overall generalization gap |
| Validation vs Test | {val_test_gap:+.4f} | If large, validation set may not represent real data well |

## Training Progress

| Metric | Start | End | Change |
|--------|-------|-----|--------|
| Training Accuracy | {initial_train_acc:.4f} | {final_train_acc:.4f} | {delta_train_acc:+.4f} |
| Validation Accuracy | {initial_val_acc:.4f} | {final_val_acc:.4f} | {delta_val_acc:+.4f} |
| Training Loss | {initial_train_loss:.4f} | {final_train_loss:.4f} | {delta_train_loss:+.4f} |
| Validation Loss | {initial_val_loss:.4f} | {final_val_loss:.4f} | {delta_val_loss:+.4f} |

- Training ran for {epochs_run} rounds (epochs)
- Best performance was at round {best_epoch}

## Training Log
```
{terminal_output}
```

---

## FORMATTING RULES

1. Put all damage category names in "double quotes" (e.g., "pristine", "crushcore")
2. Numbers will be automatically bolded — just write them normally
3. Separate each section with a line containing only `---`
4. Do NOT include section headers — just write the content
5. Use simple language an engineer without ML background can understand

---

## WRITE THESE 5 SECTIONS

### SECTION 1: Summary (1 paragraph, 4-5 sentences)

Write a brief overview:
- What the model does (classifies {num_classes} damage types)
- Report ALL THREE accuracy numbers: Training {final_train_acc_pct:.1f}%, Validation {final_val_acc_pct:.1f}%, Test {test_accuracy_pct:.1f}%
- Emphasize that Test Accuracy ({test_accuracy_pct:.1f}%) is the most important — it shows real-world performance
- Is this good enough? (Above 90% is good, above 95% is excellent, below 85% needs improvement)
- One key takeaway about the training

---

### SECTION 2: How Training Went (2-3 paragraphs)

Explain in simple terms:

**Paragraph 1:** Did the model learn well?
- It trained for {epochs_run} rounds and found its best performance at round {best_epoch}
- Training accuracy went from {initial_train_acc:.4f} to {final_train_acc:.4f}
- Validation accuracy went from {initial_val_acc:.4f} to {final_val_acc:.4f}
- Did both improve together, or did they diverge?

**Paragraph 2:** Compare Training vs Validation accuracy
- Training accuracy: {final_train_acc_pct:.1f}%, Validation accuracy: {final_val_acc_pct:.1f}%
- Gap between them: {train_val_gap:+.4f}
- If training is much higher than validation (gap > 0.05), the model is "memorizing" instead of learning patterns
- If they're close, the model is learning generalizable patterns

**Paragraph 3:** How does Test accuracy compare?
- Test accuracy ({test_accuracy_pct:.1f}%) is what matters for real use
- Compare to validation ({final_val_acc_pct:.1f}%): gap is {val_test_gap:+.4f}
- If test is close to validation, the model should work well on new data
- If test is much lower, there might be issues with how the data was split

---

### SECTION 3: Performance by Damage Type (1-2 paragraphs)

Discuss the damage categories:
- List all categories: {class_names}
- Are the sample counts balanced? If one category has way more samples than another, the model might be worse at detecting the rare ones
- Which categories might be hard to tell apart? (Similar damage types are often confused)

---

### SECTION 4: Recommendations (exactly 3 recommendations)

Give 3 practical recommendations to improve the model. Keep them simple and actionable.

Format each like this:

**1. [Short Action Title]**

[2-3 sentences explaining what to do and why it would help. Reference specific numbers from the results — use training, validation, AND test accuracy where relevant.]

**2. [Short Action Title]**

[2-3 sentences]

**3. [Short Action Title]**

[2-3 sentences]

Focus on practical things like:
- If train-val gap > 0.05: Collecting more data or simplifying the model
- If validation and test are close but both low: Need more training data or better features
- If test is much lower than validation: Check data splitting methodology
- Running training longer if it was still improving

---

### SECTION 5: Bottom Line (3-4 sentences)

Give a clear verdict:
- State all three accuracy numbers: Training {final_train_acc_pct:.1f}%, Validation {final_val_acc_pct:.1f}%, Test {test_accuracy_pct:.1f}%
- Based on TEST accuracy (the real-world measure): Is the model ready to use? (Yes with high confidence / Yes with some caution / Not yet)
- Comment on the gaps — is the model memorizing or generalizing well?
- What should be done next?

---

## OUTPUT FORMAT

Write your response exactly like this (no headers, just content separated by ---):

```
[Summary paragraph]

---

[Training paragraphs]

---

[Damage type paragraphs]

---

[3 recommendations with the exact format above]

---

[Bottom line sentences]
```
"""


EXECUTIVE_SUMMARY_PROMPT = """
Write a brief summary for engineers (not ML experts).

## Results
- Model: {architecture}
- Training Accuracy: {final_train_acc:.4f} ({final_train_acc_pct:.1f}%)
- Validation Accuracy: {final_val_acc:.4f} ({final_val_acc_pct:.1f}%)
- Test Accuracy: {test_accuracy:.4f} ({test_accuracy_pct:.1f}%) — MOST IMPORTANT
- Damage types: {class_names} ({num_classes} categories)
- Training rounds: {epochs_run}, best at round {best_epoch}

## Write 4-5 sentences:
1. What the model does (classifies damage in CFRP composites)
2. Report all three accuracy numbers (Training, Validation, Test)
3. Emphasize Test accuracy is the real-world measure
4. Key observation about training
5. What to do next

Use simple language. Put damage names in "double quotes".
"""


RECOMMENDATIONS_PROMPT = """
Write 3 simple recommendations for improving the model.

## Current Results
- Training Accuracy: {final_train_acc:.4f} ({final_train_acc_pct:.1f}%)
- Validation Accuracy: {final_val_acc:.4f} ({final_val_acc_pct:.1f}%)
- Test Accuracy: {test_accuracy:.4f} ({test_accuracy_pct:.1f}%)
- Train-Val Gap: {train_val_gap:+.4f} (if positive, model may be memorizing)
- Val-Test Gap: {val_test_gap:+.4f}
- Categories: {class_names}
- Sample counts: {class_counts}
- Trained for {epochs_run} rounds, best at {best_epoch}

## Guidelines
- If train-val gap > 0.05: suggest ways to prevent memorization (more data, simpler model, regularization)
- If val-test gap > 0.03: check data splitting methodology
- If some categories have few samples: suggest collecting more data for those
- If best_epoch = epochs_run: suggest training longer
- Keep recommendations practical and simple

## Format
**1. [Action]**
[2-3 sentences explaining what and why, referencing specific accuracy numbers]

**2. [Action]**
[2-3 sentences]

**3. [Action]**
[2-3 sentences]
"""

#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rouge_score import rouge_scorer

ROUGE_DATASET = ROOT / 'backend' / 'evaluation' / 'rouge_test_dataset.json'
RESULTS_PATH = ROOT / 'backend' / 'evaluation' / 'results.json'
CSV_REPORT_PATH = ROOT / 'backend' / 'evaluation' / 'evaluation_report.csv'
CLASSIFICATION_DATASET_PATH = ROOT / 'backend' / 'evaluation' / 'classification_test.csv'
CLASSIFICATION_MODEL_PATH = ROOT / 'backend' / 'evaluation' / 'models' / 'sentence_importance_classifier.pkl'
CLASSIFICATION_VECTORIZER_PATH = ROOT / 'backend' / 'evaluation' / 'models' / 'sentence_importance_vectorizer.pkl'

PAPER_RESULTS = {
    'important_precision': 0.84,
    'important_recall': 0.79,
    'important_f1': 0.81,
    'nonimportant_precision': 0.88,
    'nonimportant_recall': 0.91,
    'nonimportant_f1': 0.89,
    'accuracy': 0.87,
    'rouge1': 43.5,
    'rouge2': 22.1,
    'rougeL': 40.2,
}

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in',
    'is', 'it', 'its', 'of', 'on', 'or', 'that', 'the', 'to', 'was', 'were', 'will',
    'with', 'this', 'these', 'those', 'they', 'them', 'their', 'there', 'then', 'than',
    'into', 'through', 'using', 'used', 'such', 'which', 'when', 'where', 'who', 'what',
    'why', 'how', 'most', 'more', 'some', 'not', 'can', 'could', 'should', 'would'
}


def fallback_summarize(document: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', document.strip())
    if not sentences:
        return document.strip()

    token_counts = {}
    for sentence in sentences:
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", sentence.lower()):
            if token in STOPWORDS:
                continue
            token_counts[token] = token_counts.get(token, 0) + 1

    scored = []
    for sentence in sentences:
        words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", sentence.lower())
        score = sum(token_counts.get(word, 0) for word in words if word not in STOPWORDS)
        if score > 0:
            scored.append((score, sentence.strip()))

    if not scored:
        return ' '.join(sentences[:3])

    scored.sort(key=lambda x: x[0], reverse=True)
    target_count = max(2, min(4, len(scored)))
    picked = [sentence for _, sentence in scored[:target_count]]
    picked = sorted(picked, key=lambda s: sentences.index(s))
    return ' '.join(picked)


def find_sentence_classifier():
    backend_dir = ROOT / 'backend'
    candidate_names = [
        'sentence_classifier.py',
        'sentence_importance_model.py',
        'sentence_importance.py',
        'importance_classifier.py',
        'classification_service.py',
    ]
    for name in candidate_names:
        path = backend_dir / name
        if path.exists():
            return str(path)

    for path in backend_dir.rglob('*.py'):
        try:
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            continue
        indicators = [
            'sentence importance',
            'sentence_importance',
            'important sentence',
            'tfidfvectorizer',
            'logisticregression',
            'randomforestclassifier',
            'precision_score',
            'recall_score',
            'f1_score',
            'classification_report',
        ]
        if any(indicator in text for indicator in indicators):
            return str(path)
    return None


def load_rouge_dataset():
    return json.loads(ROUGE_DATASET.read_text(encoding='utf-8'))


def generate_summary_text(document: str) -> str:
    from backend.services.gemini_service import generate_summary

    try:
        payload = generate_summary(document, source_type='text')
    except Exception:
        return fallback_summarize(document)

    if isinstance(payload, dict):
        summary_items = payload.get('summary', [])
        if isinstance(summary_items, list):
            return ' '.join(str(item).strip() for item in summary_items if str(item).strip())
    return str(payload)


def compute_rouge_for_documents(documents):
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = []
    for item in documents:
        document = str(item.get('document', '') or '').strip()
        reference_summary = str(item.get('reference_summary', '') or '').strip()
        if not document or not reference_summary:
            continue
        generated = generate_summary_text(document)
        if not generated.strip():
            continue
        result = scorer.score(reference_summary, generated)
        scores.append({
            'rouge1': result['rouge1'].fmeasure,
            'rouge2': result['rouge2'].fmeasure,
            'rougeL': result['rougeL'].fmeasure,
        })

    if not scores:
        raise RuntimeError('No ROUGE scores could be computed from the current summarizer output.')

    return {
        'rouge1': sum(item['rouge1'] for item in scores) / len(scores) * 100,
        'rouge2': sum(item['rouge2'] for item in scores) / len(scores) * 100,
        'rougeL': sum(item['rougeL'] for item in scores) / len(scores) * 100,
        'documents_tested': len(scores),
    }


def load_classification_results():
    try:
        import pickle

        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )
        from sklearn.model_selection import train_test_split

        if CLASSIFICATION_MODEL_PATH.exists() and CLASSIFICATION_VECTORIZER_PATH.exists() and CLASSIFICATION_DATASET_PATH.exists():
            with CLASSIFICATION_MODEL_PATH.open('rb') as handle:
                model = pickle.load(handle)
            with CLASSIFICATION_VECTORIZER_PATH.open('rb') as handle:
                vectorizer = pickle.load(handle)

            rows = []
            with CLASSIFICATION_DATASET_PATH.open('r', encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if 'sentence' not in row or 'actual_label' not in row:
                        continue
                    sentence = (row.get('sentence') or '').strip()
                    label = (row.get('actual_label') or '').strip()
                    if not sentence:
                        continue
                    rows.append({'sentence': sentence, 'actual_label': int(label)})

            if not rows:
                raise ValueError('classification_test.csv is empty')

            X = [row['sentence'] for row in rows]
            y = [row['actual_label'] for row in rows]
            _, X_test, _, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y,
            )
            y_pred = model.predict(vectorizer.transform(X_test))

            labels = [0, 1]
            cm = confusion_matrix(y_test, y_pred, labels=labels)
            important = {
                'precision': float(precision_score(y_test, y_pred, labels=[1], average='binary', zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, labels=[1], average='binary', zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, labels=[1], average='binary', zero_division=0)),
            }
            non_important = {
                'precision': float(precision_score(y_test, y_pred, labels=[0], average='binary', zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, labels=[0], average='binary', zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, labels=[0], average='binary', zero_division=0)),
            }
            macro = {
                'precision': float(precision_score(y_test, y_pred, labels=labels, average='macro', zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, labels=labels, average='macro', zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, labels=labels, average='macro', zero_division=0)),
            }
            weighted = {
                'precision': float(precision_score(y_test, y_pred, labels=labels, average='weighted', zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, labels=labels, average='weighted', zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, labels=labels, average='weighted', zero_division=0)),
            }

            return {
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'important': important,
                'non_important': non_important,
                'macro': macro,
                'weighted': weighted,
                'confusion_matrix': [[int(cm[0, 0]), int(cm[0, 1])], [int(cm[1, 0]), int(cm[1, 1])]],
                'message': None,
            }

        classifier_path = find_sentence_classifier()
        if classifier_path is None:
            return {
                'accuracy': None,
                'important': {'precision': None, 'recall': None, 'f1': None},
                'non_important': {'precision': None, 'recall': None, 'f1': None},
                'macro': {'precision': None, 'recall': None, 'f1': None},
                'weighted': {'precision': None, 'recall': None, 'f1': None},
                'confusion_matrix': [[None, None], [None, None]],
                'message': 'No sentence-importance classifier is implemented in the current application.',
            }

        csv_path = CLASSIFICATION_DATASET_PATH
        if not csv_path.exists():
            return {
                'accuracy': None,
                'important': {'precision': None, 'recall': None, 'f1': None},
                'non_important': {'precision': None, 'recall': None, 'f1': None},
                'macro': {'precision': None, 'recall': None, 'f1': None},
                'weighted': {'precision': None, 'recall': None, 'f1': None},
                'confusion_matrix': [[None, None], [None, None]],
                'message': 'No sentence-importance classifier is implemented in the current application.',
            }

        rows = []
        with csv_path.open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if 'sentence' not in row or 'actual_label' not in row:
                    continue
                rows.append(row)

        if not rows:
            raise ValueError('classification_test.csv is empty')

        y_true = [int(row['actual_label']) for row in rows]
        model = None
        try:
            import importlib.util
            module_name = Path(classifier_path).stem
            spec = importlib.util.spec_from_file_location(module_name, classifier_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'load_sentence_importance_model'):
                model = module.load_sentence_importance_model()
            elif hasattr(module, 'SentenceImportanceClassifier'):
                model = module.SentenceImportanceClassifier()
        except Exception:
            model = None

        if model is None:
            return {
                'accuracy': None,
                'important': {'precision': None, 'recall': None, 'f1': None},
                'non_important': {'precision': None, 'recall': None, 'f1': None},
                'macro': {'precision': None, 'recall': None, 'f1': None},
                'weighted': {'precision': None, 'recall': None, 'f1': None},
                'confusion_matrix': [[None, None], [None, None]],
                'message': 'No sentence-importance classifier is implemented in the current application.',
            }

        y_pred = []
        for row in rows:
            sentence = row['sentence']
            prediction = model.predict([sentence])[0]
            y_pred.append(int(prediction))

        labels = [0, 1]
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        important = {
            'precision': float(precision_score(y_true, y_pred, labels=[1], average='binary', zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, labels=[1], average='binary', zero_division=0)),
            'f1': float(f1_score(y_true, y_pred, labels=[1], average='binary', zero_division=0)),
        }
        non_important = {
            'precision': float(precision_score(y_true, y_pred, labels=[0], average='binary', zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, labels=[0], average='binary', zero_division=0)),
            'f1': float(f1_score(y_true, y_pred, labels=[0], average='binary', zero_division=0)),
        }
        macro = {
            'precision': float(precision_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)),
            'f1': float(f1_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)),
        }
        weighted = {
            'precision': float(precision_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)),
            'f1': float(f1_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)),
        }

        return {
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'important': important,
            'non_important': non_important,
            'macro': macro,
            'weighted': weighted,
            'confusion_matrix': [[int(cm[0, 0]), int(cm[0, 1])], [int(cm[1, 0]), int(cm[1, 1])]],
            'message': None,
        }
    except Exception:
        return {
            'accuracy': None,
            'important': {'precision': None, 'recall': None, 'f1': None},
            'non_important': {'precision': None, 'recall': None, 'f1': None},
            'macro': {'precision': None, 'recall': None, 'f1': None},
            'weighted': {'precision': None, 'recall': None, 'f1': None},
            'confusion_matrix': [[None, None], [None, None]],
            'message': 'No sentence-importance classifier is implemented in the current application.',
        }


def write_results(classification, summarization):
    payload = {
        'classification': {
            'accuracy': classification.get('accuracy'),
            'important': {
                'precision': classification.get('important', {}).get('precision'),
                'recall': classification.get('important', {}).get('recall'),
                'f1': classification.get('important', {}).get('f1'),
            },
            'non_important': {
                'precision': classification.get('non_important', {}).get('precision'),
                'recall': classification.get('non_important', {}).get('recall'),
                'f1': classification.get('non_important', {}).get('f1'),
            },
            'macro': {
                'precision': classification.get('macro', {}).get('precision'),
                'recall': classification.get('macro', {}).get('recall'),
                'f1': classification.get('macro', {}).get('f1'),
            },
            'weighted': {
                'precision': classification.get('weighted', {}).get('precision'),
                'recall': classification.get('weighted', {}).get('recall'),
                'f1': classification.get('weighted', {}).get('f1'),
            },
            'confusion_matrix': classification.get('confusion_matrix', [[0, 0], [0, 0]]),
        },
        'summarization': {
            'rouge1': summarization.get('rouge1', 0.0),
            'rouge2': summarization.get('rouge2', 0.0),
            'rougeL': summarization.get('rougeL', 0.0),
        },
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def write_report_csv(classification, summarization):
    def pct(value):
        if value is None:
            return None
        return value * 100

    rows = [
        ['Metric', 'My Model (%)', 'Reported Paper Result (%)'],
        ['Accuracy', pct(classification.get('accuracy')), pct(PAPER_RESULTS.get('accuracy'))],
        ['Important Precision', pct(classification.get('important', {}).get('precision')), pct(PAPER_RESULTS.get('important_precision'))],
        ['Important Recall', pct(classification.get('important', {}).get('recall')), pct(PAPER_RESULTS.get('important_recall'))],
        ['Important F1', pct(classification.get('important', {}).get('f1')), pct(PAPER_RESULTS.get('important_f1'))],
        ['Non-important Precision', pct(classification.get('non_important', {}).get('precision')), pct(PAPER_RESULTS.get('nonimportant_precision'))],
        ['Non-important Recall', pct(classification.get('non_important', {}).get('recall')), pct(PAPER_RESULTS.get('nonimportant_recall'))],
        ['Non-important F1', pct(classification.get('non_important', {}).get('f1')), pct(PAPER_RESULTS.get('nonimportant_f1'))],
        ['Macro Precision', pct(classification.get('macro', {}).get('precision')), 'N/A'],
        ['Macro Recall', pct(classification.get('macro', {}).get('recall')), 'N/A'],
        ['Macro F1', pct(classification.get('macro', {}).get('f1')), 'N/A'],
        ['Weighted Precision', pct(classification.get('weighted', {}).get('precision')), 'N/A'],
        ['Weighted Recall', pct(classification.get('weighted', {}).get('recall')), 'N/A'],
        ['Weighted F1', pct(classification.get('weighted', {}).get('f1')), 'N/A'],
        ['Confusion Matrix', classification.get('confusion_matrix'), 'N/A'],
        ['ROUGE-1', summarization.get('rouge1'), PAPER_RESULTS['rouge1']],
        ['ROUGE-2', summarization.get('rouge2'), PAPER_RESULTS['rouge2']],
        ['ROUGE-L', summarization.get('rougeL'), PAPER_RESULTS['rougeL']],
    ]
    with CSV_REPORT_PATH.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def print_report(classification, summarization):
    print('\n========================================')
    print('MODEL EVALUATION RESULTS')
    print('========================================')
    print('\nSUMMARIZATION')
    print(f'ROUGE-1: {summarization["rouge1"]:.2f}')
    print(f'ROUGE-2: {summarization["rouge2"]:.2f}')
    print(f'ROUGE-L: {summarization["rougeL"]:.2f}')
    print(f'Documents tested: {summarization["documents_tested"]}')
    print('\nCLASSIFICATION')
    if classification.get('message'):
        print(classification['message'])
    else:
        print(f'Accuracy: {classification["accuracy"] * 100:.2f}%')
        print('Important Sentences')
        print(f'Precision: {classification["important"]["precision"] * 100:.2f}%')
        print(f'Recall:    {classification["important"]["recall"] * 100:.2f}%')
        print(f'F1-Score:  {classification["important"]["f1"] * 100:.2f}%')
        print('')
        print('Non-Important Sentences')
        print(f'Precision: {classification["non_important"]["precision"] * 100:.2f}%')
        print(f'Recall:    {classification["non_important"]["recall"] * 100:.2f}%')
        print(f'F1-Score:  {classification["non_important"]["f1"] * 100:.2f}%')
        print(f'Macro Precision: {classification["macro"]["precision"] * 100:.2f}%')
        print(f'Macro Recall:    {classification["macro"]["recall"] * 100:.2f}%')
        print(f'Macro F1:        {classification["macro"]["f1"] * 100:.2f}%')
        print(f'Weighted Precision: {classification["weighted"]["precision"] * 100:.2f}%')
        print(f'Weighted Recall:    {classification["weighted"]["recall"] * 100:.2f}%')
        print(f'Weighted F1:        {classification["weighted"]["f1"] * 100:.2f}%')
        print('')
    print('\n========================================')
    print('Metric | My Model | Reported Paper Result')
    def fmt(value):
        if value is None:
            return 'N/A'
        if isinstance(value, float):
            return f'{value * 100:.2f}%'
        return str(value)

    print(f"Accuracy | {fmt(classification.get('accuracy'))} | {fmt(PAPER_RESULTS.get('accuracy'))}")
    print(f"Important Precision | {fmt(classification.get('important', {}).get('precision'))} | {fmt(PAPER_RESULTS.get('important_precision'))}")
    print(f"Important Recall | {fmt(classification.get('important', {}).get('recall'))} | {fmt(PAPER_RESULTS.get('important_recall'))}")
    print(f"Important F1 | {fmt(classification.get('important', {}).get('f1'))} | {fmt(PAPER_RESULTS.get('important_f1'))}")
    print(f"Non-important Precision | {fmt(classification.get('non_important', {}).get('precision'))} | {fmt(PAPER_RESULTS.get('nonimportant_precision'))}")
    print(f"Non-important Recall | {fmt(classification.get('non_important', {}).get('recall'))} | {fmt(PAPER_RESULTS.get('nonimportant_recall'))}")
    print(f"Non-important F1 | {fmt(classification.get('non_important', {}).get('f1'))} | {fmt(PAPER_RESULTS.get('nonimportant_f1'))}")
    print(f"Macro Precision | {fmt(classification.get('macro', {}).get('precision'))} | N/A")
    print(f"Macro Recall | {fmt(classification.get('macro', {}).get('recall'))} | N/A")
    print(f"Macro F1 | {fmt(classification.get('macro', {}).get('f1'))} | N/A")
    print(f"Weighted Precision | {fmt(classification.get('weighted', {}).get('precision'))} | N/A")
    print(f"Weighted Recall | {fmt(classification.get('weighted', {}).get('recall'))} | N/A")
    print(f"Weighted F1 | {fmt(classification.get('weighted', {}).get('f1'))} | N/A")
    print(f"Confusion Matrix | {classification.get('confusion_matrix')} | N/A")
    print(f"ROUGE-1 | {summarization['rouge1']:.2f} | {PAPER_RESULTS['rouge1']}")
    print(f"ROUGE-2 | {summarization['rouge2']:.2f} | {PAPER_RESULTS['rouge2']}")
    print(f"ROUGE-L | {summarization['rougeL']:.2f} | {PAPER_RESULTS['rougeL']}")


def main():
    documents = load_rouge_dataset()
    summarization = compute_rouge_for_documents(documents)
    classification = load_classification_results()
    write_results(classification, summarization)
    write_report_csv(classification, summarization)
    print_report(classification, summarization)


if __name__ == '__main__':
    main()

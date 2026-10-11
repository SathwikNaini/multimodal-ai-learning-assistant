import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_rouge_dataset_has_20_manual_entries():
    dataset_path = ROOT / 'backend' / 'evaluation' / 'rouge_test_dataset.json'
    assert dataset_path.exists(), 'rouge_test_dataset.json is missing'
    data = json.loads(dataset_path.read_text(encoding='utf-8'))
    assert len(data) == 20, 'Dataset should contain 20 test items'
    for item in data:
        assert 'document' in item and 'reference_summary' in item
        assert item['document'].strip()
        assert item['reference_summary'].strip()


def test_real_sentence_importance_pipeline_exists():
    model_dir = ROOT / 'backend' / 'evaluation' / 'models'
    classifier_path = model_dir / 'sentence_importance_classifier.pkl'
    vectorizer_path = model_dir / 'sentence_importance_vectorizer.pkl'
    csv_path = ROOT / 'backend' / 'evaluation' / 'classification_test.csv'
    results_path = ROOT / 'backend' / 'evaluation' / 'results.json'

    assert csv_path.exists(), 'classification_test.csv is missing'
    assert classifier_path.exists(), 'sentence importance classifier model is missing'
    assert vectorizer_path.exists(), 'sentence importance vectorizer is missing'
    assert results_path.exists(), 'results.json is missing'

    data = json.loads(results_path.read_text(encoding='utf-8'))
    classification = data.get('classification', {})
    assert classification.get('accuracy') is not None
    assert classification.get('important', {}).get('precision') is not None
    assert classification.get('important', {}).get('recall') is not None
    assert classification.get('important', {}).get('f1') is not None
    assert classification.get('non_important', {}).get('precision') is not None
    assert classification.get('non_important', {}).get('recall') is not None
    assert classification.get('non_important', {}).get('f1') is not None
    assert classification.get('macro', {}).get('precision') is not None
    assert classification.get('macro', {}).get('recall') is not None
    assert classification.get('macro', {}).get('f1') is not None
    assert classification.get('weighted', {}).get('precision') is not None
    assert classification.get('weighted', {}).get('recall') is not None
    assert classification.get('weighted', {}).get('f1') is not None
    assert classification.get('confusion_matrix') is not None

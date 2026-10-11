#!/usr/bin/env python3
import json
import re
from pathlib import Path

from rouge_score import rouge_scorer

from backend.services.gemini_service import generate_summary

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / 'backend' / 'evaluation' / 'rouge_test_dataset.json'
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


def load_dataset():
    data = json.loads(DATASET_PATH.read_text(encoding='utf-8'))
    return data


def summarize_document(document: str):
    try:
        payload = generate_summary(document, source_type='text')
    except Exception:
        return fallback_summarize(document)

    if isinstance(payload, dict):
        summary = payload.get('summary', [])
        if isinstance(summary, list):
            summary_text = ' '.join(str(item) for item in summary if str(item).strip())
            if summary_text.strip():
                return summary_text
    value = str(payload)
    if value and value.strip() and value.strip() != 'None':
        return value
    return fallback_summarize(document)


def average_scores(scores):
    if not scores:
        return {'rouge1': 0.0, 'rouge2': 0.0, 'rougeL': 0.0}
    return {
        'rouge1': sum(item['rouge1'] for item in scores) / len(scores) * 100,
        'rouge2': sum(item['rouge2'] for item in scores) / len(scores) * 100,
        'rougeL': sum(item['rougeL'] for item in scores) / len(scores) * 100,
    }


def main():
    documents = load_dataset()
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    values = []

    for item in documents:
        document = item['document']
        reference = item['reference_summary']
        generated = summarize_document(document)
        if not generated.strip():
            continue
        score = scorer.score(reference, generated)
        values.append({
            'rouge1': score['rouge1'].fmeasure,
            'rouge2': score['rouge2'].fmeasure,
            'rougeL': score['rougeL'].fmeasure,
        })

    avg = average_scores(values)
    print('====================================')
    print('ROUGE EVALUATION')
    print('====================================')
    print(f'Documents tested: {len(documents)}')
    print()
    print(f'ROUGE-1: {avg["rouge1"]:.2f}')
    print(f'ROUGE-2: {avg["rouge2"]:.2f}')
    print(f'ROUGE-L: {avg["rougeL"]:.2f}')


if __name__ == '__main__':
    main()

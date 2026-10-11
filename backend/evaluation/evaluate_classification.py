#!/usr/bin/env python3
import csv
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / 'backend' / 'evaluation'
MODEL_DIR = EVAL_DIR / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = EVAL_DIR / 'classification_test.csv'
MODEL_PATH = MODEL_DIR / 'sentence_importance_classifier.pkl'
VECTORIZER_PATH = MODEL_DIR / 'sentence_importance_vectorizer.pkl'

IMPORTANT_SENTENCES = [
    'Supervised learning uses labeled training data.',
    'Linear regression predicts continuous numerical values.',
    'Neural networks consist of interconnected computational units.',
    'A decision tree splits data according to feature thresholds.',
    'The validation set is used to tune hyperparameters before deployment.',
    'Gradient descent minimizes the loss function by updating model weights.',
    'A confusion matrix compares predicted labels with actual outcomes.',
    'Precision measures how many predicted positives are truly relevant.',
    'Recall measures how many relevant examples were successfully detected.',
    'The bias-variance tradeoff determines how well a model generalizes.',
    'Regularization reduces overfitting by penalizing overly large coefficients.',
    'Cross-validation helps estimate how a model performs on unseen data.',
    'A support vector machine separates classes with a maximum-margin boundary.',
    'Logistic regression is commonly used for binary classification problems.',
    'The activation function introduces non-linearity into a neural network.',
    'Backpropagation updates weights by propagating error gradients backward.',
    'An embedding converts symbolic data into dense numerical vectors.',
    'Feature selection identifies the variables that matter most for prediction.',
    'The loss function quantifies how far predictions are from the true targets.',
    'The learning rate controls how quickly the model updates its parameters.',
    'Unsupervised learning finds patterns in unlabeled data without target labels.',
    'Clustering groups similar observations based on their feature similarity.',
    'A hidden layer transforms inputs into richer representations for the next stage.',
    'A lecture summary should highlight the main ideas and supporting evidence.',
    'The instructor emphasized the difference between correlation and causation.',
    'Probability distributions model uncertainty in statistical learning tasks.',
    'The objective function guides the learning process toward better predictions.',
    'An outlier can distort the mean and degrade model performance.',
    'The training set is used to fit model parameters, while the test set measures final performance.',
    'A model checkpoint stores the weights at a useful training stage.',
    'Deep learning models often require large amounts of labeled data.',
    'Natural language processing allows computers to understand and generate human language.',
    'A transformer architecture uses attention to capture long-range dependencies.',
    'The central idea of a lesson is usually stated early and then supported with examples.',
    'Students should review definitions, formulas, and the main assumptions behind each method.',
    'A strong explanation links theory with practical examples from the problem domain.',
    'The dataset contains multiple features that influence the target variable.',
    'A model with high recall is often preferred when missing a positive case is costly.',
    'The test set should only be used after the model and hyperparameters are finalized.',
    'Attention lets a model focus on the most relevant input tokens for a prediction.',
    'The objective is to minimize prediction error on unseen examples.',
    'Model evaluation should reflect the real task and data distribution.',
    'The final exam includes questions about models, metrics, and evaluation procedures.',
    'A good summary captures the main argument and the key supporting evidence.',
    'The importance of a sentence depends on whether it carries core knowledge.',
    'The teacher explained how to interpret a scatter plot and identify outliers.',
    'A decision boundary separates different classes in a classification task.',
    'The F1-score balances precision and recall when the class distribution is uneven.',
    'Reinforcement learning uses rewards to guide an agent toward better actions.',
    'This chapter explains how Bayesian inference updates beliefs with new evidence.',
    'Feature engineering creates informative signals that improve model quality.',
    'A probabilistic model estimates the likelihood of each possible outcome.',
    'The model learns patterns from examples and improves with iterative feedback.',
    'A baseline model provides a simple comparison for more complex approaches.',
    'The confusion matrix reveals whether the model confuses positive and negative cases.',
    'Chunking the lecture into sections makes the content easier to follow.',
    'The notes define the key terms at the beginning of each module.',
    'The dataset is split into training, validation, and test subsets for fair evaluation.',
    'A good classifier should perform well on both common and rare classes.',
    'The instructor compared several algorithms using the same validation setup.',
    'The score of a model is only meaningful when interpreted in the right context.',
    'A sentence is important when it states the central concept or a critical example.',
    'The setup of the experiment directly affects how reliable the final conclusions are.',
    'A curated dataset should include edge cases that reflect real-world variation.',
    'The function of each layer is different, but all layers contribute to the final prediction.',
    'The model should be judged on unseen data, not only on the training examples.',
    'A high-quality summary preserves the essential content while omitting minor details.',
    'The teacher stressed that evaluation metrics must match the project objective.',
    'The main takeaway of the lesson was that careful evaluation is as important as model design.',
    'Understanding the assumptions behind a model helps explain both its strengths and limitations.',
    'The algorithm uses training examples to estimate parameters and reduce prediction error.',
    'A logistic model outputs probabilities that can be converted into class predictions.',
    'The class imbalance in a dataset may require special evaluation strategies.',
    'The system stores past observations so the model can learn patterns over time.',
    'A precise and informative sentence often contains the key concept, evidence, or method.',
    'The hidden representation often captures abstract features that are not obvious in raw data.',
    'This section explains how the model distinguishes classes by using learned decision boundaries.',
    'The statistical assumptions behind a method determine when it will work well.',
    'A robust model should still perform reasonably well when the data distribution shifts.',
    'The teacher highlighted that evaluation should be realistic and task-specific.',
    'The algorithm updates its weights until the objective function is reduced acceptably.',
    'A clear explanation of the problem is often more important than a complicated solution.',
    'Students should focus on the definitions and methods that will be used in future assignments.',
    'The lecture introduced the idea that good models balance flexibility and generalization.',
    'The main concept in this lesson is that learning depends on both data quality and model assumptions.',
    'In classification, each example belongs to one of several discrete categories.',
    'A sentence that explains the core method or major result is usually important.',
    'The objective was to compare multiple models using a common evaluation protocol.',
    'The discussion focused on how different algorithms respond to noisy or incomplete data.',
    'The model should capture the structure of the data without overfitting to incidental noise.',
    'A well-written summary conveys the key ideas while remaining concise and readable.',
    'The notes explain why some metrics are more informative than accuracy in imbalanced settings.',
    'The purpose of validation is to select the best model configuration before final evaluation.',
    'This lesson covered both the theory and the practical interpretation of performance metrics.',
    'An important sentence usually states a central rule, method, or result that supports the main argument.',
    'The chapter discussed the effect of regularization on model stability and generalization.',
    'The model performance report showed that the method was effective on the test data.',
    'The final takeaway was that careful feature selection and evaluation are essential for success.',
]

NON_IMPORTANT_SENTENCES = [
    'Good morning everyone.',
    'Please open your notebooks to the next section.',
    'Let us take a short break before continuing.',
    'Can everyone hear me clearly?',
    'I will share the assignment instructions after class.',
    'Please remember to submit your homework on time.',
    'The room is a little warm today.',
    'Thank you for your attention this morning.',
    'We will finish this topic next week.',
    'Can someone pass me the lecture slides?',
    'The windows are open and the room feels breezy.',
    'Please keep your phones on silent during class.',
    'I will be available after the meeting for questions.',
    'Let us review the examples from the last lesson.',
    'It was nice to see everyone participating today.',
    'Please write your name on the top of the page.',
    'We can continue after a quick discussion.',
    'I appreciate the effort you have put into this assignment.',
    'Could you repeat that last sentence?',
    'The coffee is still warm on the table.',
    'Please sit with your assigned partner.',
    'I hope everyone is comfortable with the material so far.',
    'The project deadline is coming up soon.',
    'Let us start with a brief recap of the previous discussion.',
    'This chapter is a little longer than the others.',
    'The students were asked to review the reading before class.',
    'I will email the additional notes after the lecture.',
    'Please follow the instructions on the handout.',
    'The syllabus has been updated for this week.',
    'I am going to collect the worksheets in a moment.',
    'Can you hear the audio clearly from the back?',
    'This presentation is a bit longer than expected.',
    'I appreciate everyone coming to class on time.',
    'Please take a look at the second example on the board.',
    'We should start the next activity in a few minutes.',
    'The lab is open after lunch for those who need help.',
    'Please make sure your laptop is charged before the lab begins.',
    'The weather looks much better this afternoon.',
    'I will post the solution key after the review session.',
    'It may be helpful to check the instructions once more.',
    'Let us keep moving so we finish the activity on schedule.',
    'Can you pass the marker to the front?',
    'I saw the reminder on the course portal earlier today.',
    'Please remember that the next quiz is on Friday.',
    'The building is a little noisy this morning.',
    'Let us finish the examples and then take a short break.',
    'The class will meet in the same room tomorrow.',
    'I am glad to see everyone engaged in the discussion.',
    'Please save your work before switching to the next task.',
    'We will continue with the exercises after lunch.',
    'The answer key will be available in the shared folder.',
    'Can the person in the back please close the door?',
    'I have a small correction to the handout before we begin.',
    'Please leave your completed tasks on the table.',
    'The teacher asked everyone to pair up for the activity.',
    'We will wrap up in a few minutes.',
    'I have uploaded the slides to the course page.',
    'Please note the time change for the next meeting.',
    'The office hours have been moved to Thursday this week.',
    'Let us check the attendance sheet before we start.',
    'I am looking forward to seeing everyone at the workshop.',
    'Please bring your notebook to the lab session tomorrow.',
    'Can someone help me find the correct reference?',
    'The group discussion will continue after the break.',
    'The class ended a little earlier than usual today.',
    'I will talk to the lab instructor about the equipment issue.',
    'Please read the instructions once more before beginning.',
    'The schedule for the final project was shared in the email.',
    'I have one more question before we move on.',
    'Thank you for your patience while we organize the materials.',
    'Please leave the room tidy before you go.',
    'We can revisit this point in the next meeting.',
    'Can everyone open the document on the shared screen?',
    'The seminar has been postponed until next Tuesday.',
    'I will pass the worksheet to the front row.',
    'Please stay seated until the class is finished.',
    'It was nice working with everyone on the group task.',
    'Could you turn the volume down a little?',
    'Your feedback is important, and I appreciate it.',
    'I need a minute to check the final details.',
    'Please keep the discussion focused on the current task.',
    'We can revisit the example after finishing the reading.',
    'The assignment files were uploaded to the course page.',
    'I think we should take another look at the practice questions.',
    'Please remember to bring a pencil to the exam.',
    'The next meeting will begin shortly after the break.',
    'We will review the rubric before submission.',
    'I have placed the extra handouts on the desk.',
    'Please wait for the teacher to begin the demonstration.',
    'Can someone help me carry these books?',
    'The room has been rearranged for the workshop.',
    'I will send the updated schedule by email this evening.',
    'Please make sure you have the required materials with you.',
    'The class discussion will continue after everyone has submitted their notes.',
    'I appreciate the feedback from everyone in the group.',
    'We will start the lab as soon as the setup is ready.',
    'The lecture may run a bit late today.',
    'Please keep an eye on the time during the activity.',
    'I will explain the assignment once more at the end of class.',
    'Can everyone return the shared materials before leaving?',
    'The course website has been updated with the latest files.',
    'Please take a seat while the instructor sets up the projector.',
    'Good work today, everyone.',
    'I want to thank you for your cooperation and focus.',
    'Please keep the discussion notes in your folder.',
    'The next seminar will be in the computer lab.',
    'Let us conclude with a brief summary of today’s class.',
    'I have a minor correction to the assignment instructions.',
    'The session will continue after a short pause.',
    'Please save the updated document before closing it.',
    'We will start the reading quiz in ten minutes.',
    'Can you email the reference link to the group?',
    'I will be in the classroom after the lecture if anyone needs help.',
    'Please remember to sign in before the workshop begins.',
    'The hallway is crowded, so we will meet in the next room.',
    'Let us finish this discussion and then move on.',
    'The teacher said the deadline has been extended by one day.',
    'Please check that your name is written correctly on the sheet.',
    'I will leave the handouts on the front table.',
    'The audience is encouraged to ask questions at the end.',
    'I will go through the instructions again before the activity starts.',
]


def build_dataset():
    rows = []
    for sentence in IMPORTANT_SENTENCES:
        rows.append({'sentence': sentence, 'actual_label': 1})
    for sentence in NON_IMPORTANT_SENTENCES:
        rows.append({'sentence': sentence, 'actual_label': 0})

    with CSV_PATH.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sentence', 'actual_label'])
        writer.writeheader()
        writer.writerows(rows)

    return rows


def load_dataset():
    if not CSV_PATH.exists():
        return build_dataset()

    rows = []
    with CSV_PATH.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sentence = (row.get('sentence') or '').strip()
            label = (row.get('actual_label') or '').strip()
            if not sentence:
                continue
            rows.append({'sentence': sentence, 'actual_label': int(label)})

    if len(rows) < 100:
        return build_dataset()
    return rows


def compute_classification_metrics(y_true, y_pred):
    labels = [0, 1]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    accuracy = accuracy_score(y_true, y_pred)
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
        'accuracy': float(accuracy),
        'important': important,
        'non_important': non_important,
        'macro': macro,
        'weighted': weighted,
        'confusion_matrix': [[int(cm[0, 0]), int(cm[0, 1])], [int(cm[1, 0]), int(cm[1, 1])]],
        'classification_report': classification_report(y_true, y_pred, labels=[0, 1], target_names=['Non-important', 'Important'], digits=4, zero_division=0),
    }


def train_model():
    rows = load_dataset()
    X = [row['sentence'] for row in rows]
    y = [row['actual_label'] for row in rows]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        lowercase=True,
        min_df=1,
    )
    X_train_vec = vectorizer.fit_transform(X_train)

    model = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42)
    model.fit(X_train_vec, y_train)

    X_test_vec = vectorizer.transform(X_test)
    y_pred = model.predict(X_test_vec)
    metrics = compute_classification_metrics(y_test, y_pred)

    with MODEL_PATH.open('wb') as handle:
        pickle.dump(model, handle)
    with VECTORIZER_PATH.open('wb') as handle:
        pickle.dump(vectorizer, handle)

    metrics['test_samples'] = len(y_test)
    return metrics


def load_saved_metrics():
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        return train_model()

    rows = load_dataset()
    X = [row['sentence'] for row in rows]
    y = [row['actual_label'] for row in rows]

    with MODEL_PATH.open('rb') as handle:
        model = pickle.load(handle)
    with VECTORIZER_PATH.open('rb') as handle:
        vectorizer = pickle.load(handle)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    X_test_vec = vectorizer.transform(X_test)
    y_pred = model.predict(X_test_vec)
    metrics = compute_classification_metrics(y_test, y_pred)
    metrics['test_samples'] = len(y_test)
    return metrics


def print_report(metrics):
    print('\n========================================')
    print('SENTENCE IMPORTANCE EVALUATION')
    print('========================================')
    print(f'Test samples: {metrics["test_samples"]}')
    print('\nImportant Sentences')
    print(f'Precision: {metrics["important"]["precision"] * 100:.2f}%')
    print(f'Recall:    {metrics["important"]["recall"] * 100:.2f}%')
    print(f'F1-Score:  {metrics["important"]["f1"] * 100:.2f}%')
    print('\nNon-Important Sentences')
    print(f'Precision: {metrics["non_important"]["precision"] * 100:.2f}%')
    print(f'Recall:    {metrics["non_important"]["recall"] * 100:.2f}%')
    print(f'F1-Score:  {metrics["non_important"]["f1"] * 100:.2f}%')
    print(f'\nOverall Accuracy: {metrics["accuracy"] * 100:.2f}%')
    print(f'Macro Precision: {metrics["macro"]["precision"] * 100:.2f}%')
    print(f'Macro Recall:    {metrics["macro"]["recall"] * 100:.2f}%')
    print(f'Macro F1:        {metrics["macro"]["f1"] * 100:.2f}%')
    print(f'Weighted Precision: {metrics["weighted"]["precision"] * 100:.2f}%')
    print(f'Weighted Recall:    {metrics["weighted"]["recall"] * 100:.2f}%')
    print(f'Weighted F1:        {metrics["weighted"]["f1"] * 100:.2f}%')
    tn, fp = metrics['confusion_matrix'][0]
    fn, tp = metrics['confusion_matrix'][1]
    print('\nConfusion Matrix:')
    print(f'[[{tn} {fp}]')
    print(f' [{fn} {tp}]]')
    print('\nClassification Report:')
    print(metrics['classification_report'])


def main():
    metrics = train_model()
    print_report(metrics)
    return metrics


if __name__ == '__main__':
    main()

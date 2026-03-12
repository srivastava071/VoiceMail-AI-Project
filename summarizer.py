import re
from collections import Counter
import heapq


def extractive_summary(text, max_sentences=2):

    if not text or len(text.strip()) == 0:
        return "No content available."

    # Clean text
    text = re.sub(r'\s+', ' ', text)

    # Split into sentences
    sentences = re.split(r'(?<=[.!?]) +', text)

    if len(sentences) <= max_sentences:
        return text[:300]

    # Word frequency
    words = re.findall(r'\w+', text.lower())
    freq = Counter(words)

    # Score sentences
    sentence_scores = {}

    for sentence in sentences:
        for word in re.findall(r'\w+', sentence.lower()):
            if word in freq:
                if len(sentence.split(' ')) < 30:
                    sentence_scores[sentence] = sentence_scores.get(sentence, 0) + freq[word]

    # Pick top sentences
    summary_sentences = heapq.nlargest(max_sentences, sentence_scores, key=sentence_scores.get)

    return " ".join(summary_sentences)
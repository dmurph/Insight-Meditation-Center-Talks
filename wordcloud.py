import os
import re
import csv
import math
from collections import Counter, defaultdict
from unidecode import unidecode


def load_stop_words(filepath="stopwords.txt"):
    """Loads stop words from a text file."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        return {line.strip().lower() for line in f}

STOP_WORDS = load_stop_words()

def filter_numeric_strings(string_list):
    """
    Filters a list of strings, removing those that can be parsed as a number.

    Args:
        string_list: A list of strings.

    Returns:
        A new list containing only the strings that cannot be parsed as a number.
    """
    filtered_list = []
    for s in string_list:
        try:
            float(s)  # Attempt to convert to float (handles integers and floats)
        except ValueError:
            # If a ValueError occurs, the string cannot be parsed as a number
            filtered_list.append(s)
    return filtered_list

def preprocess_text(text):
    """Removes markdown, URLs, and other non-word content."""
    # Remove YAML frontmatter
    text = re.sub(r'^---[\s\S]*?---', '', text)
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove footnote definitions like [^1]: ...
    text = re.sub(r'\[\^\d+\]:.*', '', text)
    # Remove speaker urls
    text = re.sub(r'\(https://www.audiodharma.org/speakers/\d+\)', '', text)
    return text

def tokenize(text):
    """Splits text into words, converts to lowercase, and removes punctuation."""
    processed_text = preprocess_text(text)
    words = re.findall(r'\b[\w\'-]+\b', processed_text.lower())
    words = filter_numeric_strings(words)
    
    # Normalize words to their ASCII equivalent
    normalized_words = [unidecode(word) for word in words]
    
    return [word for word in normalized_words if word.lower() not in STOP_WORDS and not word.isdigit()]

def main():
    talks_dir = 'talks'
    output_dir = os.path.join(talks_dir, 'cloud')
    os.makedirs(output_dir, exist_ok=True)

    # Clean up old files
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, f))

    talk_files = [f for f in os.listdir(talks_dir) if f.endswith('.md')]
    num_documents = len(talk_files)

    global_word_counts = Counter()
    talk_word_counts = {}

    print(f"Processing {num_documents} talks...")
    for filename in talk_files:
        filepath = os.path.join(talks_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                words = tokenize(content)
                talk_counts = Counter(words)
                talk_word_counts[filename] = talk_counts
                global_word_counts.update(talk_counts)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # --- TF-IDF and Other Metrics ---
    doc_frequency = Counter()
    for counts in talk_word_counts.values():
        doc_frequency.update(counts.keys())

    idf_scores = {
        word: math.log(num_documents / df)
        for word, df in doc_frequency.items() if df > 0
    }
    
    # --- Global Word Cloud ---
    global_csv_path = os.path.join(output_dir, 'wordcloud.csv')
    print(f"Writing global word cloud to {global_csv_path}...")
    with open(global_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['word', 'global_frequency', 'document_frequency', 'idf_score'])
        for word, freq in global_word_counts.most_common():
            df = doc_frequency.get(word, 0)
            idf = idf_scores.get(word, 0)
            writer.writerow([word, freq, df, f"{idf:.6f}"])

    # --- Per-Talk Keyword Files and Average TF-IDF Calculation ---
    print("Processing individual talks for TF-IDF keywords...")
    all_tfidf_scores = defaultdict(list)
    for filename, counts in talk_word_counts.items():
        output_filename = os.path.splitext(filename)[0] + '.csv'
        output_filepath = os.path.join(output_dir, output_filename)

        total_talk_words = sum(counts.values())
        if total_talk_words == 0:
            continue

        word_data = []
        for word, talk_freq in counts.items():
            tf = talk_freq / total_talk_words
            idf = idf_scores.get(word, 0)
            tfidf_score = tf * idf
            all_tfidf_scores[word].append(tfidf_score)
            word_data.append([word, tfidf_score, talk_freq, global_word_counts.get(word, 0)])

        word_data.sort(key=lambda x: x[1], reverse=True)

        with open(output_filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['word', 'tfidf_score', 'talk_frequency', 'global_frequency'])
            for row in word_data:
                writer.writerow([row[0], f"{row[1]:.6f}", row[2], row[3]])

    # --- Generate Filter Keywords ---
    print("Generating filter keywords with new ranking score...")
    
    # Calculate and normalize average TF-IDF scores
    avg_tfidf_scores = {word: sum(scores) / len(scores) for word, scores in all_tfidf_scores.items()}
    max_avg_tfidf = max(avg_tfidf_scores.values()) if avg_tfidf_scores else 1
    normalized_avg_tfidf = {word: score / max_avg_tfidf for word, score in avg_tfidf_scores.items()}

    total_global_words = sum(global_word_counts.values())

    filter_keywords = []
    for word, global_freq in global_word_counts.items():
        df = doc_frequency.get(word, 0)
        
        global_percentage = global_freq / total_global_words
        global_freq_score = 1 - global_percentage

        df_percentage = df / num_documents
        df_score = 1 - abs(0.5 - df_percentage) * 2

        avg_tfidf_score = normalized_avg_tfidf.get(word, 0)

        combined_score =   (df_score * avg_tfidf_score) ** (1/2)
        
        filter_keywords.append([word, global_percentage, df_percentage, global_freq_score, df_score, avg_tfidf_score, combined_score])

    filter_keywords.sort(key=lambda x: x[6], reverse=True)

    filter_keywords_path = os.path.join(output_dir, 'filter_keywords.csv')
    print(f"Writing filter keywords to {filter_keywords_path}...")
    with open(filter_keywords_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['word', 'global_frequency_percent', 'document_frequency_percent', 'global_freq_score', 'document_freq_score', 'avg_tfidf_score', 'combined_score'])
        for row in filter_keywords:
            writer.writerow([row[0], f"{row[1]:.3f}", f"{row[2]:.3f}", f"{row[3]:.3f}", f"{row[4]:.3f}", f"{row[5]:.3f}", f"{row[6]:.3f}"])

    print("Keyword generation complete.")

if __name__ == '__main__':
    main()
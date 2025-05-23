# -*- coding: utf-8 -*-
"""Sentiment_Analysis_cc.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1j2huGRVX11nehdv1znM-rZ1YrTxcHb34
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import string

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import LSTM, GRU, Embedding, Dropout, Dense, Bidirectional
from tensorflow.keras.models import Sequential
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc

import pickle
import joblib
import re

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

print("🛠️ NLTK resources downloaded successfully!")

train_data = pd.read_csv('/content/twitter_training.csv', names=['number', 'Border', 'label', 'text'])
test_data = pd.read_csv('/content/twitter_validation.csv', names=['number', 'Border', 'label', 'text'])

print("📊 Data Shape:")
print("Training data:", train_data.shape)
print("Testing data:", test_data.shape)

print("\n🔍 First 5 rows of training data:")
display(train_data.head())

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
train_data['label'].value_counts().plot(kind='bar', color=['skyblue', 'salmon'])
plt.title("Original Label Distribution")
plt.xlabel("Sentiment")
plt.ylabel("Count")

plt.subplot(1, 2, 2)
train_data.isna().sum().plot(kind='bar', color='lightgreen')
plt.title("Missing Values Count")
plt.ylabel("Count")

plt.tight_layout()
plt.show()

# Drop unnecessary columns
train_data.drop(['number', 'Border'], axis=1, inplace=True)
test_data.drop(['number', 'Border'], axis=1, inplace=True)

# Handle missing values and duplicates
train_data.dropna(axis=0, inplace=True)
train_data.drop_duplicates(inplace=True)

# Filter only Positive and Negative labels
train_data = train_data[train_data['label'].isin(['Positive', 'Negative'])]
train_data['label'].replace({'Positive': 1, 'Negative': 0}, inplace=True)

# Visualize cleaned label distribution
plt.figure(figsize=(6, 6))
train_data['label'].value_counts().plot.pie(autopct='%1.2f%%', colors=['salmon', 'skyblue'])
plt.title("Cleaned Label Distribution")
plt.ylabel("")
plt.show()

punc = string.punctuation
st_words = stopwords.words('english')

def clean_text(text):
    text = re.sub('@ ?[\w]+', '', text)
    text = re.sub('https?://\S+|www\.\S+', ' ', text)
    text = re.sub('\w*gmail.com\b|\w*yahoo.co.in\b', ' ', text)
    text = re.sub('<.*>', '', text)
    text = re.sub('[\W]', ' ', text)
    text = re.sub('[0-9]', ' ', text)
    text = re.sub('\s+[a-zA-Z]\s+', ' ', text)
    text = re.sub('\s+', ' ', text)
    text = ''.join([word.lower() for word in text if word not in punc])
    text = ' '.join([word for word in text.split() if word not in st_words])
    return text

train_data['cleaned_text'] = train_data['text'].apply(clean_text)

# Visualize text length distribution
text_lengths = train_data['cleaned_text'].apply(lambda x: len(x.split()))
plt.figure(figsize=(10, 5))
sns.histplot(text_lengths, bins=30, kde=True, color='teal')
plt.title("Distribution of Text Lengths (After Cleaning)")
plt.xlabel("Number of Words")
plt.ylabel("Frequency")
plt.show()

embedding_dim = 128
oov_tok = '<OOV>'
max_length = 150

X = train_data['cleaned_text']
y = train_data['label']

tokenizer = Tokenizer(oov_token=oov_tok)
tokenizer.fit_on_texts(X)
word_indx = tokenizer.word_index
vocab_size = len(word_indx)

sequence = tokenizer.texts_to_sequences(X)
sequence_padded = pad_sequences(sequence, padding='post', maxlen=max_length)

# Visualize word frequency
word_counts = pd.Series(tokenizer.word_counts).sort_values(ascending=False)
plt.figure(figsize=(12, 6))
word_counts[:20].plot(kind='bar', color='purple')
plt.title("Top 20 Most Frequent Words")
plt.xlabel("Words")
plt.ylabel("Frequency")
plt.xticks(rotation=45)
plt.show()

print(f"\n🔠 Vocabulary size: {vocab_size}")
print(f"✂ Max sequence length: {max_length}")

X_train, X_val, y_train, y_val = train_test_split(sequence_padded, y, test_size=0.2, random_state=42)

print("📊 Train-Test Split:")
print(f"Training samples: {X_train.shape[0]}")
print(f"Validation samples: {X_val.shape[0]}")

model = Sequential([
    # Updated Embedding layer without input_length
    Embedding(input_dim=vocab_size + 1, output_dim=embedding_dim),

    # First bidirectional LSTM with proper return_sequences
    Bidirectional(LSTM(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2)),

    # Bidirectional GRU
    Bidirectional(GRU(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2)),

    # Final GRU layer
    Bidirectional(GRU(32, dropout=0.2, recurrent_dropout=0.2)),

    Dense(32, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')
])

# Explicitly build the model with input shape
model.build(input_shape=(None, max_length))

model.compile(optimizer='adam',
              loss='binary_crossentropy',
              metrics=['accuracy',
                      tf.keras.metrics.Precision(name='precision'),
                      tf.keras.metrics.Recall(name='recall')])

# Display model summary
model.summary()

early_stopping = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)

history = model.fit(X_train, y_train,
                    batch_size=64,
                    epochs=10,
                    validation_data=(X_val, y_val),
                    callbacks=[early_stopping])

# Save model and tokenizer
model.save('twitter_sentiment_hybrid_model.keras')
joblib.dump(tokenizer, "hybrid_tokenizer.pkl")

print("\n✅ Model training complete and saved!")

plt.figure(figsize=(15, 5))

# Plot accuracy
plt.subplot(1, 3, 1)
plt.plot(history.history['accuracy'], label='Train')
plt.plot(history.history['val_accuracy'], label='Validation')
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend()

# Plot loss
plt.subplot(1, 3, 2)
plt.plot(history.history['loss'], label='Train')
plt.plot(history.history['val_loss'], label='Validation')
plt.title('Model Loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend()

# Plot precision-recall
plt.subplot(1, 3, 3)
plt.plot(history.history['precision'], label='Train Precision')
plt.plot(history.history['recall'], label='Train Recall')
plt.plot(history.history['val_precision'], label='Val Precision')
plt.plot(history.history['val_recall'], label='Val Recall')
plt.title('Precision & Recall')
plt.ylabel('Score')
plt.xlabel('Epoch')
plt.legend()

plt.tight_layout()
plt.show()

from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

y_pred = model.predict(X_val)
y_pred_classes = (y_pred > 0.5).astype(int)


conf_matrix = confusion_matrix(y_val, y_pred_classes)

# Plot confusion matrix
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap='Blues', xticklabels=np.unique(y), yticklabels=np.unique(y))
plt.title('Confusion Matrix')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.show()

y_pred_classes = np.array(y_pred_classes)

# Convert class labels to strings
target_names = [str(label) for label in np.unique(y)]

# Generate and print classification report
print('Classification Report:')
print(classification_report(y_val, y_pred_classes, target_names=target_names))

report = classification_report(y_val, y_pred_classes, target_names=np.unique(y), output_dict=True)
report_df = pd.DataFrame(report).transpose()

plt.figure(figsize=(8, 6))
sns.heatmap(report_df.iloc[:-1, :-1], annot=True, cmap='Blues', fmt='.2f', cbar=False)
plt.xlabel('Metrics')
plt.ylabel('Class')
plt.title('Classification Report' )
plt.show()
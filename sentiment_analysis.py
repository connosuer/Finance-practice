# -*- coding: utf-8 -*-
"""sentimentAnalysis-prac.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1upIjzTWE2gynl-hWUBPFPLcA0Iq_ldFu

Data Collection
"""

import yfinance as yf
import pandas as pd
import requests
from dotenv import load_dotenv
import os

#downloading historical data
stock_data = yf.download("AAPL", start="2022-01-01", end="2023-01-01")

# Load environment variables
load_dotenv()

#fetching api key 
api_key = os.getenv('NEWS_API_KEY')

# Check if the API key is available
if not api_key:
    raise ValueError("NEWS_API_KEY not found in environment variables")

#fetching financial news
url = f"https://newsapi.org/v2/everything?q=apple&apiKey={api_key}"
response = requests.get(url)
news_data = response.json()


#extracting headlines and publication dates
headlines = [(article['title'], article['publishedAt']) for article in news_data['articles']]

"""Sentiment Analysis"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from datetime import datetime

analyzer = SentimentIntensityAnalyzer()

#analyzing sentiment of headlines
sentiment_scores = []

for headline, date in headlines:
  score = analyzer.polarity_scores(headline)['compound']
  sentiment_scores.append({'Date': date.split('T')[0], 'Sentiment': score})

#converting to dataframe and aggregate sentiment score by date
sentiment_df = pd.DataFrame(sentiment_scores)
sentiment_df['Date'] = pd.to_datetime(sentiment_df['Date'])
sentiment_df = sentiment_df.groupby('Date').mean().reset_index()

#merging sentiment with stock data
stock_data.reset_index(inplace=True)
combined_data = pd.merge(stock_data, sentiment_df, left_on='Date', right_on='Date', how = 'inner')

"""Feature Engineering"""

#moving averages
combined_data['MA_10'] = combined_data['Close'].rolling(window=10).mean()
combined_data['Sentiment_lag'] = combined_data['Sentiment'].shift(1)

#drop missing val
combined_data.dropna(inplace=True)

"""Model Development"""

import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import matplotlib.pyplot as plt

# Debug: Check if combined_data is empty
print("Is combined_data empty?", combined_data.empty)
print("Shape of combined_data:", combined_data.shape)
print("Columns in combined_data:", combined_data.columns)

# If combined_data is empty, let's create some sample data for demonstration
if combined_data.empty:
    print("Creating sample data for demonstration")
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    combined_data = pd.DataFrame({
        'Date': dates,
        'Close': np.random.randint(100, 200, size=len(dates)),
        'Sentiment': np.random.rand(len(dates))
    })
    combined_data.set_index('Date', inplace=True)

# Calculate MA_10
combined_data['MA_10'] = combined_data['Close'].rolling(window=10).mean()

# Create 'Sentiment_Lag' column
combined_data['Sentiment_Lag'] = combined_data['Sentiment'].shift(1)

# Handle NaN values
combined_data.fillna(method='bfill', inplace=True)

# Debug: Check data after preprocessing
print("\nData after preprocessing:")
print(combined_data[['Close', 'MA_10', 'Sentiment_Lag']].head())
print("Shape of data:", combined_data.shape)

# Prepare data for LSTM
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(combined_data[['Close', 'MA_10', 'Sentiment_Lag']])

# Debug: Ensure scaled_data has values
print("Scaled Data Shape:", scaled_data.shape)

# Create sequences for LSTM model
def create_sequences(data, seq_length):
    X = []
    y = []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length][0])  # Predicting the next 'Close' price
    return np.array(X), np.array(y)

seq_length = 10
X, y = create_sequences(scaled_data, seq_length)

# Split into training and testing data
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# Build LSTM model
model = tf.keras.Sequential([
    tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
    tf.keras.layers.LSTM(50),
    tf.keras.layers.Dense(1)
])

model.compile(optimizer='adam', loss='mean_squared_error')
model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=0)

# Make predictions
predictions = model.predict(X_test)

# Inverse scaling of the predictions
predictions = scaler.inverse_transform(np.hstack((predictions, np.zeros((predictions.shape[0], 2)))))[:, 0]

# Inverse scaling of actual values
y_test_inverse = scaler.inverse_transform(np.hstack((y_test.reshape(-1, 1), np.zeros((y_test.shape[0], 2)))))[:, 0]

# Plot the results
plt.figure(figsize=(14, 7))
plt.plot(y_test_inverse, color='blue', label='Actual Prices')
plt.plot(predictions, color='red', label='Predicted Prices')
plt.title('Stock Price Prediction with LSTM')
plt.xlabel('Time')
plt.ylabel('Price')
plt.legend()
plt.show()

"""Streamlit App"""

import streamlit as st

# Assume these are imported from your previous script
# from your_preprocessing_script import combined_data, sentiment_df, model, scaler

st.title('AI-Driven Stock Market Predictions with Sentiment Analysis')

# Check if data is available
if 'combined_data' in locals() and not combined_data.empty:
    st.subheader('Historical Stock Prices')

    # Check if 'Date' is already the index
    if 'Date' in combined_data.index.names:
        st.line_chart(combined_data['Close'])
    elif 'Date' in combined_data.columns:
        st.line_chart(combined_data.set_index('Date')['Close'])
    else:
        st.write("'Date' column not found. Displaying data without date index.")
        st.line_chart(combined_data['Close'])

    # Displaying predictions vs actual price
    st.subheader('Actual Prices vs Predicted Prices')
    if 'y_test' in locals() and 'predictions' in locals():
        actual_prices = scaler.inverse_transform(np.hstack((y_test.reshape(-1, 1), np.zeros((y_test.shape[0], 2)))))[:, 0]
        comparison_df = pd.DataFrame({'Actual': actual_prices, 'Predicted': predictions})
        st.line_chart(comparison_df)
    else:
        st.write("Prediction data not available. Please run the model first.")

    # Display sentiment analysis
    if 'sentiment_df' in locals() and not sentiment_df.empty:
        st.subheader('Sentiment Analysis Over Time')
        if 'Date' in sentiment_df.index.names:
            st.line_chart(sentiment_df['Sentiment'])
        elif 'Date' in sentiment_df.columns:
            st.line_chart(sentiment_df.set_index('Date')['Sentiment'])
        else:
            st.write("'Date' column not found in sentiment data. Displaying sentiment without date index.")
            st.line_chart(sentiment_df['Sentiment'])
    else:
        st.write("Sentiment data not available.")
else:
    st.write("No data available. Please load or generate data first.")

# Add explanations
st.sidebar.title("About This App")
st.sidebar.info("This app shows historical stock prices, compares predicted prices with actual prices, and displays sentiment analysis over time. The predictions are made using an AI model trained on historical data and sentiment analysis.")

# Debug information
st.sidebar.title("Debug Information")
if 'combined_data' in locals():
    st.sidebar.write("combined_data columns:", combined_data.columns)
    st.sidebar.write("combined_data index:", combined_data.index)
if 'sentiment_df' in locals():
    st.sidebar.write("sentiment_df columns:", sentiment_df.columns)
    st.sidebar.write("sentiment_df index:", sentiment_df.index)

'''
# Example Stock Price Prediction: System Overview
# Company: TechCorp

## Process Flow

```mermaid
graph TD
    A[Collect Data] --> B[Analyze Sentiment]
    B --> C[Engineer Features]
    C --> D[Train Model]
    D --> E[Make Prediction]
    E --> F[Visualize Results]
```

## Detailed Steps

### 1. Data Collection
- The system downloads TechCorp's stock prices for the past year.
- It also fetches recent news headlines about TechCorp.

### 2. Sentiment Analysis
- The system analyzes the sentiment of these headlines.
- For example, a headline "TechCorp Launches Revolutionary Product" would be analyzed as positive sentiment.

### 3. Feature Engineering
- The system calculates the 10-day moving average of TechCorp's stock price.
- It combines this with the daily sentiment scores.

### 4. Model Training
- The AI model (LSTM) is trained on this historical data.
- It learns patterns between past stock prices, moving averages, sentiment, and subsequent price movements.

### 5. Prediction
- To predict tomorrow's price, the model looks at:
  - Recent stock prices
  - The current 10-day moving average
  - Today's news sentiment
- Based on the patterns it learned, it makes a prediction for tomorrow's price.

### 6. Visualization
- The prediction is displayed on a graph, showing how it compares to recent actual prices.
- The Streamlit app allows users to interact with this data, viewing historical trends and predictions.

## Use Case Example

Imagine you're a financial analyst interested in TechCorp. You could use this tool to:
- See how TechCorp's stock has performed historically
- Understand how news sentiment has correlated with stock price movements
- Get an AI-generated prediction for near-future price movements

For instance, if there's very positive news about TechCorp today, and the stock price has been trending upward, the model might predict a price increase for tomorrow.

## Key Points to Emphasize

1. It combines numerical data (stock prices) with textual data (news sentiment) for a more comprehensive analysis.
2. It's not a crystal ball - it's making educated guesses based on historical patterns.
3. It's meant for analysis and insight, not as a sole basis for investment decisions.

'''
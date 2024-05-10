from gtts import gTTS
#import os
import streamlit as st
import requests
from transformers import pipeline
import time
from bs4 import BeautifulSoup

URL = "https://globalnews.ca/"
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
MAX_ARTICLES = 5

@st.cache_data(ttl=3600, show_spinner=False)
def get_stories():
    percentComplete = 0
    progressBar = st.progress(percentComplete, text="Finding stories...")

    homepage = requests.get(URL)
    homepageContent = BeautifulSoup(homepage.content, "html.parser")

    stories = []
    pages = []
    headlines = []
    thumbnails = []

    results = homepageContent.find(id="home-topStories").find_all("a", class_="c-posts__inner")
    n_articles = min(len(results), MAX_ARTICLES)
    results = results[:n_articles]

    progressIncrement = 1/(1 + n_articles)

    for link in results:
        pages.append(link['href'])
        headlines.append(link.find("span")['title'])
        try:
            thumbnails.append(link.find("img")['data-src'])
        except:
            thumbnails.append(link.find("img")['src'])

    for i, page in enumerate(pages):
        article = requests.get(page)
        soup = BeautifulSoup(article.content, "html.parser")

        percentComplete += progressIncrement
        progressBar.progress(percentComplete, text=f"Summarizing article {i+1}/{n_articles}...")

        try:
            results = soup.find("article", class_="l-article__text js-story-text") 
        except:
            try: 
                results = soup.find("article", class_="l-longform-article__text js-story-text")
            except:
                results = None
        
        if results is not None:
            paragraphs = " ".join([p.text for p in results.find_all("p")])
            summary = get_summary(paragraphs)
            speech = gTTS(text=summary, lang='en', slow=False)
            fname = f"summary{i}.mp3"
            speech.save(fname)
            stories.append({"hl": headlines[i], "summary": summary, "file": fname, "thumb": thumbnails[i]})

    progressBar.progress(0.99, text=f"Done!")
    time.sleep(1)
    progressBar.empty()
    return stories

def get_summary(text, max_attempts=3):
    API_TOKEN = st.secrets["API_TOKEN"]
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    attempts = 0

    while attempts < max_attempts:
        try:
            response = requests.post(API_URL, headers=headers, json={"inputs": text})
            return response.json()[0]['summary_text']
        except:
            attempts += 1

    return "API temporarily unavailable"
   

if __name__ == "__main__":
    st.set_page_config(page_title="News Summarizer", page_icon="📰")
    st.title('News Summary')

    c = st.container()

    stories = get_stories()

    for article in stories:   
        c1, c2, c3 = c.columns(3)
        c1.image(article['thumb'])
        c1.write(f"**{article['hl']}**")
        c2.write(article['summary'])
        c3.audio(article['file'], format="audio/mp3")

    st.markdown("Source: [*Globalnews.ca*](https://globalnews.ca/)")
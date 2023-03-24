#Import Libraries

import streamlit as st
import datetime as dt
from gtts import gTTS
import speech_recognition as sr 
from google_trans_new import google_translator
from PIL import Image

trans = google_translator()
input_text = ""

#image for top of the screen

image = Image.open('translate.png')
st.image(image)

#date display

now = dt.date.today()

#Text Display

st.write(f"Today is {now}")
st.write(f"Translate your thoughts.")

input_text = st.text_input('Enter whatever')

#Translates user input and creates text to speech audio

if st.button('Translate'):
    result = trans.translate(input_text, lang_tgt = 'ja')
    st.success(result)
    speech = gTTS(text = result, lang = 'ja', slow = False)
    speech.save('user_trans.mp3')
    audio_file = open('user_trans.mp3', 'rb')
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format='audio/ogg',start_time=0)


path = st.file_uploader("Or upload audio to translate")

#Translates user audio and creates text to speech audio

if st.button('Translate audio'):

    # Initialize recognizer class (for recognizing the speech)
    r = sr.Recognizer()

    # Reading Audio file as source
    # listening the audio file and store in audio_text variable

    with sr.AudioFile(path) as source:
        
        audio_text = r.listen(source)
        
    # recoginize_() method will throw a request error if the API is unreachable, hence using exception handling
        try:
            
            # using google speech recognition
            text = r.recognize_google(audio_text)
            print('Converting audio transcripts into text ...')
            input_text = st.write(text)
            result = trans.translate(text, lang_tgt = 'ja')
            st.success(result)
            speech = gTTS(text = result, lang = 'ja', slow = False)
            speech.save('trans.mp3')
            audio_file = open('trans.mp3', 'rb')
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format='audio/ogg',start_time=0)
        
        except:
            st.write('Sorry.. run again...')

from email.policy import default
import os
from decouple import config
import openai
import streamlit as st

from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

import time
import glob
from gtts import gTTS
from googletrans import Translator

openai.api_key = st.secrets["OPENAI_KEY"]

st.set_page_config(
    page_icon='🏢',
    page_title='Your Virtual Project Assistant',
    menu_items={
        'Get Help': 'https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g',
        'Report a bug': "https://github.com/anhn/streamlit-example/issues/new",
        'About': "This chatbot is tailored by Anh Nguyen-Duc for trying a virtual project assistant "
    }
)
st.title("🏢 Hannah Consulatation's space")

st.sidebar.title("🏢 The Virtual Assistant Chatbot")
st.sidebar.markdown("""

**Feedback/Questions**: 
[join our slack workspace](https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g)

Like 🏢 **The Office Chatbot** and want to say thanks? [:coffee: buy me a coffee](https://www.buymeacoffee.com/anhnd85Q)
""")
cathy_line =''
jim_line = 'You are a helpful assistant!'

stt_button = Button(label="Speak", width=100)
stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if ( value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
    """))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0)
if result:
    if "GET_TEXT" in result:
        st.write(":pig: You: " + result.get("GET_TEXT"))
        jim_line = result.get("GET_TEXT")
        
def get_response(jim_line):
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You try your best to answer questions"},
            {"role": "user", "content": jim_line},
        ],
        max_tokens = 1024,
        temperature = 0.5,
    )
    response = completions.choices[0]["message"]["content"].strip()
    return response 

# Storing the chat
if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

#def get_text():
    #input_text = st.text_area("Can not speak?","Say something to Hannah:", height=10, key='option')
    #return input_text

#if 'past' not in st.session_state:
#    st.session_state['past'] = []

john_line = st.text_area("Can not speak?",value="write your prompt here", height=5, key='input')
if john_line:
    cathy_line = get_response(john_line)
    jim_line = ''

if jim_line != '':
#jim_line = get_text()
    cathy_line = get_response(jim_line)
#st.session_state.past.append(jim_line)
#cathy_line =  get_response(st.session_state['past'][-1] + jim_line)
st.markdown(""" :mailbox: Hannah:     """ + cathy_line)

try:
    os.mkdir("temp")
except:
    pass

translator = Translator()

#in_lang = st.selectbox(
#    "Select your input language",
#    ("English", "Vietnamese"),
#)
#if in_lang == "English":
#    input_language = "en"
#elif in_lang == "Vietnamese":
#    input_language = "vn"

#out_lang = st.selectbox(
#    "Select your output language",
#    ("English", "Vietnamese"),
#)
#if out_lang == "English":
#    output_language = "en"
#elif out_lang == "Vietnamese":
#    output_language = "vn"

input_lang == "vn"
output_lang == "vn"
tld = "com"

def text_to_speech(input_language, output_language, text, tld):
    translation = translator.translate(text, src=input_language, dest=output_language)
    trans_text = translation.text
    tts = gTTS(trans_text, lang=output_language, tld=tld, slow=False)
    try:
        my_file_name = text[0:20]
    except:
        my_file_name = "audio"
    tts.save(f"temp/{my_file_name}.mp3")
    return my_file_name, trans_text


#display_output_text = st.checkbox("Display output text")

if st.button("convert"):
    result, output_text = text_to_speech(input_language, output_language, cathy_line, tld)
    audio_file = open(f"temp/{result}.mp3", "rb")
    audio_bytes = audio_file.read()
    st.markdown(f"## Your audio:")
    st.audio(audio_bytes, format="audio/mp3", start_time=0)

#    if display_output_text:
#        st.markdown(f"## Output text:")
#        st.write(f" {output_text}")

def remove_files(n):
    mp3_files = glob.glob("temp/*mp3")
    if len(mp3_files) != 0:
        now = time.time()
        n_days = n * 86400
        for f in mp3_files:
            if os.stat(f).st_mtime < now - n_days:
                os.remove(f)
                print("Deleted ", f)

remove_files(7)
#if jim_line:
#    output = get_response(jim_line)
#    # store the output 
#    st.session_state.past.append(jim_line)
#    st.session_state.generated.append(output)

#if st.session_state['generated']:
#    
#    for i in range(len(st.session_state['generated'])-1, -1, -1):
#        message(st.session_state["generated"][i], key=str(i))
#        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
           
#with st.expander("Not sure what to say to Hannah?"):
#    st.markdown(""" 
#Try some of these:
#```
#1. What do you think are the most important qualities for a successful entrepreneur?
#2. What are the biggest challenges that entrepreneurs face in the early stages of building a business, and how can they overcome them?
#```
#    """)

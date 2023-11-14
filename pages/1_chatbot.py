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
from PIL import Image

openai.api_key = st.secrets["OPENAI_KEY"]

#st.set_page_config(
#    page_icon='🏢',
#    page_title='Phat Giao Online',
#    menu_items={
#        'Get Help': 'https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g',
#        'Report a bug': "https://github.com/anhn/streamlit-example/issues/new",
#        'About': "This chatbot is developed by CMAT JSC for supporting dissemination of Budhism "
#    }
#)
#st.title("🏢 Trợ lý sáng đạo trong đời")
image = Image.open("law1.jpg")
st.image(image, width=800)

if not os.path.exists('temp'):
    os.makedirs('temp')
#st.sidebar.title("🏢 Trợ lý sáng đạo trong đời")
#st.sidebar.markdown("""
#
#**Feedback/Questions**: 
#[join our slack workspace](https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g)
#
#Like 🏢 **The Office Chatbot** and want to say thanks? [:coffee: buy me a coffee](https://www.buymeacoffee.com/anhnd85Q)
#""")
cathy_line =''
john_line = ''
#jim_line = 'bạn đóng vai một nhà sư với kiến thức về phật giáo uyên bác. Bạn sẽ trả lời các câu hỏi từ người dùng một cách chi tiết và dễ hiểu nhất có thể. Bạn sẽ xưng là thầy, và gọi người dùng là con.'
jim_line = 'act as a software project manager who will teach a software project management class. You will answer questions from students in an academic and detailed manner. Give definitions and illustrative examples when it is possible.'
#stt_button = Button(label="Nói", width=100)
#stt_button.js_on_event("button_click", CustomJS(code="""
#    var recognition = new webkitSpeechRecognition();
#    recognition.continuous = true;
#    recognition.interimResults = true;
#
#    recognition.onresult = function (e) {
#        var value = "";
#        for (var i = e.resultIndex; i < e.results.length; ++i) {
#            if (e.results[i].isFinal) {
#                value += e.results[i][0].transcript;
#            }
#        }
#        if ( value != "") {
#            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
#        }
#    }
#    recognition.start();
#    """))

#result = streamlit_bokeh_events(
#    stt_button,
#    events="GET_TEXT",
#    key="listen",
#    refresh_on_update=False,
#    override_height=75,
#    debounce_time=0)
#if result:
#    if "GET_TEXT" in result:
#        st.write(":pig: Phật tử: " + result.get("GET_TEXT"))
#        jim_line = result.get("GET_TEXT")

def get_response(jim_line):
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "act as a software project manager who will teach a software project management class. You will answer questions from students in an academic and detailed manner. Give definitions and illustrative examples when it is possible."},
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

#with st.expander("Viết câu hỏi tại đây nếu bạn không dùng micro"):         
john_line = st.text_area("Viết câu hỏi tại đây",value='', height=5, key='input')
if john_line:
    st.session_state.generated = john_line
else:
    st.session_state.generated = 'something'
##    cathy_line = get_response(john_line)
##    jim_line = ''

##if jim_line != '':
#jim_line = get_text()
##    cathy_line = get_response(jim_line)
#st.session_state.past.append(jim_line)

##if cathy_line != '':
##    st.session_state.generated = cathy_line
    
##st.markdown(""" :mailbox: Lecturer:     """ + cathy_line)

#try:
#    os.mkdir("temp")
#except:
#    pass

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

input_language = "no"
#output_language = "vi"
output_language = "no"
tld = "com"

def list_mp3_files(folder_path):
    # List all files in the specified directory
    all_files = os.listdir(folder_path)
    # Filter out files that are not MP3
    mp3_files = [file for file in all_files]
    return mp3_files
    
def text_to_speech(input_language, output_language, text, tld):
    translation = translator.translate(text, src=input_language, dest=output_language)
    trans_text = translation.text
    tts = gTTS(trans_text, lang=output_language, tld=tld, slow=False)
    tts = gTTS(text, lang=output_language, tld=tld, slow=False)
    try:
        my_file_name = text[0:20]
    except:
        my_file_name = "audio"
    tts.save(f"temp/{my_file_name}.mp3")
    return my_file_name, trans_text
    
display_output_text = st.checkbox("Display output text")
# Streamlit user interface to input the folder path

mp3_files = list_mp3_files(os.getcwd())
if mp3_files:
    st.write("MP3 Files in the folder:")
    for file in mp3_files:
        st.write(file)
else:
    st.write("No MP3 files found in the specified folder.")

if john_line!= '':
    st.session_state.generated = john_line
    result, output_text = text_to_speech(input_language, output_language, st.session_state.generated, tld)
    audio_file = open(f"temp/{result}.mp3", "rb")
    audio_bytes = audio_file.read()
    st.markdown(f"## Speech:")
    st.audio(audio_bytes, format="audio/mp3", start_time=0)

#if st.button("convert"):
#    result, output_text = text_to_speech(input_language, output_language, st.session_state.generated, tld)
#    audio_file = open(f"temp/{result}.mp3", "rb")
#    audio_bytes = audio_file.read()
#    st.markdown(f"## Your audio:")
#    st.audio(audio_bytes, format="audio/mp3", start_time=0)
#    if display_output_text:
#        st.markdown(f"## Output text:")
#        st.write(f" {output_text}")

#def remove_files(n):
#    mp3_files = glob.glob("temp/*mp3")
#    if len(mp3_files) != 0:
#        now = time.time()
#        n_days = n * 86400
#        for f in mp3_files:
#            if os.stat(f).st_mtime < now - n_days:
#                os.remove(f)
#                print("Deleted ", f)

#remove_files(7)
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

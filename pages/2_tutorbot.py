from email.policy import default
import os
from decouple import config
import openai
import streamlit as st
from streamlit_chat import message

openai.api_key = st.secrets["OPENAI_KEY"]

st.set_page_config(
    page_icon='🏢',
    page_title='Your virtual assisant in learning Javascript',
    menu_items={
        'Get Help': 'https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g',
        'Report a bug': "https://github.com/anhn/streamlit-example/issues/new",
        'About': "This chatbot is tailored by Anh Nguyen-Duc for trying a virtual project assistant "
    }
)
st.title("🏢 Virtual assistant in learning Javascript")

st.sidebar.title("🏢 Your virtual assisant in learning Javascript")
cathy_line =''
jim_line = ''
def get_response(jim_line):
#    completions = openai.ChatCompletion.create(
#        model="gpt-3.5-turbo",
#        messages=[
#            {"role": "system", "content": "You are a Javascript teacher for 2nd year students"},
#            {"role": "user", "content": jim_line},
#        ],
#        max_tokens = 1024,
#        temperature = 0.5,
#    )
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=jim_line,
      temperature=0.9,
      max_tokens=150,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0.6,
      stop=[" Human:", " AI:"]
    )
    output = response.choices[0].text
    return output 

# Storing the chat
if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

def get_text():
    input_text = st.text_area("Write you command here","Say something to your tutor:", height=10, key='option')
    return input_text

jim_line = get_text()

if jim_line:
    cathy_line = get_response(jim_line)
    st.session_state.past.append(jim_line)
    st.session_state.generated.append(cathy_line)

if st.session_state['generated']:  
    for i in range(len(st.session_state['generated'])-1, -1, -1):
        st.markdown(""" :mailbox: AI:     """ + st.session_state["generated"][i])
        st.markdown(""" :mailbox: Human:     """ + st.session_state['past'][i])
           
#with st.expander("Not sure what to say to Hannah?"):
#    st.markdown(""" 
#Try some of these:
#```
#1. What do you think are the most important qualities for a successful entrepreneur?
#2. What are the biggest challenges that entrepreneurs face in the early stages of building a business, and how can they overcome them?
#```
#    """)

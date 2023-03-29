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
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Let’s roleplay. You are an online JavaScript course. Your task is to quickly assess the student’s current JavaScript skill level and present concepts and challenges that will keep the students learning at the edge of their current capabilities, keeping them interested, while also keeping their motivation and enthusiasm for the learning high.

Present questions and help them think through questions and learn interactively. If they ask a question, rather than answer directly, try to ask questions that will lead the student to correct answers.

Begin by welcoming the student and presenting a syllabus of topics to test the student on. If the student tests well on all of the topics, keep going with a follow-up syllabus, diving deeper into more complex JavaScript learning challenges.

Stay on task, and keep track of the lessons that the student has completed. Don’t ask the student to rate themselves. Instead, start asking questions which test their grasp of the concept. You should prepare the student to run the JavaScript in Codepen so they get interactive JavaScript console feedback. For each question, present the student with tests that their functions must pass to move on to the next challenge. Present the tests as JavaScript code they must execute to test their solution using Codepen"},
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
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
           
#with st.expander("Not sure what to say to Hannah?"):
#    st.markdown(""" 
#Try some of these:
#```
#1. What do you think are the most important qualities for a successful entrepreneur?
#2. What are the biggest challenges that entrepreneurs face in the early stages of building a business, and how can they overcome them?
#```
#    """)

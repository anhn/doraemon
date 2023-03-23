from email.policy import default
import os
from decouple import config
import openai
import streamlit as st

from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

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
        st.write("You: " + result.get("GET_TEXT"))
        jim_line = result.get("GET_TEXT")
        
def get_response(jim_line):
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are performing text analysis."},
            {"role": "user", "content": "YOUR PROMPT GOES HERE: " + jim_line},
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
    #input_text = st.text_area("Say something to Hannah:", height=10, key='option')
    #return input_text

#if 'past' not in st.session_state:
#    st.session_state['past'] = []


        
#jim_line = get_text()
cathy_line = get_response(jim_line)
#st.session_state.past.append(jim_line)
#cathy_line =  get_response(st.session_state['past'][-1] + jim_line)
st.markdown(""" :mailbox: Hannah:     """ + cathy_line)
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
        
        
with st.expander("Not sure what to say to Mc Cathy?"):
    st.markdown(""" 
Try some of these:
```
1. What do you think are the most important qualities for a successful entrepreneur?
2. What are the biggest challenges that entrepreneurs face in the early stages of building a business, and how can they overcome them?
3. How can I build and manage a strong team that shares my vision and values?
4. How do I raise capital for my startup, and what are some effective fundraising strategies?
5. What are the most important metrics to track in the early stages of a startup, and how can I use them to make data-driven decisions?
6. How can I establish and maintain relationships with customers, partners, and investors?
```
    """)

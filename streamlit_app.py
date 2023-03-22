from email.policy import default
import os
from decouple import config
import openai
import streamlit as st

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
st.title("🏢 Mc Cathy Consulatation's space")

st.sidebar.title("🏢 The Virtual Assistant Chatbot")
st.sidebar.markdown("""

**Feedback/Questions**: 
[join our slack workspace](https://join.slack.com/t/officechatbot/shared_invite/zt-14rlr8chh-C~rwJN~~KUAX~DOkvcno1g)

Like 🏢 **The Office Chatbot** and want to say thanks? [:coffee: buy me a coffee](https://www.buymeacoffee.com/anhnd85Q)
""")


jim_line = st.text_input("Say something to Mc Cathy:", value='I am having a problem with my project...')

def get_response(jim_line):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=jim_line,
        max_tokens = 1024,
        temperature=0.5,
    )
    
    response = completions.choices[0].text
    return response 

# Storing the chat
if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

if jim_line:
    @st.cache() # caching just so it's cheaper
    output = generate_response(jim_line)
    # store the output 
    st.session_state.past.append(jim_line)
    st.session_state.generated.append(output)

if st.session_state['generated']:
    
    for i in range(len(st.session_state['generated'])-1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
        
        
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

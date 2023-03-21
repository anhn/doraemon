import openai 
import streamlit as st

# pip install streamlit-chat  
from streamlit_chat import message

openai.api_key =  "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"

st.set_page_config(
    page_title="Ex-stream-ly Cool App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About me': 'https://www.usn.no/english/about/contact-us/employees/anh-nguyen-duc',
        'Service': "# This is the very first version of your Startup Virtual Assistant"
    }
)

def generate_response(prompt):
    completions = openai.Completion.create(
        engine = "text-davinci-003",
        prompt = prompt,
        max_tokens = 1024,
        n = 1,
        stop = None,
        temperature=0.5,
    )
    message = completions.choices[0].text
    return message 
    
#Creating the chatbot interface
st.title("Your virtual assistant")

col1, col2= st.columns((1,3))
col1.subheader('Software Project Management')
col2.subheader('Your project assistant')
with col1:
    st.image('pmmethod.png')

with col2:
    # Storing the chat
    if 'generated' not in st.session_state:
        st.session_state['generated'] = []

    if 'past' not in st.session_state:
        st.session_state['past'] = []

    # We will get the user's input by calling the get_text function
    def get_text():
        input_text = st.text_input("You: ","What is meaning of a human life?", key="input")
        return input_text

    user_input = get_text()

    if user_input:
        output = generate_response(user_input)
        # store the output 
        st.session_state.past.append(user_input)
        st.session_state.generated.append(output)

    if st.session_state['generated']:
        
        for i in range(len(st.session_state['generated'])-1, -1, -1):
            message(st.session_state["generated"][i], key=str(i))
            message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')

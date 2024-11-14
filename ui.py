import streamlit as st
import requests
 
# Set the title of the Streamlit app
st.title("Lemmatize Your Sentence")
 
# Input box to get sentence from the user
sentence_input = st.text_input("Enter a sentence:", "")
 
# If the user has entered a sentence
if sentence_input:
    # Azure Function endpoint (replace with your actual function URL)
    url = "https://beyondhumanlemmapi.azurewebsites.net/api/confluence_gpt"
 
    # Send the sentence as a query parameter to the Azure Function
    try:
        response = requests.get(url, params={"sentence": sentence_input})
 
        # Print raw response content for debugging
        st.write("Response raw text: ", response.text)
        st.write("Statsu code: ", response.status_code)
 
        # Check if the response status code is OK (200)
        if response.status_code == 200:
            # Attempt to parse the JSON response
            try:
                st.write("I'm here")
                data = response.json()
                st.write("I'm here2: ",data)
                lemmatized_words = data.get('root_words', [])
                st.write(f"Lemmatized words: {lemmatized_words}")
            except ValueError as e:
                st.error(f"Error parsing JSON response: {e}")
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

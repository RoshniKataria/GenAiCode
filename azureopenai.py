import logging
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
import azure.functions as func
import json
import pymongo
import uuid
from pymongo import MongoClient
from azure.ai.openai import OpenAIClient
from azure.core.credentials import AzureKeyCredential
 
# Download necessary NLTK datasets if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
 
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
 
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
 
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
 
# Initialize lemmatizer, stemmer, and stopwords
lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))
 
# MongoDB connection details (use your actual connection string)
MONGO_URI = ""  # Store this in the environment variable or hard-code for testing
DATABASE_NAME = ""
COLLECTION_NAME = ""
 
# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]
 
# Initialize Azure OpenAI client
OPENAI_API_KEY = "f1d10e27aa074f40bd06661117fdf416"  # Azure OpenAI API Key
OPENAI_ENDPOINT = "https://genai-openai-beyondhuman.openai.azure.com/"  # Azure OpenAI Endpoint
openai_client = OpenAIClient(endpoint=OPENAI_ENDPOINT, credential=AzureKeyCredential(OPENAI_API_KEY))
 
def generate_unique_key_value():
    return str(uuid.uuid4())
 
# Define function to lemmatize and stem a sentence
def process_sentence(sentence: str):
    """Stems non-verbs and lemmatizes verbs from a sentence, removing stopwords."""
    words = word_tokenize(sentence)
    processed_words = []
 
    for word in words:
        word_lower = word.lower()
 
        # Skip stopwords and non-alphabetic words
        if word_lower not in stop_words and word.isalpha():
            # Stemming for non-verbs, lemmatizing verbs
            if word_lower in ["am", "is", "are", "was", "were", "be", "been", "being"]:
                # For certain common verbs, we apply lemmatization
                processed_words.append(lemmatizer.lemmatize(word_lower, pos="v"))
            else:
                # Apply stemming for non-verbs
                processed_words.append(stemmer.stem(word_lower))
 
    return processed_words
 
# Create a Function App instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
 
# Define route for lemmatize function
@app.route(route="lemmatize")
def process(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing a request to lemmatize and stem a sentence.')
 
    # Get the sentence from query parameters
    sentence = req.params.get('sentence')
 
    # If the sentence is not in query parameters, check the request body
    if not sentence:
        try:
            req_body = req.get_json()
            sentence = req_body.get('sentence')
        except ValueError:
            pass
 
    # If no sentence is provided, return an error message
    if not sentence:
        return func.HttpResponse(
            '{"error": "Please provide a sentence in the query string or in the request body."}',
            mimetype="application/json",
            status_code=400
        )
 
    # Process the sentence: apply both stemming and lemmatization
    processed_words = process_sentence(sentence)
    root_words_str = '-'.join(processed_words)
 
    # Check if the processed words exist in the MongoDB collection
    existing_document = collection.find_one({"root_words": root_words_str})
 
    if existing_document:
        # If document exists, return the value field (assuming the value field is 'value')
        value_field = existing_document.get('value', 'No value found')
        return func.HttpResponse(
            f'{{"root_words": "{root_words_str}", "found_in_db": true, "value": "{value_field}"}}',
            mimetype="application/json",
            status_code=200
        )
    else:
        # If document does not exist, use Azure OpenAI to generate a response
        try:
            response = openai_client.completions.create(
                model="gpt-4",  # You can choose a different model like gpt-3.5, gpt-4, etc.
                prompt=f"Generate information or a relevant response for the sentence: {sentence}",
                max_tokens=100
            )
            print("Connected successfully!")
            # Extract the value from the OpenAI response
            ai_generated_value = response.choices[0].text.strip()
            unique_key_value = generate_unique_key_value()
            # Insert into MongoDB
            document = {
                "sentence": sentence,
                "root_words": root_words_str,
                "value": ai_generated_value,  # Store AI-generated value
                "uniqueKey": unique_key_value  # Ensure this field is included
            }
            collection.insert_one(document)
 
            logging.info(f"Document inserted: {document}")
 
            return func.HttpResponse(
                f'{{"root_words": "{root_words_str}", "found_in_db": false, "value": "{ai_generated_value}"}}',
                mimetype="application/json",
                status_code=200
            )
        except Exception as e:
            logging.error(f"Error calling Azure OpenAI: {str(e)}")
            return func.HttpResponse(
                '{"error": "Error processing the request with Azure OpenAI."}',
                mimetype="application/json",
                status_code=500
            )

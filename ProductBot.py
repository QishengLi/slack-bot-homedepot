import json
import os
import logging
from pathlib import Path

from langchain.document_loaders import JSONLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts.prompt import PromptTemplate
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT


class ProductBot:

    def __init__(self, prod_name):

        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable.")

        # Create a logger object
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)
        
        self.prod_name = prod_name
        print(self.prod_name)
        file_path = self.prod_name + '.json',
        self.data = self.json_to_texts(file_path)


        embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_texts(self.data, embeddings)
        
        # define two LLM models from OpenAI
        self.llm = OpenAI(temperature=0.8)
        
        self.streaming_llm = OpenAI(
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            verbose=True,
            max_tokens=500,
            temperature=0.2
        )
        
        # use the LLM Chain to create a question creation chain
        self.question_generator = LLMChain(
            llm=self.llm,
            prompt=CONDENSE_QUESTION_PROMPT
        )
        
        # use the streaming LLM to create a question answering chain
        self.doc_chain = load_qa_chain(
            llm=self.streaming_llm,
            chain_type="stuff",
            prompt=QA_PROMPT
        )

        self.chatbot = ConversationalRetrievalChain(
            retriever=self.vectorstore.as_retriever(),
            combine_docs_chain=self.doc_chain,
            question_generator=self.question_generator
        )

        self.chat_history = []

    def predict(self, input_text):

        response = self.chatbot(
            {"question": input_text, "chat_history": self.chat_history}
        )
        print("\n")
        self.chat_history.append((response["question"], response["answer"]))

        return response["answer"]

    def dict_to_text(self, data_dict):
        text = ""
        product = data_dict['product']
        for key, value in product.items():
            if key == 'features':
                text += f"Features: "
                for i, feature in enumerate(value):
                    if i != len(value) - 1:
                        text += f"{feature['name']}: {feature['value']}; "
                    else:
                        text += f"{feature['name']}: {feature['value']}\n"
            elif key == 'images':
                continue  # skip the images field
            elif key == 'collection':
                continue  # skip the collection field
            else:
                text += f"'{key}': '{value}',\n"

        fulfillment = data_dict['fulfillment']
        for key, value in fulfillment.items():
            if key == 'pickup_info':
                continue  # skip the pickup_info field
            elif key == 'ship_to_home_info':
                continue  # skip the ship_to_home_info field
            elif key == 'scheduled_delivery_info':
                continue  # skip the scheduled_delivery_info field
            else:
                text += f"'{key}': {value},\n"

        offers = data_dict['offers']['primary']
        for key, value in offers.items():
            if key in ['price', 'regular_price']:
                text += f"'{key}': {offers['symbol']} {value},\n"
            else:
                continue  # skip other keys

        return text

    def json_to_texts(self, json_file):

        # Open and load json file: FIX
        with open('data/' + json_file[0], 'r') as f:
            data = json.load(f)
        
        # Get request parameters and homedepot_url from request_metadata
        request_params = data['request_parameters']
        homedepot_url = data['request_metadata']['homedepot_url']
        results_count = len(data['search_results'])
        
        # Generate the search metadata text
        metadata_text = "search metadata:\n"
        for key, value in request_params.items():
            metadata_text += f' "{key}": "{value}",\n'
        metadata_text += f' "homedepot_url": "{homedepot_url}"\n'
        metadata_text += f' "search_results_count": {results_count}\n'
        
        # Process each product in search_results
        result_texts = []
        for product in data['search_results']:
            print(type(product))
            print(product)
            text = self.dict_to_text(product)
            # Append the metadata text at the beginning of the product text
            text = metadata_text + text
            result_texts.append(text)
        
        return result_texts


if __name__ == "__main__":
    chatbot = ChatBot('test')
    chatbot.predict("Can you tell me more about these products?")

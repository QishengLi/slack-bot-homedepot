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
        self.loader = JSONLoader(
            file_path=self.prod_name + '.json',
            jq_schema='.search_results[]',
            text_content=False
        )

        self.data = self.loader.load()

        embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_documents(self.data, embeddings)
        
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


if __name__ == "__main__":
    chatbot = ChatBot('test.json')
    chatbot.predict("Can you tell me more about these products?")

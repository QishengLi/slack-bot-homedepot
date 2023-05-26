import prompts
from langchain import OpenAI, ConversationChain, LLMChain, PromptTemplate
from langchain.chains.conversation.memory import ConversationBufferWindowMemory

class ParamBot:
    def __init__(self):
        template = prompts.CONSTRUCT_API_PROMPT

        prompt = PromptTemplate(
            input_variables=["history", "human_input"],
            template=template
        )

        self.chatgpt_chain = LLMChain(
            llm=OpenAI(temperature=0),
            prompt=prompt,
            verbose=True,
            memory=ConversationBufferWindowMemory(k=2),
        )

    def predict(self, human_input):
        return self.chatgpt_chain.predict(human_input=human_input)

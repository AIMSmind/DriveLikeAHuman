import base64
import json
import re

from langchain_core.messages import AIMessage
from rich import print
import sqlite3

from langchain_community.chat_models import AzureChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from scenario.scenario import Scenario


class OutputParser:
    def __init__(self, sce: Scenario, llm, temperature: float = 0.0) -> None:
        self.sce = sce
        self.temperature = temperature
        self.llm = llm
        # todo: put into a yaml file
        self.response_schemas = [
            ResponseSchema(
                name="action_id",
                description=f"output the id(int) of the decision. The comparative table is:  {{ 0: 'change_lane_left', 1: 'keep_speed or idle', 2: 'change_lane_right', 3: 'accelerate or faster',4: 'decelerate or slower'}} . For example, if the ego car wants to keep speed, please output 1 as a int."),
            ResponseSchema(
                name="action_name",
                description=f"output the name(str) of the decision. MUST consist with previous \"action_id\". The comparative table is:  {{ 0: 'change_lane_left', 1: 'keep_speed', 2: 'change_lane_right', 3: 'accelerate',4: 'decelerate'}} . For example, if the action_id is 3, please output 'Accelerate' as a str."),
            ResponseSchema(
                name="explanation",
                description=f"Explain for the driver why you make such decision in 40 words.")
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(
            self.response_schemas)
        self.format_instructions = self.output_parser.get_format_instructions()

    def agentRun(self, final_results: dict) -> str:
        print('[green]Output parser is running...[/green]')
        prompt_template = ChatPromptTemplate(
            messages=[
                HumanMessagePromptTemplate.from_template(
                    "parse the problem response follow the format instruction.\nformat_instructions:{format_instructions}\n response: {answer}")
            ],
            input_variables=["answer"],
            partial_variables={"format_instructions": self.format_instructions}
        )
        input = prompt_template.format_prompt(
            answer=final_results['answer'] + final_results['thoughts'])
        with get_openai_callback() as cb:
            msgs = input.to_messages()[0]
            print(msgs)

            output: AIMessage = self.llm.invoke(str(msgs))
            str_output = output.content
            print("output content pre parse " + str_output)
            pattern = r'```json\n(.*?)\n```'
            match = re.search(pattern, str_output, re.DOTALL)
            if match:
                str_output = match.group(1)
        print("OUTPUT " + str(str_output))
        print("===============================================")

        self.parseredOutput = self.output_parser.parse(str(str_output))
        self.dataCommit()
        print("Finish output agent:\n", cb)
        return self.parseredOutput

    def dataCommit(self):
        conn = sqlite3.connect(self.sce.database)
        cur = conn.cursor()
        parseredOutput = json.dumps(self.parseredOutput)
        base64Output = base64.b64encode(
            parseredOutput.encode('utf-8')).decode('utf-8')
        cur.execute(
            """UPDATE decisionINFO SET outputParser ='{}' WHERE frame ={};""".format(
                base64Output, self.sce.frame
            )
        )
        conn.commit()
        conn.close()

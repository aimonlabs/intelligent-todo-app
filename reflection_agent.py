import os
import json
import logging
from aimon import Detect
from autogen import ConversableAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class AIMonReflectionAgent(ConversableAgent):
    
    def __init__(self):
        super().__init__(
            name="ReflectionAgent",
            system_message="An agent that checks whether model output follows given instructions."
        )

        ## Configure the AIMon decorator
        self.detector = Detect(
            values_returned=["context", "generated_text", "instructions"],
            config={"instruction_adherence": {"detector_name": "default", "explain": "negatives_only",}},
            api_key=os.getenv("AIMON_API_KEY"),
            application_name="todo_agent",
            model_name="claude_api_model",
            publish=True,
        )

        @self.detector
        def _reflect(context: str, generated_text: str, instructions: list[str]):
            return context, generated_text, instructions

        self._reflect = _reflect

        ## Register check function as a tool for this agent
        @self.register_for_execution(
            name="check_instruction_adherence",
            description="Check whether the generated text follows the given instructions."
        )
        def check_instruction_adherence(
            context: str,
            generated_text: str,
            instructions: list[str]
        ) -> str:
            """
            Runs AIMon on the tuple (context, generated_text, instructions) and returns
            a JSON string with {"score":…, "issues":[…]}.
            """
            try:
                ## Invoke AIMon
                _, _, _, aimon_res = self._reflect(context, generated_text, instructions)
                ia = aimon_res.detect_response.instruction_adherence

                issues = []
                for inst in ia.get("instructions_list", []):
                    if not inst.get("label", True):  
                        ## label=True means instruction was followed
                        issues.append({
                            "instruction": inst["instruction"],
                            "explanation": inst.get("explanation", "")
                        })

                result = {
                    "score": ia.get("score", 1.0),
                    "issues": issues
                }
            except Exception as e:
                logger.error(f"AIMon check failed: {e}")
                result = {"error": str(e)}

            return json.dumps(result)

reflection_agent = AIMonReflectionAgent()

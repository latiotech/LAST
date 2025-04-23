#guardrails.py:
import os
from agents import (
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    Agent,
    RunHooks,
    output_guardrail,
    input_guardrail,
    InputGuardrailTripwireTriggered,
    TResponseInputItem
)
import httpx
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

class PillarClient:
    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.app_id = app_id or os.environ.get("PILLAR_APP_ID")
        if not self.app_id:
            msg = "Couldn't get Pillar app ID. Set `PILLAR_APP_ID` in the environment."
            raise PillarGuardrailMissingCredentials(msg)
        self.api_key = api_key or os.environ.get("PILLAR_API_KEY")
        if not self.api_key:
            msg = "Couldn't get Pillar API key. Set `PILLAR_API_KEY` in the environment."
            raise PillarGuardrailMissingCredentials(msg)

        self.api_url = (
            api_url or os.environ.get("PILLAR_API_URL") or "https://api.pillar.security/api/v0/sessions"
        )
        self.client = httpx.AsyncClient(timeout=30.0)

    async def scan_session(self, messages, service="openai", model="gpt-4", user_id=None, session_id=None):
        """
        Scan messages against Pillar Security API

        Args:
            messages: Messages list to scan
            service: The model provider used by the application
            model: The model used by the application
            user_id: The current application user's ID
            session_id: The current agent session ID

        Returns:
            API response as dictionary
        """
        headers = {
            "X-App-Id": self.app_id,
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "async": "false" # get a verdict immediately to enable blocking as needed
        }

        try:
            data = {
            "messages": messages,
            "service": service,
            "model": model,
            "user_id": user_id,
            "session_id": session_id
            }
        
            response = await self.client.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise PillarGuardrailAPIError(
                f"Pillar API returned error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise PillarGuardrailAPIError(f"Error connecting to Pillar API: {str(e)}")

class PillarScanResult(BaseModel):
    """Model for Pillar scan results."""
    
    action: str
    categories: Dict[str, Any]
    raw_findings: List[Dict[str, Any]]
    anonymized_text: str
    session_id: str

@output_guardrail
async def pillar_output_guardrails(
    ctx: RunContextWrapper[None],
    agent: Agent,
    output_data: any # Output type varies by agent
) -> GuardrailFunctionOutput:
    """Checks agent final output using Pillar API.
    
    Args:
        ctx: The run context.
        agent: The agent being run.
        output_data: The final output produced by the agent.
        
    Returns:
        GuardrailFunctionOutput indicating if the tripwire should be triggered.
    """

    # Convert output to string for Pillar analysis
    content_to_check = ""
    if hasattr(output_data, 'final_output') and output_data.final_output:
        content_to_check = str(output_data.final_output)
    elif hasattr(output_data, "response"):
        content_to_check = output_data.response
    elif hasattr(output_data, "content"):
        content_to_check = output_data.content
    elif isinstance(output_data, str):
        content_to_check = output_data
    else:
        # Fallback: convert the output_data to string if not None
        content_to_check = str(output_data) if output_data is not None else ""
        
    if not content_to_check: # Don't call Pillar if there's no content
        return GuardrailFunctionOutput(output_info={"pillar_checked": False}, tripwire_triggered=False)
        
    messages = [{"role": "assistant", "content": content_to_check}]

    pillar_client = PillarClient()
    pillar_response = await pillar_client.scan_session(messages, user_id=ctx.context.user_id, session_id=ctx.context.session_id)
    
    scan_result = None
    
    # Check if pillar_response is a list
    if isinstance(pillar_response, list):
        # Look for any verdict with "block" action
        for verdict in pillar_response:
            if verdict.get("action") == "block":
                scan_result =  PillarScanResult(
                    action=verdict.get("action", "block"),
                    categories=verdict.get("categories", {}),
                    raw_findings=verdict.get("raw_findings", []),
                    anonymized_text=verdict.get("anonymized_text", ""),
                    session_id=verdict.get("session_id", ""),
                )
                break
        
        # If no "block" action found, use the first verdict
        if pillar_response:
            verdict = pillar_response[0]
            scan_result = PillarScanResult(
                action=verdict.get("action", "allow"),
                categories=verdict.get("categories", {}),
                raw_findings=verdict.get("raw_findings", []),
                anonymized_text=verdict.get("anonymized_text", ""),
                session_id=verdict.get("session_id", ""),
            ) 
    return GuardrailFunctionOutput(
        output_info=scan_result,
        tripwire_triggered=scan_result.action == "block",
    )
    
@input_guardrail
async def pillar_input_guardrails(
    ctx: RunContextWrapper[None] | None,
    agent: Agent,
    input: str | TResponseInputItem | None
) -> GuardrailFunctionOutput:
    """Checks first agent input using Pillar API.
    
    Args:
        ctx: The run context.
        agent: The agent being run.
        input_data: The input data provided to the agent.
        
    Returns:
        GuardrailFunctionOutput indicating if the tripwire should be triggered.
    """
    # 1. sanitize prompts ------------------------------------------
    
    if isinstance(agent, RunContextWrapper):
        system_prompt = None
    else:
        system_prompt = await agent.get_system_prompt(ctx)
    
    if isinstance(system_prompt, RunContextWrapper):
        system_prompt = None
    else:
        system_prompt = str(system_prompt)
        
    if isinstance(input, RunContextWrapper):
        input = None
    elif isinstance(input, str):
        input = str(input)
    
    # 2. build a message list ------------------------------------
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if input:
        messages.append({"role": "user", "content": input})

    # session_id = ctx.context.session_id if ctx else str(uuid.uuid4())
    # user_id = ctx.context.user_id if ctx else str(uuid.uuid4())
        
    pillar_client = PillarClient()
    # Call Pillar API with direct detection endpoint
    
    
    print("ctx", ctx)
    print("type of ctx", type(ctx))
    print("agent", agent)
    print("type of agent", type(agent))
    print("messages", messages)
    print("type of messages", type(messages))
    pillar_response = await pillar_client.scan_session(messages, user_id=ctx.context.user_id, session_id=ctx.context.session_id)
    # Create scan result
    scan_result = None

    if isinstance(pillar_response, list):
        # Look for any verdict with "block" action
        for verdict in pillar_response:
            if verdict.get("action") == "block":
                scan_result =  PillarScanResult(
                    action=verdict.get("action", "block"),
                    categories=verdict.get("categories", {}),
                    raw_findings=verdict.get("raw_findings", []),
                    anonymized_text=verdict.get("anonymized_text", ""),
                    session_id=verdict.get("session_id", ""),
                )
                break
        
        # If no "block" action found, use the first verdict
        if pillar_response:
            verdict = pillar_response[0]
            scan_result = PillarScanResult(
                action=verdict.get("action", "allow"),
                categories=verdict.get("categories", {}),
                raw_findings=verdict.get("raw_findings", []),
                anonymized_text=verdict.get("anonymized_text", ""),
                session_id=verdict.get("session_id", ""),
            ) 
    return GuardrailFunctionOutput(
        output_info=scan_result,
        tripwire_triggered=scan_result.action == "block",
    )
    
    
async def pillar_agent_start_guardrails(
    ctx: RunContextWrapper[None] | None,
    agent: Agent,
    input: str | TResponseInputItem | None
) -> GuardrailFunctionOutput:
    """Checks first agent input using Pillar API.
    
    Args:
        ctx: The run context.
        agent: The agent being run.
        input_data: The input data provided to the agent.
        
    Returns:
        GuardrailFunctionOutput indicating if the tripwire should be triggered.
    """
    # 1. sanitize prompts ------------------------------------------
    
    if isinstance(agent, RunContextWrapper):
        system_prompt = None
    else:
        system_prompt = await agent.get_system_prompt(ctx)
    
    if isinstance(system_prompt, RunContextWrapper):
        system_prompt = None
    else:
        system_prompt = str(system_prompt)
        
    if isinstance(input, RunContextWrapper):
        input = None
    elif isinstance(input, str):
        input = str(input)
    
    # 2. build a message list ------------------------------------
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if input:
        messages.append({"role": "user", "content": input})

    # session_id = ctx.context.session_id if ctx else str(uuid.uuid4())
    # user_id = ctx.context.user_id if ctx else str(uuid.uuid4())
        
    pillar_client = PillarClient()
    # Call Pillar API with direct detection endpoint
    
    
    print("ctx", ctx)
    print("type of ctx", type(ctx))
    print("agent", agent)
    print("type of agent", type(agent))
    print("messages", messages)
    print("type of messages", type(messages))
    pillar_response = await pillar_client.scan_session(messages, user_id=ctx.context.user_id, session_id=ctx.context.session_id)
    # Create scan result
    scan_result = None

    if isinstance(pillar_response, list):
        # Look for any verdict with "block" action
        for verdict in pillar_response:
            if verdict.get("action") == "block":
                scan_result =  PillarScanResult(
                    action=verdict.get("action", "block"),
                    categories=verdict.get("categories", {}),
                    raw_findings=verdict.get("raw_findings", []),
                    anonymized_text=verdict.get("anonymized_text", ""),
                    session_id=verdict.get("session_id", ""),
                )
                break
        
        # If no "block" action found, use the first verdict
        if pillar_response:
            verdict = pillar_response[0]
            scan_result = PillarScanResult(
                action=verdict.get("action", "allow"),
                categories=verdict.get("categories", {}),
                raw_findings=verdict.get("raw_findings", []),
                anonymized_text=verdict.get("anonymized_text", ""),
                session_id=verdict.get("session_id", ""),
            ) 
    return GuardrailFunctionOutput(
        output_info=scan_result,
        tripwire_triggered=scan_result.action == "block",
    )

class PillarGuardrails(RunHooks):
    # ----------------------- input side ---------------------------------
    async def on_agent_start(
        self,
        ctx: RunContextWrapper,
        agent: Agent,
    ) -> None:
        """Called every time an agent is about to run."""

        
        result = await pillar_agent_start_guardrails(ctx=ctx, agent=agent, input=None) #TODO: possible to add input data - with conv history

        if result.tripwire_triggered:
            raise InputGuardrailTripwireTriggered(result)

    # ----------------------- output side --------------------------------
    async def on_agent_end(
        self,
        ctx: RunContextWrapper,
        agent: Agent,
        output: object,                            # final output of this agent
    ) -> None:
        """Called after the agent produces its final answer."""
        result = await pillar_output_guardrails.run(ctx, agent, output)

        if result.output.tripwire_triggered:
            raise OutputGuardrailTripwireTriggered(result)
        
    # ----------  tool OUTPUT  ----------
    async def on_tool_end(self, ctx, agent, tool, result):
        # run Pillar on what the tool returned
        if tool.name == "gather_full_code":
            result = await pillar_output_guardrails.run(ctx, agent, result)
            if result.output.tripwire_triggered:
                raise OutputGuardrailTripwireTriggered(result)

class PillarGuardrailMissingCredentials(Exception):
    """Raised when required Pillar API credentials are missing."""
    pass


class PillarGuardrailAPIError(Exception):
    """Raised when there's an error with the Pillar API."""
    pass

@dataclass
class RunCtx:
    user_id: str
    session_id: str
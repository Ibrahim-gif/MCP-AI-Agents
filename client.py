import asyncio
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from datetime import datetime
from openai import AsyncAzureOpenAI
from agents import Agent, Runner, set_default_openai_client, OpenAIChatCompletionsModel
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

async def main():
    params = {"command": "uv", "args": ["run", "server.py"]}
    async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as server:
        mcp_tools = await server.list_tools()
        request = "Add a task to schedule a meeting with the client tomorrow at 3 PM and another task to prepare the presentation slides by tonight at 8 PM."
        model = "gpt-4.1"

        time_now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        instructions = "You are an expert task management agent for the user. You help the user by breaking down their requests into manageable tasks and executing them efficiently. The current time is " + time_now + "."
        
        agent = initialize_agent(name="Task Agent", instructions=instructions, model=model, mcp_servers=[server])
        result = await Runner.run(agent, request)
        print(result.final_output)

def initialize_agent(name, instructions, model, mcp_servers):
    from agents import set_tracing_disabled
    set_tracing_disabled(True)

    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment ="gpt-4.1",  # your deployment name here
        api_version="2024-10-21"  # or newer supported version
    )
    model = OpenAIChatCompletionsModel(model=model, openai_client=client)
    set_default_openai_client(client)

    agent = Agent(
        name=name,
        instructions=instructions,
        model=model,
        mcp_servers=mcp_servers
    )
    return agent

if __name__ == "__main__":
    asyncio.run(main())

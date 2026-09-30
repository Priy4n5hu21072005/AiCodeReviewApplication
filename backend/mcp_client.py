
import httpx
import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import json

load_dotenv()

async def get_github_file(owner,repo,path):
    token=os.getenv("GITHUB_TOKEN")

    headers={
        "Authorization":f"Bearer {token}"
    }

    async with httpx.AsyncClient(headers=headers) as http_client:

        async with streamable_http_client(
            "https://api.githubcopilot.com/mcp/",
             http_client=http_client
        ) as (read_stream,write_stream):

            async with ClientSession(
                read_stream,write_stream
            )as session:
                await session.initialize()


                result = await session.call_tool(
                    "get_file_contents",
                    {
                        "owner":owner,
                        "repo":repo,
                        "path":path
                    }
                )

                return result

async def search_github_code(owner,repo,query):
    token = os.getenv("GITHUB_TOKEN")
    headers={
        "Authorization":f"Bearer {token}"
    }

    async with httpx.AsyncClient(headers=headers)as http_client:
        async with streamable_http_client("https://api.githubcopilot.com/mcp/",http_client=http_client)as (read_stream,write_stream):
            async with ClientSession(read_stream,write_stream)as session:
                await session.initialize()
                result=await session.call_tool(
                    "search_code",
                    {
                        "query":query
                        
                    }
                )
                data=json.loads(result.content[0].text)
                return data

async def main():
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(headers=headers) as http_client:

        async with streamable_http_client(
            "https://api.githubcopilot.com/mcp/",
            http_client=http_client
        ) as (read_stream, write_stream):

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                await session.initialize()

                owner = "octocat"
                repo = "Hello-World"

                keywords = [
                    "authentication",
                    "password",
                    "jwt",
                    "token",
                    "secret",
                    "authorization"
                ]

                owner="Priy4n5hu21072005"
                repo="Multi-Wallet-App"
                result = await search_github_code("Priy4n5hu21072005","Multi-Wallet-App","token")
                print(result)

                
                


asyncio.run(main())
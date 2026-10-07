
import httpx
import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import json
from reviewAgent.templates import REVIEW_TEMPLATES    

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
        ) as (read_stream,write_stream,_):

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

async def list_dir(owner,repo,path=""):
    result=await get_github_file(owner,repo,path)
    if result.isError:
        return []
    data=json.loads(result.content[0].text)
    return [
        {
            "name":item["name"],
            "path":item["path"],
            "type":item["type"]
        }
        for item in data
    ]

async def traverse_repo(owner,repo,path=""):
    items=await list_dir(owner,repo,path)
    files=[]
    for item in items:
        if item["type"]=="file":
            files.append(item["path"])
        elif item["type"]=="dir":
            child_files=await traverse_repo(owner,repo,item["path"])
            files.extend(child_files)
    return files

async def get_relevent_files(owner,repo,template):
    template_context=REVIEW_TEMPLATES[template]
    search_keywords=template_context["search_keywords"]
    combined_query=" OR ".join(search_keywords)
    search_result=await search_github_code(owner,repo,combined_query)
    files=[]
    for item in search_result.get("items",[]):
        path=item.get("path")

        if path:
            files.append(path)
    return files

async def search_github_code(owner,repo,query):
    token = os.getenv("GITHUB_TOKEN")
    headers={
        "Authorization":f"Bearer {token}"
    }

    async with httpx.AsyncClient(headers=headers)as http_client:
        async with streamable_http_client("https://api.githubcopilot.com/mcp/",http_client=http_client)as (read_stream,write_stream,_):
            async with ClientSession(read_stream,write_stream)as session:
                await session.initialize()
                result=await session.call_tool(
                    "search_code",
                    {
                        "query":f"{query} repo:{owner}/{repo}"
                        
                    }
                )
                data=json.loads(result.content[0].text)
                return data

def score_path(path,template_context):
    score=0
    path_lower=path.lower()
    for keyword in template_context["search_keywords"]:
        if keyword.lower() in path_lower:
            score+=1
    return score

async def main():
        owner="Priy4n5hu21072005"
        repo="Multi-Wallet-App"
        files=await traverse_repo(owner,repo)
        print("FILES FOUND:")
        for file in files:
            print(file)
asyncio.run(main())
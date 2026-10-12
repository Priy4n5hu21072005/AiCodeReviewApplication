
import httpx
import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import json
from reviewAgent.templates import REVIEW_TEMPLATES    
import heapq
import itertools


load_dotenv()

async def get_github_file(owner,repo,path):
    token=os.getenv("GITHUB_TOKEN")

    headers={
        "Authorization":f"Bearer {token}"
    }

    async with httpx.AsyncClient(headers=headers,timeout=httpx.Timeout(30.0,connect=15.0)) as http_client:

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
    try:
        result = await get_github_file(owner,repo,path)
        if result.isError or not result.content:
            print(f"Failed to list directory:{path or 'root'}")
            return []
        data=json.loads(result.content[0].text)

        if not isinstance(data,list):
            print(f"Unexpected response for:{path or 'root'}")
            return []
        return [
            {
                "name":item["name"],
                "path":item["path"],
                "type":item["type"]
            }
            for item in data
        ]
    except (httpx.TimeoutException,httpx.ConnectError) as e:
        print(f"Connection failed for {path or 'root'}:{e}")
        return []
    except (json.JSONDecodeError,KeyboardInterrupt,IndexError)as e:
        print(f"Invalid MCP response for {path or 'root'}:{e}")
        return []
    
async def traverse_repo(owner,repo,path="",deapth=0,max_deapth=3,budget=None,template="security"):
    if budget is None:
        budget={"directories":0,"max_directories":15}
    if deapth>max_deapth:
        return []
    if budget["directories"]>=budget["max_directories"]:
        return []
    budget["directories"]+=1

    items=await list_dir(owner,repo,path)
    files=[]
    priorities={
        "security":[
            "src","main","java","security",
            "auth","config","controller","service"
        ],
        "code_quality":[
            "src","main","java","service",
            "controller","repository","test",
                        
        ],
        "scalability":[
            "src","main","java",
            "repository","service",
            "config","resources"
        ]
    }
    priority=priorities.get(template,["src","main"])

    directories = sorted(
    [
        item for item in items
        if item["type"] == "dir"
        and item["name"].lower() != "multiwallet"
    ],
    key=lambda item: (
        priority.index(item["name"].lower())
        if item["name"].lower() in priority
        else len(priority)
    )
)

    for item in items:
        if item["type"]=="file":
            files.append(item["path"])
    for item in directories:
        if budget["directories"]>=budget["max_directories"]:
            break
        child_files=await traverse_repo(owner,repo,item["path"],deapth+1,max_deapth,budget,template)
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
    keywords=[keyword.lower()
              for keyword in template_context.get("search_keywords",[])]
    for keyword in keywords:
        if keyword.lower() in path_lower:
            score+=2
    source_extension=(
        ".py",".java",".js",".ts",
        ".go",".rs",".cpp",".cs",".php",
        ".rb",".sql"
    )
    if path_lower.endswith(source_extension):
        score+=1
    useful_extensions=(
        ".yml",".yaml",".toml",".json",
        ".xml",".properties",".md"
    )
    if path_lower.endswith(useful_extensions):
        score+=1
    return score
    

async def intelligent_trav(owner,repo,template,max_dir=15,max_depth=4):
    qu=[]
    counter=itertools.count()
    template_context=REVIEW_TEMPLATES[template]
    heapq.heappush(qu,(0,next(counter),"",0))
    visited=set()
    discovery_files=[]
    dir_count=0
    while qu and dir_count < max_dir:
        priority,_,path,depth=heapq.heappop(qu)
        if path in visited or depth>max_depth:
            continue
        visited.add(path)
        dir_count+=1
        items=await list_dir(owner,repo,path)
        print(
            f"Exploring:{path or '<root>'} |"
            f"Depth:{depth} |"
            f"Directories visited:{dir_count}"
        )
        for item in items:
            item_path=item["path"]
            if item["type"]=="file":
                file_score=score_path(item_path,template_context)
                discovery_files.append({
                    "path":item_path,
                    "score":file_score
                })
            elif item["type"]=="dir":
                if item_path not in visited:
                    score=score_path(item_path,template_context)
                    heapq.heappush(qu,(-score,next(counter),item_path,depth+1))

    discovery_files.sort(
                    key=lambda file:file["score"],
                    reverse=True
                )
    return discovery_files         

async def main():
        owner="Priy4n5hu21072005"
        repo="Multi-Wallet-App"
        files=await intelligent_trav(owner,repo,template="security",max_depth=4)
        print("FILES FOUND:",len(files))
        for file in files:
            print(file["score"],file["path"])
asyncio.run(main())